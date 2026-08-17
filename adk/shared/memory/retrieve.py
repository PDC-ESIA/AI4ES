"""Recuperação dos itens de memória relevantes para a run corrente.

## O algoritmo é o do ReasoningBank; o backend, não

De `third_party/src/minisweagent/memory/memory_management.py`, no repositório
`google-research/reasoning-bank`, preservamos o procedimento de
`select_memory`/`screening`: embutir a consulta, normalizar em L2, ranquear os
itens do banco por **similaridade de cosseno** e devolver o **top-k**.

O que trocamos é só o backend de embedding, e por impossibilidade concreta: o
original importa `torch` + `transformers` (Qwen3-Embedding-8B) ou `vertexai` /
`google.genai`. Isso significaria ~16 GB de modelo, ou uma credencial Google
nova num projeto que autentica por GitHub Copilot.

Usamos **`fastembed`**, que já está declarado no `pyproject.toml` e instalado,
mas que até aqui não era importado por nenhum módulo do repositório — uma
dependência paga e não usada. É ONNX puro, roda em CPU, não arrasta torch, e
esta camada passa a justificar esse custo.

## Um pré-filtro que o ReasoningBank não podia ter

Antes do cosseno roda um filtro **determinístico** por `error_code` e por
`tech_stack`. Isso não é um atalho para economizar embedding: é o uso da verdade
de campo que o ReasoningBank não tem e que aqui existe — ver `judge.py`. Se a
run anterior morreu com `FALHA_BUILD`, o item que fala de `FALHA_BUILD` é
relevante por construção, não por proximidade de vetores. A similaridade entra
depois, para ordenar o que sobrou e para cobrir o caso em que não há
`error_code` algum — que é justamente a primeira run.

Degradação: se o `fastembed` não estiver disponível ou o modelo não puder ser
baixado, a recuperação **não falha** — cai para o pré-filtro determinístico mais
ordenação por recência. Sem rede, a memória continua funcionando; só perde o
desempate semântico.
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Sequence

from .schemas import MemoryItem
from .store import MemoryStore, memoria_habilitada

logger = logging.getLogger(__name__)

# MiniLM multilíngue: nosso conteúdo é escrito em português (ver `_ADENDO_AI4ES`
# em extract.py), então um modelo só-inglês ranquearia mal. ~120 MB em ONNX.
_DEFAULT_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_DEFAULT_TOP_K = 5

_embedder = None  # cache de processo: carregar o ONNX a cada run é caro
_INDISPONIVEL = object()  # sentinela: falha já diagnosticada, não retentar


def _get_embedder():
    """Instancia o `TextEmbedding` uma vez por processo, ou `None` se indisponível.

    Toda falha — pacote ausente, download bloqueado, modelo desconhecido — vira
    `None` e ativa o caminho degradado. Nunca propaga.

    A falha também é cacheada, e isso importa: esta função roda uma vez por
    TURNO do coder (ver `_instruction_provider` em `coder/agent.py`), então um
    download bloqueado sem cache seria retentado — com timeout de rede — antes
    de cada requisição ao LLM. O preço é que a primeira falha desliga o ranking
    semântico até o processo reiniciar; aceitável, porque o fallback por
    recência é funcional.
    """
    global _embedder
    if _embedder is _INDISPONIVEL:
        return None
    if _embedder is not None:
        return _embedder

    try:
        from fastembed import TextEmbedding

        nome = os.environ.get("AI4ES_MEMORY_EMBED_MODEL", _DEFAULT_EMBED_MODEL)
        _embedder = TextEmbedding(model_name=nome)
        logger.info("[MEMORY] Embedder carregado: %s", nome)
        return _embedder
    except Exception as exc:  # noqa: BLE001 — ver docstring
        logger.warning(
            "[MEMORY] fastembed indisponível (%s); recuperação cai para o "
            "pré-filtro determinístico sem ranking semântico.",
            exc,
        )
        _embedder = _INDISPONIVEL
        return None


def _top_k() -> int:
    try:
        return max(1, int(os.environ.get("AI4ES_MEMORY_TOP_K", _DEFAULT_TOP_K)))
    except (TypeError, ValueError):
        return _DEFAULT_TOP_K


def _texto_do_item(item: MemoryItem) -> str:
    """Texto embutido de um item — os três campos do contrato ReasoningBank."""
    return f"{item.title}. {item.description} {item.content}"


def _ranquear_por_cosseno(
    consulta: str, itens: list[MemoryItem], k: int
) -> Optional[list[MemoryItem]]:
    """Ranking por cosseno, como no `screening()` do ReasoningBank.

    Devolve `None` quando o embedder não está disponível, sinalizando ao
    chamador que use a ordenação de fallback.
    """
    embedder = _get_embedder()
    if embedder is None:
        return None

    try:
        import numpy as np

        vetores = list(embedder.embed([consulta] + [_texto_do_item(i) for i in itens]))
        matriz = np.array(vetores, dtype=np.float32)

        # Normalização L2 + produto interno = cosseno (idêntico ao original,
        # que usa torch.nn.functional.normalize antes do matmul).
        normas = np.linalg.norm(matriz, axis=1, keepdims=True)
        matriz = matriz / np.clip(normas, 1e-12, None)

        scores = matriz[1:] @ matriz[0]
        ordem = np.argsort(-scores)
        return [itens[i] for i in ordem[:k]]
    except Exception as exc:  # noqa: BLE001
        logger.warning("[MEMORY] Ranking semântico falhou (%s); usando fallback.", exc)
        return None


def _pre_filtrar(
    itens: list[MemoryItem],
    *,
    error_codes: Sequence[str] = (),
    tech_stack: str = "",
) -> list[MemoryItem]:
    """Filtro determinístico por escopo e por código de erro.

    - **Escopo:** item de outra stack sai; item genérico (sem stack) fica.
      Quando a stack da run corrente é **desconhecida**, o filtro fica MAIS
      restritivo, não menos: só passam itens genéricos. Deixar passar tudo
      seria injetar lição de `node-express` num projeto Python — precisamente
      o *perspective confinement* que o OEP descreve (confundir acerto
      localizado com regra amplamente válida). Na prática a stack vem do
      `_macro_context.json`, que o context engineer grava antes do coder; se
      ela faltou, algo já está errado e o silêncio é a resposta segura.
    - **error_code:** se a run corrente já falhou com códigos conhecidos, os
      itens que citam algum deles são os relevantes por construção. Se nenhum
      item casar, devolve todos — é melhor ranquear semanticamente o banco
      inteiro do que entregar bloco vazio.
    """
    stack = tech_stack.strip().casefold()
    if stack:
        itens = [
            i for i in itens if not i.tech_stack.strip() or i.tech_stack.casefold() == stack
        ]
    else:
        genericos = [i for i in itens if not i.tech_stack.strip()]
        if len(genericos) != len(itens):
            logger.warning(
                "[MEMORY] Stack da run desconhecida; %d item(ns) com escopo "
                "declarado foram retidos para não cruzar stacks.",
                len(itens) - len(genericos),
            )
        itens = genericos

    codigos = {c.strip().upper() for c in error_codes if c and c.strip()}
    if codigos:
        casados = [i for i in itens if codigos & {c.upper() for c in i.error_codes}]
        if casados:
            return casados

    return itens


def recuperar(
    consulta: str,
    *,
    error_codes: Sequence[str] = (),
    tech_stack: str = "",
    store: Optional[MemoryStore] = None,
    k: Optional[int] = None,
) -> list[MemoryItem]:
    """Seleciona os itens promovidos mais relevantes para a run corrente.

    Só itens com status `promovido` são candidatos — os em quarentena existem
    no banco, mas nunca chegam ao prompt.
    """
    if not memoria_habilitada():
        return []

    store = store or MemoryStore()
    candidatos = store.promovidos()
    if not candidatos:
        return []

    candidatos = _pre_filtrar(
        candidatos, error_codes=error_codes, tech_stack=tech_stack
    )
    k = k or _top_k()

    ranqueados = _ranquear_por_cosseno(consulta, candidatos, k)
    if ranqueados is None:
        # Fallback sem embedding: os mais recentes primeiro. `created_at` é
        # ISO-8601 UTC, então a ordem lexicográfica é a cronológica.
        ranqueados = sorted(candidatos, key=lambda i: i.created_at, reverse=True)[:k]

    return ranqueados


def render_bloco(itens: list[MemoryItem]) -> str:
    """Formata os itens como o bloco markdown injetado no prompt do coder.

    O ReasoningBank não especifica esse formato (o `select_memory` devolve
    dicts crus), então o layout é nosso. Duas escolhas deliberadas:

    - o bloco **declara sua própria origem** e diz que é falível, para o coder
      não tratar a lição como parte do contrato da task;
    - cada item mostra o `error_code` que o originou, dando ao modelo o gancho
      concreto para reconhecer a situação.
    """
    if not itens:
        return ""

    linhas = [
        "# MEMÓRIA DE RUNS ANTERIORES",
        "",
        "As lições abaixo foram destiladas automaticamente de execuções passadas",
        "deste pipeline e validadas contra a evidência do harness. Trate-as como",
        "aviso de quem já tropeçou, NÃO como requisito: em conflito com o",
        "contrato da task ou com o `_macro_context.json`, o contrato vence.",
        "",
    ]

    for item in itens:
        origem = (
            f" (origem: {', '.join(item.error_codes)})" if item.error_codes else ""
        )
        linhas.append(f"## {item.title}{origem}")
        if item.description.strip():
            linhas.append(f"_{item.description.strip()}_")
        linhas.append(item.content.strip())
        linhas.append("")

    return "\n".join(linhas)
