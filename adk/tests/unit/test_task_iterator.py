"""Testes da Fatia 1: iteração determinística e gate de cobertura."""

from __future__ import annotations

from types import SimpleNamespace
from typing import AsyncGenerator

import pytest
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import PrivateAttr

from shared.tools.coding_tools import harness_execucao
from src.agents.workflow_coding_review.task_iterator import (
    TaskIterator,
    calcular_cobertura,
    classificar_desfecho,
    detalhe_erro_operacional,
    validar_envelope_de_tasks,
)


class _StubLoop(BaseAgent):
    """Loop controlável que aprova, reprova ou lança erro por task."""

    _comportamentos: dict[str, str] = PrivateAttr(default_factory=dict)
    _chamadas: list[dict] = PrivateAttr(default_factory=list)

    def configurar(self, comportamentos: dict[str, str]) -> None:
        self._comportamentos = comportamentos

    @property
    def chamadas(self) -> list[dict]:
        return self._chamadas

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        task_id = ctx.session.state["task_id"]
        self._chamadas.append(
            {
                "task_id": task_id,
                "branch": ctx.branch,
                "execution_result": ctx.session.state.get("execution_result"),
            }
        )
        comportamento = self._comportamentos.get(task_id, "aprovado")
        if comportamento == "erro":
            raise RuntimeError("falha operacional de teste")

        ctx.session.state["validation"] = {
            "work_item_id": task_id,
            "status": comportamento,
            "blocking_reason": None if comportamento == "aprovado" else "falhou",
        }
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=task_id)]),
        )


async def _executar_iterator(tasks: object, comportamentos: dict[str, str]):
    loop = _StubLoop(name="stub_loop")
    loop.configurar(comportamentos)
    iterator = TaskIterator(
        name="task_iterator_test",
        sub_agents=[loop],
    )
    session_service = InMemorySessionService()
    runner = Runner(
        agent=iterator,
        app_name="workflow_coding_review",
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name="workflow_coding_review",
        user_id="test-user",
        state={"tasks": tasks},
    )

    eventos = []
    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=types.Content(
            role="user", parts=[types.Part(text="processar tasks")]
        ),
    ):
        eventos.append(event)

    atualizada = await session_service.get_session(
        app_name="workflow_coding_review",
        user_id=session.user_id,
        session_id=session.id,
    )
    assert atualizada is not None
    return loop, eventos, atualizada.state


def test_validar_envelope_rejeita_formas_invalidas():
    casos = [
        (None, "tasks_ausente"),
        ([], "envelope_invalido"),
        ({}, "lista_ausente"),
        ({"tasks": {}}, "lista_tipo_invalido"),
        ({"tasks": []}, "lista_vazia"),
        ({"tasks": [None]}, "task_tipo_invalido"),
        ({"tasks": [{}]}, "id_ausente"),
        ({"tasks": [{"id": 1}]}, "id_tipo_invalido"),
        ({"tasks": [{"id": "../TASK-001"}]}, "id_invalido"),
        (
            {"tasks": [{"id": "TASK-001"}, {"id": "TASK-001"}]},
            "id_duplicado",
        ),
    ]

    for envelope, tipo_esperado in casos:
        tasks, erros = validar_envelope_de_tasks(envelope)
        assert tasks == []
        assert any(erro["type"] == tipo_esperado for erro in erros)


def test_calcular_cobertura_e_fail_closed():
    ids = ["TASK-001", "TASK-002"]
    assert calcular_cobertura(True, ids, ids, ids) is True
    assert calcular_cobertura(False, ids, ids, ids) is False
    assert calcular_cobertura(True, [], [], []) is False
    assert calcular_cobertura(True, ids, ids, ["TASK-001"]) is False


def test_classificar_desfecho_rejeita_work_item_divergente():
    resultado = classificar_desfecho(
        {
            "validation": {
                "work_item_id": "TASK-999",
                "status": "aprovado",
            }
        },
        "TASK-001",
    )
    assert resultado["status"] == "reprovado"
    assert resultado["motivo_terminacao"] == "validation_ausente_ou_invalida"


