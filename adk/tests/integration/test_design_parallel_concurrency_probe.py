"""Probe (não faz parte do deliverable): confirma empiricamente o que
acontece quando um branch de um ParallelAgent pausa (long-running) enquanto
o branch irmao ainda esta rodando. Reproduz a topologia real do
parallel_branch (prototyping_specialist + diagram_flow[mermaid, validator,
markdown])."""

from typing import AsyncGenerator
import asyncio

import pytest
from google.adk.agents import BaseAgent, SequentialAgent, ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import ConfigDict


class _PausesImmediately(BaseAgent):
    """Simula o validator: pausa (long-running) na primeira invocacao."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        if ctx.user_content and ctx.user_content.parts:
            for p in ctx.user_content.parts:
                fr = getattr(p, "function_response", None)
                if fr is not None:
                    yield Event(
                        author=self.name, invocation_id=ctx.invocation_id,
                        content=types.Content(role="model", parts=[
                            types.Part(text=f"validator retomou: {fr.response.get('decision')}")
                        ]),
                    )
                    return
        fc = types.FunctionCall(
            id="call-validator-1", name="aguardar_decisao_validacao",
            args={"checkpoint_id": "diagrama-x", "approval_question": "?", "allowed_decisions": ["resolvido", "abandonar_artefato"]},
        )
        yield Event(
            author=self.name, invocation_id=ctx.invocation_id,
            content=types.Content(role="model", parts=[types.Part(function_call=fc)]),
            long_running_tool_ids={"call-validator-1"},
        )


class _SlowSibling(BaseAgent):
    """Simula o prototyping_specialist: continua trabalhando por N ticks,
    independente do que acontece no branch irmao."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    ticks_emitted: list = []

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        for i in range(3):
            await asyncio.sleep(0.05)  # simula trabalho real (I/O, tool call)
            _SlowSibling.ticks_emitted.append(i)
            yield Event(
                author=self.name, invocation_id=ctx.invocation_id,
                content=types.Content(role="model", parts=[
                    types.Part(text=f"prototyping_specialist tick {i}")
                ]),
            )


@pytest.mark.asyncio
async def test_sibling_branch_continua_rodando_apos_pausa_do_outro_branch(monkeypatch):
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    _SlowSibling.ticks_emitted = []

    validator_stub = _PausesImmediately(name="validator_stub", description="pausa imediata")
    diagram_flow_stub = SequentialAgent(name="diagram_flow_stub", sub_agents=[validator_stub])
    slow_stub = _SlowSibling(name="prototyping_stub", description="trabalha 3 ticks")

    parallel_branch_stub = ParallelAgent(
        name="parallel_branch_stub", sub_agents=[slow_stub, diagram_flow_stub],
    )
    design_stub = SequentialAgent(name="design_pipeline", sub_agents=[parallel_branch_stub])

    monkeypatch.setattr(_PipelineOrchestrator, "_pipelines", [design_stub])

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    outer_runner = Runner(
        app_name="orchestrator", agent=orch,
        session_service=InMemorySessionService(), memory_service=InMemoryMemoryService(),
    )
    outer_session = await outer_runner.session_service.create_session(
        app_name="orchestrator", user_id="u", state={},
    )

    msg_t0 = types.Content(role="user", parts=[types.Part.from_text(text="prompt inicial")])
    events_t0 = [e async for e in outer_runner.run_async(
        user_id="u", session_id=outer_session.id, new_message=msg_t0,
    )]

    # 1) O branch irmao (prototyping) rodou TODOS os ticks, sem ser cancelado?
    assert _SlowSibling.ticks_emitted == [0, 1, 2], (
        f"prototyping_specialist foi interrompido/cancelado antes de terminar: "
        f"{_SlowSibling.ticks_emitted}"
    )

    # 2) O evento de pausa do validator realmente chegou ao orchestrator?
    has_long_running = any(e.long_running_tool_ids for e in events_t0 if e.long_running_tool_ids)
    assert has_long_running, "pausa do validator nao propagou"

    # 3) O estado de pausa foi persistido (so depois que os dois branches terminaram)?
    refreshed = await outer_runner.session_service.get_session(
        app_name="orchestrator", user_id="u", session_id=outer_session.id,
    )
    assert refreshed.state.get("paused_pipeline") == "design_pipeline"

    # 4) markdown_specialist (proximo do validator no diagram_flow real) nao
    #    deveria rodar - aqui simulado por ausencia de terceiro sub-agente,
    #    mas a checagem estrutural real esta no SequentialAgent (ver leitura
    #    de codigo da ADK: `if pause_invocation: return`).

    await outer_runner.close()
