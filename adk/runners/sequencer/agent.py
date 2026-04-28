"""Entry point ADK — expõe ResilientSequencer como runner standalone.

O ``ResilientSequencer`` envolve o ``sdlc_pipeline`` (SequentialAgent)
adicionando:
  • timeout por sub-agente (centralizado em ``resilience.run_with_resilience``);
  • validação de contrato após cada etapa (via ``contract.validate_state``);
  • registro estruturado de falhas em ``session.state``.
"""

from __future__ import annotations

from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from agents.workflows.sequencer.contract import stage_index, validate_state
from agents.workflows.sequencer.resilience import (
    SequencerError,
    _record_failure,
    run_with_resilience,
)
from agents.workflows.coding.agent import agent as sdlc_pipeline

# Timeout padrão por sub-agente (segundos).
_TIMEOUT_SECONDS: float = 300.0


class ResilientSequencer(BaseAgent):
    """Runner resiliente que executa o pipeline SDLC com tolerância a falhas."""

    wrapped_pipeline: BaseAgent

    @property
    def _sub_agents(self) -> list[BaseAgent]:
        """Expõe os sub-agentes do pipeline envolvido para o ADK."""
        return [self.wrapped_pipeline]

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        session_state = ctx.session.state
        session_state["sequencer_status"] = "running"

        for sub_agent in self.wrapped_pipeline.sub_agents:
            agent_name = sub_agent.name

            # Delega timeout + interceptação para resilience.py
            # COMO FICA (Streaming):
            async for event in run_with_resilience(
                agent=sub_agent,
                ctx=ctx,
                session_state=session_state,
                timeout_seconds=_TIMEOUT_SECONDS,
                failed_at=agent_name,
            ):
                yield event

            # Validação de contrato — stage_index aceita agent_name
            idx = stage_index(agent_name)
            is_valid, missing_keys = validate_state(session_state, up_to_stage=idx)

            if not is_valid:
                detail = (
                    f"Contrato quebrado após '{agent_name}'. "
                    f"Chaves ausentes: {missing_keys}"
                )
                _record_failure(session_state, "schema_violation", detail, agent_name)
                raise SequencerError("schema_violation", detail, agent_name)

        session_state["sequencer_status"] = "completed"


root_agent = ResilientSequencer(
    name="resilient_sequencer",
    description=(
        "Sequenciador resiliente que executa o pipeline SDLC "
        "com timeout, validação de contrato e tratamento de falhas."
    ),
    wrapped_pipeline=sdlc_pipeline,
)
