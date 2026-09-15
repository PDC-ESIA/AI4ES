"""Integração da política de progresso com LoopAgent e TaskIterator.

Exercita a costura real do ADK sem LLM: agentes stub produzem rodadas com nota
constante, a política emite ``escalate`` ao decidir parar, o LoopAgent encerra
antes do teto de segurança e o TaskIterator preserva o diagnóstico no summary.

Dois casos, porque a nota parada NÃO decide sozinha o desfecho: repetir a mesma
falha encerra cedo; atravessar falhas diferentes segue até o orçamento.
"""

from __future__ import annotations

from typing import AsyncGenerator

import pytest
from google.adk.agents import BaseAgent, LoopAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import PrivateAttr

from src.agents.workflow_coding_review.executor.loop_policy import (
    ORCAMENTO_FALHAS_DISTINTAS,
    registrar_e_avaliar,
)
from src.agents.workflow_coding_review.task_iterator import TaskIterator


class _CoderStub(BaseAgent):
    _chamadas: int = PrivateAttr(default=0)

    @property
    def chamadas(self) -> int:
        return self._chamadas

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        self._chamadas += 1
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text="codificado")]),
        )


class _ExecutorReprovadoStub(BaseAgent):
    """Reprova sempre, com nota constante. `falha_sempre_inedita` escolhe o
    gatilho exercitado: assinatura fixa cai no erro repetido; assinatura nova a
    cada rodada atravessa o platô e só para no orçamento de falhas distintas."""

    falha_sempre_inedita: bool = False
    _chamadas: int = PrivateAttr(default=0)

    @property
    def chamadas(self) -> int:
        return self._chamadas

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        self._chamadas += 1
        state = ctx.session.state
        state["validation"] = {
            "work_item_id": state["task_id"],
            "status": "reprovado",
            "blocking_reason": "critério ainda não atendido",
        }
        decisao = registrar_e_avaliar(
            state,
            nota_total=0.4,
            nota_detalhe={"build_concluido": 1.0},
            arquivos_mudaram=True,
            assinatura_erro_atual=(
                f"falha-{self._chamadas}" if self.falha_sempre_inedita else "falha-fixa"
            ),
        )
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            actions=EventActions(escalate=decisao.parar),
            content=types.Content(role="model", parts=[types.Part(text="reprovado")]),
        )


async def _rodar_ate_o_fim(executor: BaseAgent) -> tuple[dict, list[Event], LoopAgent]:
    coder = _CoderStub(name="coder_stub")
    loop = LoopAgent(
        name="code_execute_loop_test",
        sub_agents=[coder, executor],
        max_iterations=20,
    )
    iterator = TaskIterator(name="task_iterator_test", sub_agents=[loop])
    sessions = InMemorySessionService()
    runner = Runner(
        agent=iterator,
        app_name="workflow_coding_review_test",
        session_service=sessions,
    )
    session = await sessions.create_session(
        app_name="workflow_coding_review_test",
        user_id="test-user",
        state={"tasks": {"tasks": [{"id": "TASK-001"}]}},
    )

    eventos = []
    async for evento in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=types.Content(
            role="user", parts=[types.Part(text="processar task")]
        ),
    ):
        eventos.append(evento)

    atualizada = await sessions.get_session(
        app_name="workflow_coding_review_test",
        user_id=session.user_id,
        session_id=session.id,
    )
    assert atualizada is not None
    resultado = atualizada.state["task_iteration_summary"]["task_results"]["TASK-001"]
    return resultado, eventos, loop


@pytest.mark.asyncio
async def test_falha_repetida_encerra_loop_e_chega_ao_summary():
    """Assinatura constante: o coder repisa o mesmo erro e o loop encerra cedo."""
    executor = _ExecutorReprovadoStub(name="executor_stub", falha_sempre_inedita=False)

    resultado, eventos, loop = await _rodar_ate_o_fim(executor)

    assert executor.chamadas == 3
    assert executor.chamadas < loop.max_iterations
    assert any(evento.actions.escalate for evento in eventos)
    assert resultado["status"] == "bloqueado"
    assert resultado["motivo_terminacao"] == "bloqueado_erro_repetido"
    assert resultado["historico_notas"] == [0.4, 0.4, 0.4]


@pytest.mark.asyncio
async def test_falha_sempre_inedita_atravessa_o_plato_e_para_no_orcamento():
    """Assinatura nova a cada rodada: o loop NÃO encerra por platô.

    É a costura real da política orientada a causa — a nota fica parada em 0.4 o
    tempo todo e, mesmo assim, o loop segue enquanto o coder estiver derrubando
    problemas diferentes. O freio é o orçamento de falhas distintas.
    """
    executor = _ExecutorReprovadoStub(name="executor_stub", falha_sempre_inedita=True)

    resultado, eventos, loop = await _rodar_ate_o_fim(executor)

    assert executor.chamadas == ORCAMENTO_FALHAS_DISTINTAS + 1
    assert executor.chamadas < loop.max_iterations
    assert any(evento.actions.escalate for evento in eventos)
    assert resultado["status"] == "bloqueado"
    assert resultado["motivo_terminacao"] == "bloqueado_orcamento_de_falhas_distintas"
    assert resultado["historico_notas"] == [0.4] * (ORCAMENTO_FALHAS_DISTINTAS + 1)
    assert resultado["detalhes_notas"] == [{"build_concluido": 1.0}] * (
        ORCAMENTO_FALHAS_DISTINTAS + 1
    )
