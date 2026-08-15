"""Memória incremental do pipeline de codificação — o agente evolui entre runs.

PoC da issue #303, construída sobre o **ReasoningBank** (Google Research,
Apache-2.0). O ciclo é:

    run N   ─┬─> ExecutionReport + ValidationVerdict   (evidência determinística)
             ├─> extract.destilar()   ≤3 itens, prompts verbatim do ReasoningBank
             ├─> judge.julgar()       veredito ternário, sem LLM (GovMem)
             └─> store.append()       JSONL em AI4ES_MEMORY_DIR, FORA do repo
                                                   │
    run N+1 ─── retrieve.recuperar() ──────────────┘  pré-filtro por error_code
             └─> render_bloco() → prompt do cr_coder      + cosseno (fastembed)

O banco vive fora do `workspace_output/` de propósito: `init_workspace()` faz
`shutil.rmtree` da pasta inteira a cada run, e é exatamente por isso que o
agente nunca acumulou nada entre execuções.

Kill switch: `AI4ES_MEMORY_ENABLED=0` desliga injeção e escrita, restaurando o
comportamento de `develop`.

Este pacote **não importa `shared.execution`** — de propósito. Aquele pacote
reexporta `sandbox.py`, que faz `import resource` (POSIX-only) e derrubaria a
memória em Windows junto com o resto do pipeline.
"""

from .extract import destilar, modelo_de_destilacao, parse_memory_items
from .judge import julgar, julgar_lote
from .retrieve import recuperar, render_bloco
from .schemas import (
    MemoryItem,
    MemoryOutcome,
    MemoryProvenance,
    MemoryStatus,
)
from .store import MemoryStore, get_memory_dir, memoria_habilitada
from .trajectory import (
    carregar_historico,
    carregar_report,
    error_codes_do_report,
    montar_manifesto,
    montar_trajetoria,
    normalizar_status,
    resumir_tentativas,
)

__all__ = [
    "MemoryItem",
    "MemoryOutcome",
    "MemoryProvenance",
    "MemoryStatus",
    "MemoryStore",
    "carregar_historico",
    "carregar_report",
    "destilar",
    "error_codes_do_report",
    "get_memory_dir",
    "julgar",
    "julgar_lote",
    "memoria_habilitada",
    "modelo_de_destilacao",
    "montar_manifesto",
    "montar_trajetoria",
    "normalizar_status",
    "parse_memory_items",
    "recuperar",
    "render_bloco",
    "resumir_tentativas",
]
