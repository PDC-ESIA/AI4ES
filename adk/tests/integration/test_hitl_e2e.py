"""Integration: orchestrator real (sem LLM real) com agente stub que pausa.

Em vez de stubar Runner como no unit, aqui usamos o Runner real do ADK
contra um BaseAgent stub que emite um function_call long-running. Valida
a integração end-to-end com a infra ADK.
"""

from typing import AsyncGenerator

import pytest
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import ConfigDict


class _StubPausesOnce(BaseAgent):
    """Agente stub: na primeira invocação emite function_call long-running.

    Na segunda (recebendo function_response), emite texto final."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # Detecta function_response no user_content
        if ctx.user_content and ctx.user_content.parts:
            for p in ctx.user_content.parts:
                fr = getattr(p, "function_response", None)
                if fr is not None:
                    yield Event(
                        author=self.name,
                        invocation_id=ctx.invocation_id,
                        content=types.Content(
                            role="model",
                            parts=[types.Part(text=f"decisao recebida: {fr.response.get('decision')}")],
                        ),
                    )
                    return

        # Primeiro turno: emite long-running pendente
        fc = types.FunctionCall(
            id="call-stub-1",
            name="aguardar_aprovacao_humana",
            args={
                "checkpoint_id": "ck-stub",
                "approval_question": "?",
                "allowed_decisions": ["aprovar", "rejeitar"],
            },
        )
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            content=types.Content(role="model", parts=[types.Part(function_call=fc)]),
            long_running_tool_ids={"call-stub-1"},
        )


@pytest.mark.asyncio
async def test_orchestrator_pausa_real_e_resume_via_runner_adk(monkeypatch):
    """Integration: pausa real + resume através do Runner ADK."""
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    # Substitui os 4 pipelines do orchestrator por um único stub.
    stub = _StubPausesOnce(name="qa_pipeline", description="stub")
    monkeypatch.setattr(
        _PipelineOrchestrator,
        "_pipelines",
        [stub],
    )

    orch = _PipelineOrchestrator(name="orchestrator", description="test")

    # T0: invoca via Runner externo
    outer_runner = Runner(
        app_name="orchestrator",
        agent=orch,
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )
    outer_session = await outer_runner.session_service.create_session(
        app_name="orchestrator", user_id="u", state={},
    )

    msg_t0 = types.Content(role="user", parts=[types.Part.from_text(text="prompt inicial")])
    events_t0 = [e async for e in outer_runner.run_async(
        user_id="u", session_id=outer_session.id, new_message=msg_t0,
    )]

    # T0 deve ter emitido function_call long-running
    has_long_running = any(
        e.long_running_tool_ids for e in events_t0 if e.long_running_tool_ids
    )
    assert has_long_running, f"function_call long-running ausente em T0: {events_t0}"

    # State setado
    refreshed = await outer_runner.session_service.get_session(
        app_name="orchestrator", user_id="u", session_id=outer_session.id,
    )
    assert refreshed.state.get("paused_pipeline") == "qa_pipeline"
    assert outer_session.id in orch._live_runners

    # T1: envia "aprovar" como texto livre
    msg_t1 = types.Content(role="user", parts=[types.Part.from_text(text="aprovar")])
    events_t1 = [e async for e in outer_runner.run_async(
        user_id="u", session_id=outer_session.id, new_message=msg_t1,
    )]

    # T1 deve ter texto "decisao recebida: aprovar" do stub
    texts_t1 = [
        p.text for e in events_t1 if e.content
        for p in e.content.parts if p.text
    ]
    assert any("decisao recebida: aprovar" in t for t in texts_t1), (
        f"resume não chegou ao stub: {texts_t1}"
    )

    # State limpo
    refreshed = await outer_runner.session_service.get_session(
        app_name="orchestrator", user_id="u", session_id=outer_session.id,
    )
    assert refreshed.state.get("paused_pipeline") is None
    assert outer_session.id not in orch._live_runners

    await outer_runner.close()
