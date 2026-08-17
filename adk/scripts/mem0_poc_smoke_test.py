"""Smoke test isolado do PoC de memória (mem0) — sem subir o pipeline ADK.

Valida a config de `shared/memory/config.py::get_memory()` (chave Gemini,
embedder, vector store) fazendo um roundtrip real de add + search, antes de
depender disso dentro do `workflow_coding_review`.

Uso (vector store local, Chroma — não exige nada rodando):
    GOOGLE_API_KEY=... uv run python scripts/mem0_poc_smoke_test.py

Uso (vector store Postgres/pgvector):
    GOOGLE_API_KEY=... AI4ES_MEMORY_DATABASE_URL=postgresql://user:pass@host:port/db \\
        uv run python scripts/mem0_poc_smoke_test.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.memory.config import get_memory  # noqa: E402

_STACK_KEY = "smoke-test-stack"
_LICAO = (
    "Iteração 1: motivo do bloqueio = ModuleNotFoundError para o pacote 'requests'. "
    "Estágios com falha: testes_automatizados: DEPENDENCIA_AUSENTE. "
    "Status final após revisão: APROVADO."
)


async def _run() -> int:
    if not os.environ.get("GOOGLE_API_KEY", "").strip():
        print("GOOGLE_API_KEY não definido — necessário para LLM e embedder do mem0.")
        return 1

    memoria = get_memory()

    try:
        resultado_add = await memoria.add(messages=_LICAO, agent_id=_STACK_KEY)
        print(f"add() OK — {resultado_add}")

        resultado_busca = await memoria.search(
            query="dependência ausente requests",
            filters={"agent_id": _STACK_KEY},
            top_k=5,
        )
        memorias = resultado_busca.get("results", [])
        if not memorias:
            print("Falha: search() não retornou nenhuma memória após o add().")
            return 1

        print(f"search() OK — {len(memorias)} memória(s) encontrada(s):")
        for m in memorias:
            print(f"  - {m.get('memory')}")

        print("\nSmoke test OK.")
        return 0
    except Exception as exc:
        print(f"Smoke test falhou: {exc}")
        return 1


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