def test_classificar_desfecho_detecta_estagnacao():
    resultado = classificar_desfecho(
        {
            "validation": {
                "work_item_id": "TASK-001",
                "status": "reprovado",
                "blocking_reason": "sem progresso",
            },
            "execution_result": "STATUS: bloqueado\nSem alterações.",
        },
        "TASK-001",
    )
    assert resultado["status"] == "bloqueado"
    assert resultado["motivo_terminacao"] == "bloqueado_estagnacao"


@pytest.mark.asyncio
async def test_iterator_processa_todas_em_branches_irmas_e_publica_gate():
    loop, eventos, state = await _executar_iterator(
        {"tasks": [{"id": "TASK-001"}, {"id": "TASK-002"}]},
        {"TASK-001": "aprovado", "TASK-002": "aprovado"},
    )

    assert [c["task_id"] for c in loop.chamadas] == ["TASK-001", "TASK-002"]
    assert [c["branch"] for c in loop.chamadas] == [
        "task_iterator.task_0_TASK-001",
        "task_iterator.task_1_TASK-002",
    ]
    assert loop.chamadas[0]["execution_result"] is None
    assert loop.chamadas[1]["execution_result"].startswith("NOVA_TASK:")

    summary = state["task_iteration_summary"]
    assert summary["processed_task_ids"] == ["TASK-001", "TASK-002"]
    assert summary["approved_task_ids"] == ["TASK-001", "TASK-002"]
    assert summary["cobertura_completa"] is True
    assert any(
        event.actions and event.actions.state_delta.get("task_iteration_summary")
        for event in eventos
    )


@pytest.mark.asyncio
async def test_iterator_isola_erro_e_continua_proxima_task():
    loop, _, state = await _executar_iterator(
        {"tasks": [{"id": "TASK-001"}, {"id": "TASK-002"}]},
        {"TASK-001": "erro", "TASK-002": "aprovado"},
    )

    assert [c["task_id"] for c in loop.chamadas] == ["TASK-001", "TASK-002"]
    summary = state["task_iteration_summary"]
    assert summary["processed_task_ids"] == ["TASK-001", "TASK-002"]
    assert summary["approved_task_ids"] == ["TASK-002"]
    assert summary["task_results"]["TASK-001"]["motivo_terminacao"] == "erro_operacional"
    assert summary["cobertura_completa"] is False


@pytest.mark.asyncio
async def test_iterator_entrada_invalida_nao_invoca_loop():
    loop, _, state = await _executar_iterator(
        {"tasks": [{"id": "TASK-invalida"}]},
        {},
    )
    assert loop.chamadas == []
    summary = state["task_iteration_summary"]
    assert summary["input_valid"] is False
    assert summary["cobertura_completa"] is False


def test_resolver_task_id_state_prevalece_e_fallback_e_preservado(monkeypatch):
    recebidos = []

    def fake_validacao(task_id, iteration, tool_context=None):
        recebidos.append((task_id, iteration, tool_context))
        return {"work_item_id": task_id}

    monkeypatch.setattr(
        harness_execucao, "executar_harness_validacao", fake_validacao
    )
    contexto = SimpleNamespace(state={"task_id": "TASK-002"})

    resultado = harness_execucao.executar_harness_tool(
        "TASK-999", iteration=3, tool_context=contexto
    )
    assert resultado["work_item_id"] == "TASK-002"
    assert recebidos[-1][:2] == ("TASK-002", 3)

    resultado_direto = harness_execucao.executar_harness_tool("TASK-003")
    assert resultado_direto["work_item_id"] == "TASK-003"


def test_detalhe_erro_operacional_nao_expoe_mensagem_bruta():
    detalhe = detalhe_erro_operacional(RuntimeError("segredo " * 100))
    assert detalhe == "RuntimeError: erro operacional; consulte os logs."
    assert "segredo" not in detalhe
