"""
test_sequencer.py
=================
Testes unitários para o agente sequenciador: contrato, resiliência e runner.

Execute com:
    pytest test_sequencer.py -v
"""

import asyncio
import sys
from pathlib import Path

import pytest

# Garante que o diretório adk/ esteja no sys.path para imports absolutos.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.sequencer.contract import PIPELINE_STAGES, validate_state
from agents.sequencer.resilience import SequencerError, run_with_resilience


# ===========================================================================
# Testes: contrato (PIPELINE_STAGES + validate_state)
# ===========================================================================


class TestPipelineStages:

    def test_pipeline_stages_count(self):
        """O pipeline deve conter exatamente 6 estágios."""
        assert len(PIPELINE_STAGES) == 6

    def test_pipeline_stages_order(self):
        """Os estágios devem seguir a ordem do SDLC."""
        expected_names = [
            "requirements_agent",
            "architecture_agent",
            "test_planning_agent",
            "coder_agent",
            "review_agent",
            "finalization_agent",
        ]
        actual_names = [s["name"] for s in PIPELINE_STAGES]
        assert actual_names == expected_names

    def test_pipeline_stages_output_keys(self):
        """Cada estágio deve declarar um output_key não-vazio."""
        for stage in PIPELINE_STAGES:
            assert "output_key" in stage, f"{stage['name']} sem output_key"
            assert stage["output_key"], f"{stage['name']} com output_key vazio"

    def test_pipeline_stages_have_schema(self):
        """Cada estágio deve referenciar um output_schema."""
        for stage in PIPELINE_STAGES:
            assert "output_schema" in stage, f"{stage['name']} sem output_schema"
            assert stage["output_schema"] is not None


class TestValidateState:

    @pytest.fixture
    def full_state(self):
        """Estado completo com todas as output_keys preenchidas."""
        return {stage["output_key"]: "mock_value" for stage in PIPELINE_STAGES}

    def test_all_keys_present(self, full_state):
        """Deve retornar (True, []) quando todas as chaves existem."""
        ok, missing = validate_state(full_state)
        assert ok is True
        assert missing == []

    def test_missing_single_key(self, full_state):
        """Deve detectar uma chave ausente."""
        del full_state["architecture"]
        ok, missing = validate_state(full_state)
        assert ok is False
        assert "architecture" in missing

    def test_missing_multiple_keys(self):
        """Deve listar todas as chaves ausentes."""
        ok, missing = validate_state({})
        assert ok is False
        assert len(missing) == 6

    def test_up_to_stage_partial(self, full_state):
        """Valida apenas até o estágio indicado (inclusive)."""
        # Remove chave do último estágio — não deve afetar validação parcial
        del full_state["finalization"]
        ok, missing = validate_state(full_state, up_to_stage="review_agent")
        assert ok is True
        assert missing == []

    def test_up_to_stage_with_missing(self):
        """Detecta chave ausente dentro do range parcial."""
        state = {"requirements": "ok"}
        ok, missing = validate_state(state, up_to_stage="architecture_agent")
        assert ok is False
        assert "architecture" in missing
        # Não deve incluir chaves além do estágio indicado
        assert "test_plan" not in missing

    def test_up_to_stage_first_only(self, full_state):
        """Valida apenas o primeiro estágio."""
        ok, missing = validate_state(full_state, up_to_stage="requirements_agent")
        assert ok is True
        assert missing == []

    def test_up_to_stage_first_missing(self):
        """Detecta chave ausente no primeiro estágio."""
        ok, missing = validate_state({}, up_to_stage="requirements_agent")
        assert ok is False
        assert missing == ["requirements"]


# ===========================================================================
# Testes: resiliência (SequencerError + run_with_resilience)
# ===========================================================================


