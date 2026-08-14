"""Schemas Pydantic da memória incremental do pipeline de codificação.

O núcleo é o `MemoryItem`, cujos três campos de conteúdo — `title`,
`description`, `content` — são o schema do **ReasoningBank** (Google, Apache
2.0), reproduzido sem alteração para que os prompts de extração originais
possam ser reusados verbatim. Ver `extract.py` para os prompts.

Ao redor desses três campos acrescentamos o que o ReasoningBank não tem e nós
temos: **verdade de campo**. O item carrega o `error_code` do estágio do harness
que o originou, o veredito determinístico do `implementation_validator` e a
proveniência completa da run. É isso que permite julgar a promoção sem depender
de auto-avaliação por LLM (ver `judge.py`).

Nomes de campos em inglês; descrições/enums/comentários em português, seguindo
o padrão de `executor/schemas.py` e `implementation_validator/schemas.py`.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MemoryStatus(str, Enum):
    """Veredito de curadoria de um item — **ternário**, seguindo o GovMem.

    O terceiro estado é o ponto todo: o GovMem mostra que o volume real de
    candidatos se concentra em "precisa de revisão", e que tratar essa fatia
    como binária é justamente o que produz falsa promoção (na adjudicação
    humana deles, 0 de 133 candidatos de agente de código eram seguros para
    promoção automática). Só `PROMOVIDO` é recuperado e injetado no prompt.
    """

    PROMOVIDO = "promovido"  # ancorado em evidência; entra no contexto do coder
    REVISAR = "revisar"  # plausível, sem âncora suficiente; fica em quarentena
    REJEITADO = "rejeitado"  # malformado ou contradiz a evidência


class MemoryOutcome(str, Enum):
    """Desfecho da trajetória que originou o item.

    Decide qual dos dois prompts do ReasoningBank é usado na extração:
    trajetória de sucesso rende estratégia replicável; a de falha rende lição
    preventiva.
    """

    SUCESSO = "sucesso"
    FALHA = "falha"


class MemoryProvenance(BaseModel):
    """De onde o item veio — auditoria e rastreio até a evidência bruta.

    Sem isso um item promovido é indistinguível de um item inventado. O
    `report_path` aponta para o `ExecutionReport` que sustenta a alegação.
    """

    run_id: str = Field(description="Identificador da run (session id do ADK)")
    task_id: str = Field(default="", description="Work item de origem, ex.: TASK-001")
    iteration: Optional[int] = Field(
        default=None, description="Iteração do loop coder⇄executor, quando conhecida"
    )
    report_path: Optional[str] = Field(
        default=None, description="Caminho do ExecutionReport que embasa o item"
    )
    model: str = Field(default="", description="Modelo que destilou o item")


class MemoryItem(BaseModel):
    """Uma lição destilada de uma trajetória, reusável em runs futuras.

    Os campos `title`/`description`/`content` são o contrato do ReasoningBank e
    chegam prontos do parser de markdown; todo o resto é preenchido
    deterministicamente pelo pipeline, nunca pelo LLM.
    """

    # --- Contrato ReasoningBank (preenchido pelo LLM) ----------------------
    title: str = Field(description="Título do item de memória")
    description: str = Field(description="Resumo em uma frase")
    content: str = Field(description="1-3 frases com a lição acionável, generalizada")

    # --- Verdade de campo (preenchida pelo pipeline) -----------------------
    outcome: MemoryOutcome = Field(description="Desfecho da trajetória de origem")
    error_codes: list[str] = Field(
        default_factory=list,
        description="error_codes dos estágios em falha na trajetória de origem",
    )
    unmet_criteria: list[str] = Field(
        default_factory=list,
        description=(
            "Critérios de aceite não atendidos/inconclusivos no ValidationVerdict. "
            "É o SEGUNDO sinal de verdade de campo, ao lado do error_code: a "
            "reprovação semântica do implementation_validator não produz "
            "error_code nenhum, porque nela o harness passa em todos os estágios."
        ),
    )
    tech_stack: str = Field(
        default="", description="Stack do produto, vinda do _macro_context.json"
    )

    # --- Curadoria ---------------------------------------------------------
    status: MemoryStatus = Field(
        default=MemoryStatus.REVISAR,
        description="Veredito de curadoria; só 'promovido' é injetado no prompt",
    )
    judge_reason: str = Field(
        default="", description="Por que o julgador decidiu esse status"
    )

    # --- Metadados ---------------------------------------------------------
    id: str = Field(default="", description="Identificador estável, derivado do título")
    created_at: str = Field(default="", description="Timestamp ISO-8601 UTC da criação")
    times_retrieved: int = Field(
        default=0, description="Quantas vezes o item já foi injetado num prompt"
    )
    provenance: Optional[MemoryProvenance] = Field(
        default=None, description="Rastro até a run e a evidência de origem"
    )

    def model_post_init(self, _context) -> None:
        """Preenche `id` e `created_at` quando não vieram do disco."""
        if not self.id:
            self.id = derivar_id(self.title)
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


def normalizar_titulo(titulo: str) -> str:
    """Reduz o título à sua forma canônica para comparação.

    Casefold + colapso de espaços + remoção de pontuação de borda. É o mesmo
    grau de normalização do dedup por título da KB anterior, aqui usado só para
    gerar o `id` — a deduplicação real é semântica (ver `store.py`).
    """
    t = re.sub(r"\s+", " ", titulo or "").strip().casefold()
    return t.strip(" .:;-–—\"'`")


def derivar_id(titulo: str) -> str:
    """Deriva um id curto e estável a partir do título normalizado."""
    canonico = normalizar_titulo(titulo)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()[:12]
