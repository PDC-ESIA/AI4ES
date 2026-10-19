"""Avaliação do `cr_coder_agent`, endereçado como sub-agente do pipeline de codificação.
A âncora é o disco: depois de cada execução, o gate de executabilidade do executor julga o projeto."""

import json
from pathlib import Path

import pytest

MODULO = "src.agents.workflow_coding_review.agent"
AGENTE = "cr_coder_agent"
CASO = "coder_cli"

_TAREFAS = Path(__file__).resolve().parent / "fixtures" / CASO / "coder" / "tasks"


def _conferir_contrato_do_caso(caminho_evalset: str) -> None:
    """Sem LLM: fixture e mensagem do caso validam contra os schemas do context engineer."""
    from src.agents.workflow_coding_review.context_engineer.schemas import (
        MacroContext,
        Task,
        TasksOutput,
    )

    macro = MacroContext.model_validate_json(
        (_TAREFAS / "_macro_context.json").read_text(encoding="utf-8")
    )
    task = Task.model_validate_json(
        (_TAREFAS / "TASK-001.json").read_text(encoding="utf-8")
    )
    caso = json.loads(Path(caminho_evalset).read_text(encoding="utf-8"))
    mensagem = caso["eval_cases"][0]["conversation"][0]["user_content"]["parts"][0]
    saida = TasksOutput.model_validate_json(mensagem["text"])
    assert saida.macro_context == macro and saida.tasks == [task], (
        "a mensagem do caso diverge do contrato em fixtures/coder_cli/coder/tasks/"
    )


@pytest.mark.eval
async def test_coder_entrega_projeto_que_o_executor_aceita(
    workspace_semeado, evalset, rodar_eval, num_runs
):
    """A partir do contrato de uma task de CLI, deixa em coder/src um projeto que o gate do executor aceita."""
    from shared.execution.manifest import load_manifest
    from shared.execution.verificador_executabilidade import verificar_executabilidade

    caminho = evalset(CASO)
    _conferir_contrato_do_caso(caminho)

    # O AgentEvaluator roda todas as execuções antes de medir; com o disco como
    # âncora, cada execução precisa de workspace novo e conferência própria.
    for execucao in range(1, num_runs + 1):
        src = workspace_semeado(CASO) / "coder" / "src"
        await rodar_eval(caminho, agent_module=MODULO, agent_name=AGENTE, num_runs=1)

        resultado = verificar_executabilidade(src)
        assert resultado.executavel, f"execução {execucao}: {resultado.bloqueios}"
        assert (src / "README.md").is_file(), f"execução {execucao}: sem README.md"
        surface = load_manifest(src / "run.json").surface
        assert surface == "command", (
            f"execução {execucao}: surface={surface!r}; product_type 'cli' pede 'command'"
        )
