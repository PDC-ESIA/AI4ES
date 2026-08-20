"""Log local de erros brutos entre execuções — PoC de memória em lote.

Essa camada não precisa de Postgres — é só um arquivo
local por stack, que o `reviewer` acumula a cada reprovação e processa em
lote quando atinge `limite_lote()`. Só o que sobrevive ao lote (erro que se
repetiu) vira lição gravada no mem0 (ver `reviewer/agent.py::_escrever_memoria`)
— este módulo cuida exclusivamente do log bruto, antes desse filtro.

Um arquivo JSONL por stack_key, dentro de `memory_store/error_log/` — mesma
pasta-base usada pelo fallback local do mem0 (`shared/memory/config.py`),
fora de `WORKSPACE_OUTPUT_DIR` para sobreviver à limpeza do workspace a cada
execução nova, e já coberta pelo `.gitignore` (`adk/memory_store/`).
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def _dir_error_log() -> Path:
    override = os.environ.get("AI4ES_MEMORY_DIR")
    raiz = (
        Path(override)
        if override
        else Path(__file__).resolve().parents[2] / "memory_store"
    )
    return raiz / "error_log"


def _arquivo_stack(stack_key: str) -> Path:
    diretorio = _dir_error_log()
    diretorio.mkdir(parents=True, exist_ok=True)
    return diretorio / f"{stack_key}.jsonl"


def registrar_erros(stack_key: str, entradas: list[dict]) -> None:
    """Acrescenta entradas ao log bruto da stack (append-only, uma por linha)."""
    if not entradas:
        return
    caminho = _arquivo_stack(stack_key)
    with caminho.open("a", encoding="utf-8") as f:
        for entrada in entradas:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")


def ler_erros_pendentes(stack_key: str) -> list[dict]:
    """Lê todas as entradas ainda não processadas daquela stack."""
    caminho = _arquivo_stack(stack_key)
    if not caminho.exists():
        return []
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    return [json.loads(linha) for linha in linhas if linha.strip()]


def limpar_erros_pendentes(stack_key: str) -> None:
    """Remove o log da stack após um lote ser processado."""
    caminho = _arquivo_stack(stack_key)
    if caminho.exists():
        caminho.unlink()


def limite_lote() -> int:
    """Quantidade de erros acumulados que dispara o processamento em lote.

    Trata valor ausente OU vazio como "não configurado" (usa o default) —
    `.env` costuma deixar a chave presente e vazia, não ausente.
    """
    valor = os.environ.get("AI4ES_MEMORY_BATCH_THRESHOLD", "").strip()
    return int(valor) if valor else 3
