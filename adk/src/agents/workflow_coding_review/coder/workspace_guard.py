"""Proteção determinística contra sobrescrita cega entre tasks do coder."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any, MutableMapping

from shared.workspace import get_agent_workspace

CHAVE_ARQUIVOS_HERDADOS = "coder_arquivos_herdados_da_task"


def preparar_arquivos_herdados(
    state: MutableMapping[str, Any], *, primeira: bool
) -> None:
    """Registra os arquivos que já existiam antes da task corrente.

    Na primeira task o projeto ainda está sendo materializado, portanto não há
    proteção contra sobrescrita integral. Nas seguintes, a fotografia permanece
    imutável durante todos os retries da mesma task.
    """
    if primeira:
        state[CHAVE_ARQUIVOS_HERDADOS] = []
        return

    raiz = get_agent_workspace("cr_coder")
    state[CHAVE_ARQUIVOS_HERDADOS] = sorted(
        caminho.relative_to(raiz).as_posix()
        for caminho in raiz.rglob("*")
        if caminho.is_file()
    )


def _normalizar_caminho(caminho: object) -> str | None:
    """Normaliza um caminho relativo da tool ou devolve None se for inseguro."""
    if not isinstance(caminho, str) or not caminho.strip():
        return None
    texto = caminho.strip().replace("\\", "/")
    path = PurePosixPath(texto)
    if path.is_absolute() or ".." in path.parts:
        return None
    normalizado = path.as_posix()
    return None if normalizado in ("", ".") else normalizado


def bloquear_sobrescrita_herdada(tool, args, tool_context) -> dict | None:
    """Impede ``tool_criar_arquivo`` de sobrescrever arquivo de task anterior.

    Arquivos novos da task atual continuam livres, inclusive em retries. Um
    arquivo herdado pode ser modificado conscientemente após leitura usando
    ``tool_substituir_trecho``; apenas a substituição integral e cega é barrada.
    """
    if getattr(tool, "name", None) != "tool_criar_arquivo":
        return None

    herdados = tool_context.state.get(CHAVE_ARQUIVOS_HERDADOS)
    if herdados is None:
        # Execuções diretas do coder, fora do TaskIterator, preservam o
        # comportamento legado porque não possuem baseline por task.
        return None
    if not isinstance(herdados, list):
        return {
            "sucesso": False,
            "codigo": "BASELINE_DA_TASK_INVALIDA",
            "erro": (
                "A fotografia dos arquivos anteriores desta task está inválida; "
                "a sobrescrita integral foi bloqueada por segurança."
            ),
            "caminho": args.get("caminho"),
        }

    caminho = _normalizar_caminho(args.get("caminho"))
    if caminho is None or caminho not in set(herdados):
        return None

    return {
        "sucesso": False,
        "codigo": "SOBRESCRITA_INTER_TASK_BLOQUEADA",
        "erro": (
            f"O arquivo '{caminho}' já existia antes da task atual e não pode "
            "ser sobrescrito integralmente com tool_criar_arquivo. Leia-o com "
            "tool_ler_arquivo e altere somente o trecho necessário usando "
            "tool_substituir_trecho. Não recrie o projeto nem o PLAN.md."
        ),
        "caminho": caminho,
    }
