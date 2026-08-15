"""Destilação de itens de memória a partir da trajetória de uma run.

## Origem: ReasoningBank (Google Research, Apache License 2.0)

Os dois system instructions abaixo são **reproduzidos verbatim** de
`third_party/src/minisweagent/memory/instruction.py` do repositório
`google-research/reasoning-bank`, que é a implementação de referência do
ReasoningBank para SWE-Bench — o trabalho do levantamento mais próximo do nosso
domínio. Mantê-los sem edição é deliberado: é o que faz esta PoC ser uma
integração do trabalho publicado, e não uma reinvenção com o nome dele.

Deles vêm quatro decisões de desenho, todas preservadas:

1. o item de memória tem exatamente `Title` / `Description` / `Content`;
2. no máximo **3** itens por trajetória;
3. prompts **diferentes** para sucesso e falha — sucesso rende estratégia
   replicável, falha rende lição preventiva (aprender de falha é a contribuição
   central do ReasoningBank frente ao Dynamic Cheatsheet);
4. a saída é **Markdown**, não JSON.

## Por que a saída em Markdown importa tanto aqui

O item 4 nos livra de graça de um modo de falha conhecido deste pipeline: sob
GitHub Copilot o `output_schema` é decorativo, porque `app/main.py` liga
`litellm.drop_params = True` e o LiteLLM descarta o `response_format` em
silêncio. O modelo nunca é obrigado a emitir JSON, o Pydantic valida depois do
fato, e a run cai em `ValidationError` — já aconteceu com o `TasksOutput` do
context engineer. Um parser de cabeçalhos markdown degrada (extrai o que der,
ignora o resto) em vez de derrubar.

## O que trocamos

O `induce_memory.py` do ReasoningBank não é reusável: é um script de CLI que
parseia o formato de log do mini-swe-agent e instancia um `genai.Client()` fixo.
Aqui a trajetória é montada do `ExecutionReport` + `ValidationVerdict`, e a
chamada de LLM usa `litellm.completion` direto — o mesmo padrão de
`shared/preflight.py:86`, sem agente ADK no caminho.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Optional

from .schemas import MemoryItem, MemoryOutcome, MemoryProvenance

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 90.0
_DEFAULT_MODEL = "gemini-2.5-flash"
_MAX_ITENS = 3  # teto do ReasoningBank: "at most 3 memory items"

# ---------------------------------------------------------------------------
# TRECHO DE TERCEIROS — as duas constantes abaixo são obra de outro autor.
#
#   Copyright 2026 Google LLC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# Fonte: github.com/google-research/reasoning-bank
#        third_party/src/minisweagent/memory/instruction.py
#
# ALTERAÇÃO EM RELAÇÃO AO ORIGINAL (exigida pela §4(b) da licença): nenhuma
# alteração de conteúdo. A única diferença é a remoção de um espaço em branco
# no fim da primeira linha de cada string — 1 caractere em cada, sem efeito
# semântico. Conferido por diff programático em 13/08/2026.
#
# NÃO EDITAR o texto abaixo: mantê-lo idêntico é o que faz esta camada ser uma
# integração do trabalho publicado, e não uma reescrita com o nome dele. O
# adendo nosso vive separado, em `_ADENDO_AI4ES`, e é concatenado em runtime.
# ---------------------------------------------------------------------------

SUCCESSFUL_SI = """
You are an expert in coding, specifically fixing a given issue in a code repository. You will be given an issue to be fixed, the corresponding trajectory that represents **how an agent successfully resolved the issue**.

## Guidelines
You need to extract and summarize useful insights in the format of memory items based on the agent's successful trajectory.
The goal of summarized memory items is to be helpful and generalizable for future similar tasks.

## Important notes
  - You must first think why the trajectory is successful, and then summarize the insights.
  - You can extract *at most 3* memory items from the trajectory.
  - You must not repeat similar or overlapping items.
  - Do not mention specific websites, queries, or string contents, but rather focus on the generalizable insights.

