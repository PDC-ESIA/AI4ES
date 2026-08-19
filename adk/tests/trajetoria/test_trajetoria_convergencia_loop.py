"""Camada 2 (trajetória): convergência/esgotamento do LoopAgent `code_execute_loop`.

Gap coberto: os testes existentes de `cr_coder`, `cr_executor` e do pipeline
`workflow_coding_review` (Camada 1) validam o *wiring* de cada agente
isoladamente (nome, tools, prompt), mas nenhum teste exercita o `LoopAgent`
real do ADK (`_code_execute_loop`, sub_agents=[coder, executor],
max_iterations configurável) através de múltiplas iterações efetivas.

Isso deixa dois comportamentos de trajetória sem cobertura, ambos
essenciais para a garantia descrita em `agent.py` ("o LoopAgent garante
que o código produzido é EXECUTÁVEL antes de seguir para revisão"):

1. **Convergência**: quando o executor sinaliza aprovação (`exit_loop` →
   `actions.escalate=True`), o `LoopAgent` do ADK realmente para de
   iterar, na iteração em que a aprovação ocorreu — nem antes, nem depois.
2. **Encerramento controlado por esgotamento**: quando o executor nunca
   aprova, o `LoopAgent` para exatamente em `max_iterations` (o teto de
   segurança), sem travar e sem produzir uma falsa aprovação.

Ambos os testes rodam o `Runner` real do ADK (mesmo padrão de
`test_hitl_e2e.py`) contra stubs de `BaseAgent` que substituem coder e
executor via `monkeypatch.setattr(_code_execute_loop, "sub_agents", ...)`,
para exercitar a máquina de iteração real do `LoopAgent` sem depender de
LLM.
"""

from typing import AsyncGenerator

import pytest
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import ConfigDict

from src.agents.workflow_coding_review.agent import _code_execute_loop


class _StubCoder(BaseAgent):
    """Stub do `cr_coder_agent`: emite texto simulando "código corrigido"."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    trace_collector: object = None

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        self.trace_collector.record(agente="cr_coder_agent", acao="corrigir_codigo")
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="codigo corrigido")],
            ),
        )


class _StubExecutorConverge(BaseAgent):
    """Stub do `cr_executor_agent`: reprova 2x, aprova (escalate=True) na 3ª."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    trace_collector: object = None
    invocacoes: int = 0

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        self.invocacoes += 1

        if self.invocacoes < 3:
            self.trace_collector.record(
                agente="cr_executor_agent", acao="veredito", status="reprovado",
            )
            yield Event(
                author=self.name,
                invocation_id=ctx.invocation_id,
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text="veredito: reprovado")],
                ),
            )
            return

        self.trace_collector.record(
            agente="cr_executor_agent", acao="veredito", status="aprovado",
        )
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="veredito: aprovado")],
            ),
            actions=EventActions(escalate=True),
        )


class _StubExecutorNuncaAprova(BaseAgent):
    """Stub do `cr_executor_agent`: reprova sempre, nunca chama exit_loop."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    trace_collector: object = None
    invocacoes: int = 0

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        self.invocacoes += 1
        self.trace_collector.record(
            agente="cr_executor_agent", acao="veredito", status="reprovado",
        )
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="veredito: reprovado")],
            ),
        )


async def _roda_loop(agent: BaseAgent) -> list[Event]:
    """Executa `_code_execute_loop` via Runner real do ADK e retorna os eventos."""
    runner = Runner(
        app_name="code_execute_loop_test",
        agent=agent,
        session_service=InMemorySessionService(),
    )
    session = await runner.session_service.create_session(
        app_name="code_execute_loop_test", user_id="u", state={},
    )
    msg = types.Content(role="user", parts=[types.Part.from_text(text="implementar feature")])
    eventos = [
        e async for e in runner.run_async(
            user_id="u", session_id=session.id, new_message=msg,
        )
    ]
    await runner.close()
    return eventos


@pytest.mark.asyncio
async def test_loop_converge_apos_reprovacoes(trace_collector, monkeypatch):
    """LoopAgent para na iteração em que o executor sinaliza aprovação (escalate=True).

    Reprodução: executor reprova nas 2 primeiras iterações (loop continua) e
    aprova na 3ª (exit_loop). O LoopAgent real do ADK deve encerrar
    exatamente ali — nem rodar uma 4ª iteração, nem parar antes da 3ª.
    """
    stub_coder = _StubCoder(name="cr_coder_agent", description="stub", trace_collector=trace_collector)
    stub_executor = _StubExecutorConverge(
        name="cr_executor_agent", description="stub", trace_collector=trace_collector,
    )
    monkeypatch.setattr(_code_execute_loop, "sub_agents", [stub_coder, stub_executor])

    await _roda_loop(_code_execute_loop)

    assert stub_executor.invocacoes == 3, (
        f"esperado exatamente 3 invocações do executor até a aprovação, "
        f"obtido {stub_executor.invocacoes}"
    )

    trace_collector.assert_order(["cr_coder_agent", "cr_executor_agent"])

    eventos_veredito = [
        e for e in trace_collector.events if e.acao == "veredito"
    ]
    assert eventos_veredito, "nenhum evento de veredito registrado no trace"
    assert eventos_veredito[-1].status == "aprovado", (
        f"último veredito deveria ser 'aprovado', obtido: {eventos_veredito[-1].status}"
    )


@pytest.mark.asyncio
async def test_loop_encerra_controladamente_ao_esgotar_max_iterations(trace_collector, monkeypatch):
    """LoopAgent encerra em `max_iterations` quando o executor nunca aprova.

    Reprodução: executor sempre reprova (nunca chama exit_loop). O LoopAgent
    deve parar pelo teto de segurança (`max_iterations`), sem travar e sem
    produzir uma falsa aprovação — o encerramento aqui é um fallback
    controlado, não uma convergência.
    """
    stub_coder = _StubCoder(name="cr_coder_agent", description="stub", trace_collector=trace_collector)
    stub_executor = _StubExecutorNuncaAprova(
        name="cr_executor_agent", description="stub", trace_collector=trace_collector,
    )
    monkeypatch.setattr(_code_execute_loop, "sub_agents", [stub_coder, stub_executor])

    max_iterations = _code_execute_loop.max_iterations
    eventos = await _roda_loop(_code_execute_loop)

    assert eventos is not None  # run_async concluiu sem exception e sem travar

    assert stub_executor.invocacoes == max_iterations, (
        f"esperado exatamente max_iterations={max_iterations} invocações do "
        f"executor, obtido {stub_executor.invocacoes}"
    )

    status_aprovado = [e for e in trace_collector.events if e.status == "aprovado"]
    assert not status_aprovado, (
        f"nenhum veredito deveria ser 'aprovado' neste cenário de esgotamento, "
        f"encontrado: {status_aprovado}"
    )
