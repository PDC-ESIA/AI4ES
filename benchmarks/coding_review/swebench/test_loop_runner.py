"""Testes das partes puras do `loop_runner` (sem LLM e sem Docker)."""

from __future__ import annotations

import json
from enum import Enum

from benchmarks.coding_review.swebench import loop_runner
from benchmarks.coding_review.swebench._testutils import ADK_DIR, module_constant
from benchmarks.coding_review.swebench.contract import TASK_ID
from benchmarks.coding_review.swebench.dataset import SWEInstance
from benchmarks.coding_review.swebench.metrics import MOTIVOS_ERRO

HARNESS_SCHEMAS = ADK_DIR / "shared/tools/coding_tools/harness_schemas.py"


class _Status(str, Enum):
    APROVADO = "aprovado"


def test_nomes_de_estagio_batem_com_o_harness():
    assert module_constant(HARNESS_SCHEMAS, "PREPARACAO_AMBIENTE") == loop_runner.STAGE_PREPARACAO
    assert module_constant(HARNESS_SCHEMAS, "TESTES_AUTOMATIZADOS") == loop_runner.STAGE_TESTES


def test_motivos_de_erro_da_instancia_sao_conhecidos_pelas_metricas():
    assert {loop_runner.MOTIVO_ERRO_OPERACIONAL, loop_runner.MOTIVO_TIMEOUT,
            loop_runner.MOTIVO_ESTOURO_CONTEXTO} == MOTIVOS_ERRO


def test_resumo_do_execution_report():
    report = {
        "iteration": 3,
        "overall_status": "sucesso",
        "stages": [
            {"stage": "preparacao_ambiente", "status": "sucesso",
             "evidence": {"test_commands": ["python -m pytest t.py"]}},
            {"stage": "testes_automatizados", "status": "sucesso",
             "evidence": {"testes_identificados": 4, "resultados": [
                 {"resumo": {"passaram": 3, "falharam": 1, "erros": 0}},
                 {"resumo": {"passaram": 1, "falharam": 0, "erros": True}},
             ]}},
        ],
    }
    resumo = loop_runner.summarize_execution_report(report)
    assert resumo == {
        "iteracao": 3,
        "overall_status": "sucesso",
        "test_commands": ["python -m pytest t.py"],
        "status_testes": "sucesso",
        "testes_identificados": 4,
        "passaram": 4,
        "falharam": 1,
        "erros": 0,
    }
    assert loop_runner.summarize_execution_report(None) == {}


def test_veredito_do_validador():
    def state(**validation):
        return {"validation": validation}

    assert loop_runner.validator_verdict(state(work_item_id=TASK_ID, status="aprovado")) == "aprovado"
    assert loop_runner.validator_verdict(
        state(work_item_id=TASK_ID, status=_Status.APROVADO)
    ) == "aprovado"
    assert loop_runner.validator_verdict(state(work_item_id="TASK-999", status="aprovado")) is None
    assert loop_runner.validator_verdict({}) is None


def test_grava_a_task_onde_o_harness_procura(tmp_path):
    inst = SWEInstance(
        instance_id="a__a-1", repo="a/a", base_commit="x", version="1",
        problem_statement="p", image="i",
    )
    caminho = loop_runner.write_task_file(tmp_path / "tasks", inst)
    assert caminho.name == f"{TASK_ID}.json"
    assert json.loads(caminho.read_text())["requirement_id"] == "a__a-1"


def test_json_safe_converte_enum():
    assert loop_runner.json_safe({"s": _Status.APROVADO}) == {"s": "aprovado"}


def test_estouro_de_contexto_tem_rotulo_proprio():
    copilot = ("BadRequestError: litellm.BadRequestError: Github_copilotException - prompt "
               "token count of 169117 exceeds the limit of 128000")
    assert loop_runner.is_context_overflow(copilot)
    assert loop_runner.is_context_overflow("ContextWindowExceededError: maximum context length")
    assert not loop_runner.is_context_overflow("ValueError: outra coisa")
    assert loop_runner.motivo_do_erro(copilot, timed_out=False) == "estouro_de_contexto"
    assert loop_runner.motivo_do_erro("ValueError: x", timed_out=False) == "erro_operacional"
    assert loop_runner.motivo_do_erro(copilot, timed_out=True) == "timeout_da_instancia"


# --- teto por instância: conta o trabalho, não a espera do controle de ritmo ----


def _tarefa_que_termina_em(clock, fim: float, retorno=None, erro: Exception | None = None):
    """Tarefa de verdade, cujo "fim" depende do relógio simulado."""
    import asyncio

    async def _corpo():
        while clock.agora < fim:
            await asyncio.sleep(0)
        if erro is not None:
            raise erro
        return retorno

    return asyncio.ensure_future(_corpo())


class _RelogioSimulado:
    """Cada `wait` do helper avança o tempo, sem dormir de verdade."""

    def __init__(self):
        self.agora = 0.0

    def __call__(self):
        return self.agora


def test_teto_estoura_quando_o_trabalho_passa_do_limite():
    import asyncio

    clock = _RelogioSimulado()
    tarefa = None

    async def _main():
        nonlocal tarefa
        tarefa = _tarefa_que_termina_em(clock, fim=10_000)
        original_wait = asyncio.wait

        async def _wait(fs, timeout=None):
            clock.agora += timeout or 0
            return await original_wait(fs, timeout=0)

        asyncio.wait = _wait
        try:
            await loop_runner.aguardar_com_teto(
                tarefa, timeout_s=100, pausado_s=lambda: 0.0, clock=clock, intervalo_s=10.0
            )
        finally:
            asyncio.wait = original_wait

    import pytest

    with pytest.raises(TimeoutError):
        asyncio.run(_main())
    assert tarefa.cancelled()
    assert 100 <= clock.agora <= 110


def test_pausas_nao_contam_para_o_teto():
    import asyncio

    clock = _RelogioSimulado()

    async def _main():
        # Trabalho de 60 s + 400 s dormindo: 460 s de relógio, mas só 60 s de trabalho.
        tarefa = _tarefa_que_termina_em(clock, fim=460, retorno="ok")
        original_wait = asyncio.wait

        async def _wait(fs, timeout=None):
            clock.agora += timeout or 0
            return await original_wait(fs, timeout=0)

        asyncio.wait = _wait
        try:
            await loop_runner.aguardar_com_teto(
                tarefa, timeout_s=100,
                pausado_s=lambda: min(400.0, clock.agora), clock=clock, intervalo_s=10.0,
            )
        finally:
            asyncio.wait = original_wait
        return tarefa.result()

    assert asyncio.run(_main()) == "ok"
    assert clock.agora >= 460


def test_erro_da_tarefa_e_repropagado():
    import asyncio

    import pytest

    clock = _RelogioSimulado()

    async def _main():
        tarefa = _tarefa_que_termina_em(clock, fim=0, erro=ValueError("falhou"))
        await loop_runner.aguardar_com_teto(
            tarefa, timeout_s=100, pausado_s=lambda: 0.0, clock=clock, intervalo_s=10.0
        )

    with pytest.raises(ValueError, match="falhou"):
        asyncio.run(_main())