## Output Format
Your output must strictly follow the Markdown format shown below:

```
# Memory Item i
## Title <the title of the memory item>
## Description <one sentence summary of the memory item>
## Content <1-3 sentences describing the insights learned to successfully resolve the issue in the future>
```
"""

FAILED_SI = """
You are an expert in coding, specifically fixing a given issue in a code repository. You will be given a user query, the corresponding trajectory that represents **how an agent attempted to resolve the issue but failed**.

## Guidelines
You need to extract and summarize useful insights in the format of memory items based on the agent's failed trajectory.
The goal of summarized memory items is to be helpful and generalizable for future similar tasks.

## Important notes
  - You must first reflect and think why the trajectory failed, and then summarize what lessons you have learned or strategies to prevent the failure in the future.
  - You can extract *at most 3* memory items from the trajectory.
  - You must not repeat similar or overlapping items.
  - Do not mention specific websites, queries, or string contents, but rather focus on the generalizable insights.

## Output Format
Your output must strictly follow the Markdown format shown below:

```
# Memory Item i
## Title <the title of the memory item>
## Description <one sentence summary of the memory item>
## Content <1-3 sentences describing the insights learned to successfully resolve the issue in the future>
```
"""

# Adendo nosso ao system instruction. Não altera o contrato do ReasoningBank —
# só ancora o idioma e nomeia a evidência que temos e o mini-swe-agent não.
_ADENDO_AI4ES = """
## Additional context for this deployment
The trajectory below comes from a deterministic execution harness, not from a
free-form agent log. Stage names, statuses and `error_code` values are ground
truth produced by the harness — not the agent's own opinion of what happened.
Anchor every insight you write on that evidence.

