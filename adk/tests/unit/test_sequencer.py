"""
test_sequencer.py
=================
Testes unitários para o sequenciador: contrato, resiliência e runner.

Execute com:
    uv run pytest tests/unit/test_sequencer.py -v --tb=short
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Garante que o diretório adk/ esteja no sys.path para imports absolutos.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.workflows.sequencer.contract import PIPELINE_STAGES, stage_index, validate_state
from agents.workflows.sequencer.resilience import (
    SequencerError,
    _record_failure,
    run_with_resilience,
)


# ===========================================================================
# Helpers
# ===========================================================================


def _full_state() -> dict:
    """Retorna um session_state com todas as output_keys preenchidas."""
    return {stage["output_key"]: f"mock_{stage['output_key']}" for stage in PIPELINE_STAGES}


class _FakeEvent:
    """Evento stub para testes de run_with_resilience."""

    def __init__(self, label: str = "evt"):
        self.label = label


def _make_fake_agent(events=None, *, raises=None, sleep_seconds=0.0):
    """Cria um agente mock cujo ``run_async`` é um async generator."""
    agent = MagicMock()
    agent.name = "fake_agent"

    async def _run_async(ctx):
        if sleep_seconds > 0:
            await asyncio.sleep(sleep_seconds)
        if raises is not None:
            raise raises
        for evt in (events or []):
            yield evt

    agent.run_async = _run_async
    return agent


# ===========================================================================
# 1. test_stage_index_por_name
# ===========================================================================


class TestStageIndex:

    def test_stage_index_por_name(self):
        """stage_index('requirements_agent') retorna 0."""
        assert stage_index("requirements_agent") == 0

    def test_stage_index_por_output_key(self):
        """stage_index('requirements') retorna 0."""
        assert stage_index("requirements") == 0

    def test_stage_index_todos_por_name(self):
        """Cada agent name deve retornar o índice correto."""
        for i, stage in enumerate(PIPELINE_STAGES):
            assert stage_index(stage["name"]) == i

    def test_stage_index_todos_por_output_key(self):
        """Cada output_key deve retornar o índice correto."""
        for i, stage in enumerate(PIPELINE_STAGES):
            assert stage_index(stage["output_key"]) == i

    def test_stage_index_inexistente(self):
        """stage_index('nao_existe') levanta KeyError."""
        with pytest.raises(KeyError, match="nao_existe"):
            stage_index("nao_existe")


# ===========================================================================
# 2. test_validate_state
# ===========================================================================


class TestValidateState:

    def test_validate_state_completo(self):
        """Todas as 6 chaves presentes → (True, [])."""
        ok, missing = validate_state(_full_state())
        assert ok is True
        assert missing == []

    def test_validate_state_parcial(self):
        """up_to_stage=2 com 3 primeiras chaves presentes → (True, [])."""
        state = {}
        for stage in PIPELINE_STAGES[:3]:
            state[stage["output_key"]] = "ok"
        ok, missing = validate_state(state, up_to_stage=2)
        assert ok is True
        assert missing == []

    def test_validate_state_chave_ausente(self):
        """Chave faltando → (False, ['chave'])."""
        state = _full_state()
        del state["architecture"]
        ok, missing = validate_state(state)
        assert ok is False
        assert "architecture" in missing

    def test_validate_state_vazio(self):
        """Estado vazio → todas as 6 chaves ausentes."""
        ok, missing = validate_state({})
        assert ok is False
        assert len(missing) == 6

    def test_validate_state_parcial_nao_inclui_alem(self):
        """up_to_stage=1 não deve reclamar de chaves do estágio 2+."""
        state = {"requirements": "ok", "architecture": "ok"}
        ok, missing = validate_state(state, up_to_stage=1)
        assert ok is True
        assert missing == []


# ===========================================================================
# 3. test_sequencer_error
# ===========================================================================


class TestSequencerError:

    def test_sequencer_error_atributos(self):
        """SequencerError('timeout', 'msg', 'agente') carrega os 3 atributos."""
        err = SequencerError("timeout", "excedeu 300s", "requirements_agent")
        assert err.error_type == "timeout"
        assert err.detail == "excedeu 300s"
        assert err.failed_at == "requirements_agent"

    def test_sequencer_error_str(self):
        """A representação string contém tipo e detalhe."""
        err = SequencerError("api_error", "Connection refused")
        assert "[api_error]" in str(err)
        assert "Connection refused" in str(err)

    def test_sequencer_error_is_exception(self):
        """SequencerError deve ser subclasse de Exception."""
        assert issubclass(SequencerError, Exception)


# ===========================================================================
# 4. test_record_failure
# ===========================================================================


class TestRecordFailure:

    def test_record_failure_escreve_state(self):
        """_record_failure escreve sequencer_error, error_detail, failed_at."""
        state: dict = {}
        _record_failure(state, "timeout", "excedeu 300s", "coder_agent")
        assert state["sequencer_error"] == "timeout"
        assert state["error_detail"] == "excedeu 300s"
        assert state["failed_at"] == "coder_agent"

    def test_record_failure_sem_failed_at(self):
        """Sem failed_at, a chave não deve ser criada."""
        state: dict = {}
        _record_failure(state, "api_error", "erro genérico")
        assert state["sequencer_error"] == "api_error"
        assert "failed_at" not in state


# ===========================================================================
# 5. test_run_with_resilience
# ===========================================================================


class TestRunWithResilience:

    @pytest.mark.asyncio
    async def test_run_with_resilience_sucesso(self):
        """Agente mock que retorna eventos → lista de eventos."""
        events = [_FakeEvent("a"), _FakeEvent("b")]
        agent = _make_fake_agent(events)
        state: dict = {}

        result = await run_with_resilience(
            agent=agent,
            ctx=MagicMock(),
            session_state=state,
            timeout_seconds=5.0,
            failed_at="fake_agent",
        )

        assert len(result) == 2
        assert result[0].label == "a"
        assert result[1].label == "b"
        assert "sequencer_error" not in state

    @pytest.mark.asyncio
    async def test_run_with_resilience_timeout(self):
        """Agente que dorme > timeout → SequencerError(error_type='timeout')."""
        agent = _make_fake_agent(sleep_seconds=10.0)
        state: dict = {}

        with pytest.raises(SequencerError) as exc_info:
            await run_with_resilience(
                agent=agent,
                ctx=MagicMock(),
                session_state=state,
                timeout_seconds=0.05,
                failed_at="slow_agent",
            )

        assert exc_info.value.error_type == "timeout"
        assert state["sequencer_error"] == "timeout"
        assert state["failed_at"] == "slow_agent"

    @pytest.mark.asyncio
    async def test_run_with_resilience_api_error(self):
        """Agente que levanta Exception → SequencerError(error_type='api_error')."""
        agent = _make_fake_agent(raises=ConnectionError("Connection refused"))
        state: dict = {}

        with pytest.raises(SequencerError) as exc_info:
            await run_with_resilience(
                agent=agent,
                ctx=MagicMock(),
                session_state=state,
                timeout_seconds=5.0,
                failed_at="broken_agent",
            )

        assert exc_info.value.error_type == "api_error"
        assert state["sequencer_error"] == "api_error"
        assert "Connection refused" in state["error_detail"]
        assert state["failed_at"] == "broken_agent"


# ===========================================================================
# 6. test_pipeline / runner instanciação
# ===========================================================================


class TestPipelineStagesOrdem:

    def test_pipeline_stages_ordem(self):
        """Ordem: requirements → architecture → test_plan → implementation → review → finalization."""
        expected_keys = [
            "requirements",
            "architecture",
            "test_plan",
            "implementation",
            "review",
            "finalization",
        ]
        actual_keys = [s["output_key"] for s in PIPELINE_STAGES]
        assert actual_keys == expected_keys


class TestResilientSequencerInstancia:

    def test_resilient_sequencer_instancia(self):
        """root_agent instancia sem erro, wrapped_pipeline.name == 'sdlc_pipeline'."""
        from runners.sequencer.agent import root_agent

        assert root_agent.name == "resilient_sequencer"
        assert root_agent.wrapped_pipeline.name == "sdlc_pipeline"

    def test_pipeline_sub_agents_count(self):
        """O pipeline envolvido deve ter 6 sub-agentes."""
        from runners.sequencer.agent import root_agent

        assert len(root_agent.wrapped_pipeline.sub_agents) == 6

    def test_pipeline_sub_agents_names(self):
        """Os nomes dos sub-agentes devem corresponder ao contrato."""
        from runners.sequencer.agent import root_agent

        expected = [s["name"] for s in PIPELINE_STAGES]
        actual = [a.name for a in root_agent.wrapped_pipeline.sub_agents]
        assert actual == expected
