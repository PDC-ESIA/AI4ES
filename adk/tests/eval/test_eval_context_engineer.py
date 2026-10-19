"""Avaliação do `cr_context_engineer`, endereçado como sub-agente do pipeline de codificação.
Os argumentos das tools são texto livre do LLM, então a trajetória compara só nomes, e o
resultado é conferido em disco depois de cada execução, com workspace novo a cada uma."""

import json
from pathlib import Path

import pytest

MODULO = "src.agents.workflow_coding_review.agent"
AGENTE = "cr_context_engineer"

#: Escrito pelo `tool_emitir_manifesto_bloqueado` quando não acha o doubt do agente.
_DOUBT_SINTETICO = "Doubt_Artifact_manifesto_bloqueado"


def _conferir_tasks_persistidas(raiz: Path, execucao: int) -> None:
    """Contexto macro e ao menos uma task em `coder/tasks/`, válidos contra os schemas."""
    from src.agents.workflow_coding_review.context_engineer.schemas import (
        MacroContext,
        Task,
    )

    pasta = raiz / "coder" / "tasks"
    macro = pasta / "_macro_context.json"
    assert macro.is_file(), f"execução {execucao}: sem coder/tasks/{macro.name}"
    MacroContext.model_validate_json(macro.read_text(encoding="utf-8"))
    tasks = sorted(pasta.glob("TASK-*.json"))
    assert tasks, f"execução {execucao}: nenhuma TASK-*.json em coder/tasks/"
    for task in tasks:
        Task.model_validate_json(task.read_text(encoding="utf-8"))


def _conferir_bloqueio_persistido(raiz: Path, execucao: int) -> None:
    """O manifesto em `coder/` sai `blocked` e lista o doubt do agente, gravado antes dele."""
    manifesto = raiz / "coder" / "manifest.json"
    assert manifesto.is_file(), f"execução {execucao}: sem coder/manifest.json"
    dados = json.loads(manifesto.read_text(encoding="utf-8"))
    assert dados.get("status") == "blocked", (
        f"execução {execucao}: status={dados.get('status')!r}"
    )
    doubts = [d["id"] for d in dados.get("doubts", []) if d["id"] != _DOUBT_SINTETICO]
    assert doubts, f"execução {execucao}: o manifesto só lista o doubt sintético"


@pytest.mark.eval
async def test_protocolo_de_bloqueio_emite_as_tres_tools(
    workspace_semeado, evalset, rodar_eval, num_runs
):
    """Com requisitos bloqueados, chama as três tools do protocolo na ordem, até a que pausa o pipeline, e deixa o manifesto bloqueado com o seu doubt."""
    caminho = evalset("ce_protocolo_bloqueio")
    for execucao in range(1, num_runs + 1):
        raiz = workspace_semeado("projeto_completo")
        await rodar_eval(caminho, agent_module=MODULO, agent_name=AGENTE, num_runs=1)
        _conferir_bloqueio_persistido(raiz, execucao)


@pytest.mark.eval
async def test_nao_bloqueia_por_nome_de_arquivo_do_design(
    workspace_semeado, evalset, rodar_eval, num_runs
):
    """Não bloqueia só porque a análise técnica tem nome fora da convenção, e persiste contexto macro e tasks válidos."""
    caminho = evalset("ce_gate_nome_design")
    for execucao in range(1, num_runs + 1):
        raiz = workspace_semeado("projeto_design_torto")
        await rodar_eval(caminho, agent_module=MODULO, agent_name=AGENTE, num_runs=1)
        _conferir_tasks_persistidas(raiz, execucao)


@pytest.mark.eval
async def test_caminho_feliz_age_em_vez_de_narrar(
    workspace_semeado, evalset, rodar_eval, num_runs
):
    """Com requisitos e design completos, lê as duas fases e persiste contexto macro e tasks válidos, em vez de só anunciar."""
    caminho = evalset("ce_caminho_feliz")
    for execucao in range(1, num_runs + 1):
        raiz = workspace_semeado("projeto_completo")
        await rodar_eval(caminho, agent_module=MODULO, agent_name=AGENTE, num_runs=1)
        _conferir_tasks_persistidas(raiz, execucao)