class TestSequencerError:

    def test_error_attributes(self):
        """SequencerError deve carregar error_type e detail."""
        err = SequencerError(error_type="timeout", detail="Excedeu 300s")
        assert err.error_type == "timeout"
        assert err.detail == "Excedeu 300s"

    def test_error_str(self):
        """A representação string deve conter tipo e detalhe."""
        err = SequencerError("api_error", "Connection refused")
        assert "[api_error]" in str(err)
        assert "Connection refused" in str(err)

    def test_error_is_exception(self):
        """SequencerError deve ser subclasse de Exception."""
        assert issubclass(SequencerError, Exception)


class TestRunWithResilience:

    @pytest.mark.asyncio
    async def test_success_passthrough(self):
        """Deve retornar o resultado quando a coroutine tem sucesso."""
        async def success_coro():
            return "ok"

        state = {}
        result = await run_with_resilience(success_coro(), state)
        assert result == "ok"
        assert "sequencer_error" not in state

    @pytest.mark.asyncio
    async def test_timeout_raises_sequencer_error(self):
        """Deve capturar TimeoutError e lançar SequencerError."""
        async def slow_coro():
            await asyncio.sleep(10)

        state = {}
        with pytest.raises(SequencerError) as exc_info:
            await run_with_resilience(
                slow_coro(),
                state,
                timeout_seconds=0.01,
                current_agent_name="test_agent",
            )

        assert exc_info.value.error_type == "timeout"
        assert state["sequencer_error"] == "timeout"
        assert state["failed_at"] == "test_agent"

    @pytest.mark.asyncio
    async def test_api_error_raises_sequencer_error(self):
        """Deve capturar exceções genéricas como api_error."""
        async def failing_coro():
            raise ConnectionError("Connection refused")

        state = {}
        with pytest.raises(SequencerError) as exc_info:
            await run_with_resilience(
                failing_coro(),
                state,
                current_agent_name="coder_agent",
            )

        assert exc_info.value.error_type == "api_error"
        assert state["sequencer_error"] == "api_error"
        assert "Connection refused" in state["error_detail"]
        assert state["failed_at"] == "coder_agent"

    @pytest.mark.asyncio
    async def test_validation_error_raises_sequencer_error(self):
        """Deve capturar ValidationError como schema_violation."""
        from pydantic import BaseModel

        class Strict(BaseModel):
            x: int

        async def schema_fail_coro():
            Strict(x="not_an_int")  # type: ignore[arg-type]

        state = {}
        with pytest.raises(SequencerError) as exc_info:
            await run_with_resilience(schema_fail_coro(), state)

        assert exc_info.value.error_type == "schema_violation"
        assert state["sequencer_error"] == "schema_violation"

    @pytest.mark.asyncio
    async def test_no_state_pollution_on_success(self):
        """Estado não deve conter chaves de erro após sucesso."""
        async def ok():
            return 42

        state = {"existing_key": "value"}
        await run_with_resilience(ok(), state)
        assert "sequencer_error" not in state
        assert "error_detail" not in state
        assert "failed_at" not in state
        assert state["existing_key"] == "value"


# ===========================================================================
# Testes: sdlc_pipeline e runner
# ===========================================================================


class TestSdlcPipeline:

    def test_sub_agents_count(self):
        """O sdlc_pipeline deve ter exatamente 6 sub-agentes."""
        from agents.workflows.coding.agent import agent as sdlc_pipeline

        assert len(sdlc_pipeline.sub_agents) == 6

    def test_sub_agents_names(self):
        """Os nomes dos sub-agentes devem corresponder aos esperados."""
        from agents.workflows.coding.agent import agent as sdlc_pipeline

        expected = [
            "requirements_agent",
            "architecture_agent",
            "test_planning_agent",
            "coder_agent",
            "review_agent",
            "finalization_agent",
        ]
        actual = [a.name for a in sdlc_pipeline.sub_agents]
        assert actual == expected


class TestSequencerRunner:

    def test_runner_exports_root_agent(self):
        """O runner deve exportar root_agent como sdlc_pipeline."""
        from runners.sequencer.agent import root_agent
        from agents.workflows.coding.agent import agent as sdlc_pipeline

        assert root_agent is sdlc_pipeline