Write the Title, Description and Content in **Brazilian Portuguese**; keep the
Markdown headers themselves in English exactly as specified above.
"""


# ---------------------------------------------------------------------------
# Parser do formato de saída do ReasoningBank
# ---------------------------------------------------------------------------

# Aceita "# Memory Item 1", "## Memory Item 2", com ou sem número — modelos
# variam a numeração e o nível do cabeçalho, e nenhuma das duas coisas é
# semântica.
_RE_ITEM = re.compile(r"^#{1,3}\s*Memory\s+Item\b.*$", re.IGNORECASE | re.MULTILINE)
_RE_CAMPO = re.compile(
    r"^#{1,4}\s*(Title|Description|Content)\b[:\s]*(.*)$", re.IGNORECASE
)


def parse_memory_items(texto: str) -> list[dict[str, str]]:
    """Extrai os blocos `Title`/`Description`/`Content` da saída do LLM.

    Tolerante por desenho: cabeçalho fora de ordem, campo em linha própria ou
    na mesma linha do cabeçalho, cerca de código em volta e numeração ausente
    são todos aceitos. Um item sem `title` é descartado — sem título não há id
    estável e o dedup deixa de funcionar.

    Devolve no máximo `_MAX_ITENS`, respeitando o teto do ReasoningBank mesmo
    quando o modelo ignora a instrução.
    """
    if not texto or not texto.strip():
        return []

    # Remove cercas de código: o modelo costuma embrulhar a resposta inteira
    # em ``` porque o próprio prompt mostra o formato dentro de uma cerca.
    limpo = re.sub(r"^\s*```[a-zA-Z]*\s*$", "", texto, flags=re.MULTILINE)

    blocos = _RE_ITEM.split(limpo)[1:]  # [0] é o preâmbulo antes do 1º item
    if not blocos:
        blocos = [limpo]  # sem cabeçalho de item: tenta o texto todo como um só

    itens: list[dict[str, str]] = []
    for bloco in blocos:
        campos = _parse_bloco(bloco)
        if campos.get("title"):
            itens.append(campos)

    return itens[:_MAX_ITENS]


def _parse_bloco(bloco: str) -> dict[str, str]:
    """Lê um bloco de item, acumulando linhas soltas no último campo aberto."""
    campos: dict[str, list[str]] = {}
    atual: Optional[str] = None

    for linha in bloco.splitlines():
        m = _RE_CAMPO.match(linha.strip())
        if m:
            atual = m.group(1).lower()
            campos[atual] = [m.group(2).strip()] if m.group(2).strip() else []
        elif atual and linha.strip():
            # Continuação: o modelo pôs o valor na linha seguinte ao cabeçalho.
            if linha.strip().startswith("#"):
                atual = None  # cabeçalho desconhecido encerra o campo corrente
                continue
            campos[atual].append(linha.strip())

    return {k: " ".join(v).strip() for k, v in campos.items() if v}


# ---------------------------------------------------------------------------
# Chamada ao LLM
# ---------------------------------------------------------------------------


def _timeout() -> float:
    try:
        return float(os.environ.get("AI4ES_MEMORY_TIMEOUT", _DEFAULT_TIMEOUT))
    except (TypeError, ValueError):
        return _DEFAULT_TIMEOUT


def modelo_de_destilacao() -> str:
    """O modelo que `destilar` vai usar, resolvido do ambiente.

    Existe para que a proveniência do item registre **o mesmo** valor que a
    chamada usou, sem duplicar a regra de resolução em dois lugares. Antes disso
    `MemoryProvenance.model` era preenchido a partir de um `state` que ninguém
    escrevia, e saía vazio em todo item — o banco não sabia dizer que modelo
    tinha destilado o quê, o que inviabiliza comparar bancos entre modelos.
    """
    return os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)


def _completar(system_instruction: str, trajetoria: str, model: str) -> str:
    """Uma chamada de completion. Padrão de `shared/preflight.py:86`."""
    import litellm

    resposta = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": system_instruction + _ADENDO_AI4ES},
            {"role": "user", "content": trajetoria},
        ],
        max_tokens=1536,
        timeout=_timeout(),
    )
    return resposta.choices[0].message.content or ""


def destilar(
    trajetoria: str,
    outcome: MemoryOutcome,
    *,
    error_codes: Optional[list[str]] = None,
    unmet_criteria: Optional[list[str]] = None,
    tech_stack: str = "",
    provenance: Optional[MemoryProvenance] = None,
    model: Optional[str] = None,
) -> list[MemoryItem]:
    """Destila ≤3 `MemoryItem` da trajetória, pelo protocolo do ReasoningBank.

    Escolhe `SUCCESSFUL_SI` ou `FAILED_SI` conforme o desfecho — a distinção é
    o ponto do ReasoningBank frente às abordagens que só aprendem de sucesso.

    Nunca levanta: falha de rede, timeout ou saída ininteligível devolvem lista
    vazia. Memória é acessório do prompt; sua ausência não pode derrubar a run.
    """
    model = model or modelo_de_destilacao()
    si = SUCCESSFUL_SI if outcome == MemoryOutcome.SUCESSO else FAILED_SI

    try:
        bruto = _completar(si, trajetoria, model)
    except Exception as exc:  # noqa: BLE001 — ver docstring
        logger.warning("[MEMORY] Destilação falhou (%s); nenhum item extraído.", exc)
        return []

    crus = parse_memory_items(bruto)
    if not crus:
        logger.warning(
            "[MEMORY] Saída do modelo não continha item no formato ReasoningBank."
        )
        return []

    itens: list[MemoryItem] = []
    for cru in crus:
        try:
            itens.append(
                MemoryItem(
                    title=cru.get("title", ""),
                    description=cru.get("description", ""),
                    content=cru.get("content", ""),
                    outcome=outcome,
                    error_codes=list(error_codes or []),
                    unmet_criteria=list(unmet_criteria or []),
                    tech_stack=tech_stack,
                    provenance=provenance,
                )
            )
        except Exception:
            logger.warning("[MEMORY] Item malformado descartado: %r", cru)

    logger.info("[MEMORY] %d item(ns) destilado(s) da trajetória.", len(itens))
    return itens
