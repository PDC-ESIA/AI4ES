"""Testes da camada determinística que itera as tasks do coding review."""

import json
from typing import ClassVar

import pytest
from google.adk.agents import BaseAgent
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from shared.workspace import get_agent_workspace
from src.agents.workflow_coding_review.task_iterator import (
    TaskIterator,
    _carregar_tasks,
    _resolver_politica_falha,
)


def _task(task_id: str, description: str = "Implementar") -> dict:
    return {"id": task_id, "description": description}


def _persistir_tasks(tasks_dir, tasks):
    tasks_dir.mkdir(parents=True, exist_ok=True)
    for task in tasks:
        (tasks_dir / f"{task['id']}.json").write_text(
            json.dumps(task), encoding="utf-8"
        )


def test_carregar_tasks_preserva_ordem_canonica_do_state(tmp_path):
    tasks = [_task("TASK-010"), _task("TASK-002"), _task("TASK-001")]
    _persistir_tasks(tmp_path, tasks)

    carregadas = _carregar_tasks({"tasks": {"tasks": tasks}}, tmp_path)

    assert [task["id"] for task in carregadas] == [
        "TASK-010",
        "TASK-002",
        "TASK-001",
    ]


@pytest.mark.parametrize(
    ("state", "mensagem"),
    [
        ({}, "ausente ou inválido"),
        ({"tasks": {"tasks": [{"description": "sem id"}]}}, "id ausente"),
        (
            {"tasks": {"tasks": [_task("TASK-001"), _task("TASK-001")]}},
            "duplicado",
        ),
    ],
)
def test_carregar_tasks_rejeita_fila_invalida(tmp_path, state, mensagem):
    _persistir_tasks(tmp_path, [_task("TASK-001")])

    with pytest.raises(ValueError, match=mensagem):
        _carregar_tasks(state, tmp_path)


def test_carregar_tasks_rejeita_contrato_ausente(tmp_path):
    with pytest.raises(ValueError, match="não persistido"):
        _carregar_tasks({"tasks": {"tasks": [_task("TASK-001")]}}, tmp_path)


def test_carregar_tasks_rejeita_id_interno_divergente(tmp_path):
    (tmp_path / "TASK-001.json").write_text(
        json.dumps(_task("TASK-OUTRA")), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="id interno divergente"):
        _carregar_tasks({"tasks": {"tasks": [_task("TASK-001")]}}, tmp_path)


def test_carregar_tasks_ordena_dependencias_antes_das_dependentes(tmp_path):
    tasks = [
        {**_task("TASK-002"), "depends_on": ["TASK-001"]},
        _task("TASK-003"),
        _task("TASK-001"),
    ]
    _persistir_tasks(tmp_path, tasks)

    carregadas = _carregar_tasks({"tasks": {"tasks": tasks}}, tmp_path)

    assert [task["id"] for task in carregadas] == [
        "TASK-001",
        "TASK-002",
        "TASK-003",
    ]


def test_carregar_tasks_rejeita_dependencia_inexistente_e_ciclo(tmp_path):
    inexistente = [{**_task("TASK-001"), "depends_on": ["TASK-999"]}]
    _persistir_tasks(tmp_path, inexistente)
    with pytest.raises(ValueError, match="inexistentes"):
        _carregar_tasks({"tasks": {"tasks": inexistente}}, tmp_path)

    ciclicas = [
        {**_task("TASK-001"), "depends_on": ["TASK-002"]},
        {**_task("TASK-002"), "depends_on": ["TASK-001"]},
    ]
    _persistir_tasks(tmp_path, ciclicas)
    with pytest.raises(ValueError, match="ciclo"):
        _carregar_tasks({"tasks": {"tasks": ciclicas}}, tmp_path)


def test_carregar_tasks_rejeita_dependencias_divergentes_do_arquivo(tmp_path):
    state_task = {**_task("TASK-002"), "depends_on": ["TASK-001"]}
    _persistir_tasks(tmp_path, [_task("TASK-001"), _task("TASK-002")])

    with pytest.raises(ValueError, match="depends_on divergente"):
        _carregar_tasks(
            {"tasks": {"tasks": [_task("TASK-001"), state_task]}},
            tmp_path,
        )


def test_politica_padrao_e_rejeicao_de_valor_invalido():
    assert _resolver_politica_falha({"tasks": {"tasks": []}}) == "fail_fast"
    with pytest.raises(ValueError, match="failure_policy inválida"):
        _resolver_politica_falha(
            {"tasks": {"tasks": [], "failure_policy": "ignorar_tudo"}}
        )


class _LoopAprovador(BaseAgent):
    """Loop fake: observa o contexto e aprova; escalate simula o executor real."""

    observacoes: ClassVar[list[dict]] = []

    async def _run_async_impl(self, ctx):
        self.observacoes.append(
            {
                "task_id": ctx.session.state.get("task_id"),
                "current_task": ctx.session.state.get("current_task"),
                "current_task_index": ctx.session.state.get("current_task_index"),
                "total_tasks": ctx.session.state.get("total_tasks"),
                "project_initialized": ctx.session.state.get("project_initialized"),
                "stagnation_count": ctx.session.state.get("stagnation_count"),
            }
        )
        task_id = ctx.session.state["task_id"]
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            content=types.Content(
                role="model", parts=[types.Part(text=f"{task_id} aprovada")]
            ),
            actions=EventActions(
                state_delta={
                    "validation": {"status": "aprovado"},
                    "stagnation_count": 2,
                    "executor_iteration": 2,
                    "report_path": f"/reports/{task_id}.json",
                },
                escalate=True,
            ),
        )


async def test_runner_processa_duas_tasks_e_contem_escalate(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace"))
    tasks = [_task("TASK-001", "Primeira"), _task("TASK-002", "Segunda")]
    _persistir_tasks(get_agent_workspace("cr_context_engineer"), tasks)
    _LoopAprovador.observacoes = []
    loop = _LoopAprovador(name="loop_aprovador")
    iterator = TaskIterator(name="task_iterator_test", code_execute_loop=loop)
    sessions = InMemorySessionService()
    runner = Runner(app_name="task_iterator_test", agent=iterator, session_service=sessions)
    session = await sessions.create_session(
        app_name="task_iterator_test",
        user_id="user",
        state={"tasks": {"tasks": tasks}},
    )

    events = [
        event
        async for event in runner.run_async(
            user_id="user",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text="iniciar")]),
        )
    ]

    assert [item["task_id"] for item in _LoopAprovador.observacoes] == [
        "TASK-001",
        "TASK-002",
    ]
    assert _LoopAprovador.observacoes[0]["current_task"] == {
        **tasks[0],
        "depends_on": [],
    }
    assert _LoopAprovador.observacoes[0]["project_initialized"] is False
    assert _LoopAprovador.observacoes[1]["project_initialized"] is True
    assert _LoopAprovador.observacoes[1]["stagnation_count"] is None
    assert [item["current_task_index"] for item in _LoopAprovador.observacoes] == [1, 2]
    assert all(item["total_tasks"] == 2 for item in _LoopAprovador.observacoes)
    assert any(
        event.content
        and event.content.parts
        and "Todas as 2 tasks foram aprovadas" in (event.content.parts[0].text or "")
        for event in events
    )
    atualizado = await sessions.get_session(
        app_name="task_iterator_test", user_id="user", session_id=session.id
    )
    assert atualizado is not None
    assert atualizado.state["task_iteration_status"] == "concluido"
    assert atualizado.state["task_iteration_outcome"] == "aprovado"
    assert atualizado.state["task_iteration_summary"] == {
        "outcome": "aprovado",
        "total": 2,
        "processed": 2,
        "approved": 2,
        "blocked": 0,
        "pending": 0,
    }
    assert atualizado.state["task_results"] == [
        {
            "task_id": "TASK-001",
            "index": 1,
            "status": "aprovado",
            "attempts": 2,
            "report_path": "/reports/TASK-001.json",
            "blocking_reason": None,
        },
        {
            "task_id": "TASK-002",
            "index": 2,
            "status": "aprovado",
            "attempts": 2,
            "report_path": "/reports/TASK-002.json",
            "blocking_reason": None,
        },
    ]
    assert atualizado.state["task_runtime"]["task_id"] == "TASK-002"
    assert atualizado.state["task_runtime"]["stagnation"]["count"] == 2


class _LoopReprovador(BaseAgent):
    chamadas: ClassVar[list[str]] = []

    async def _run_async_impl(self, ctx):
        task_id = ctx.session.state["task_id"]
        self.chamadas.append(task_id)
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            actions=EventActions(
                state_delta={
                    "validation": {
                        "status": "reprovado",
                        "blocking_reason": "falha controlada",
                    }
                }
            ),
        )


async def test_runner_para_na_primeira_reprovacao(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace"))
    tasks = [_task("TASK-001"), _task("TASK-002")]
    _persistir_tasks(get_agent_workspace("cr_context_engineer"), tasks)
    _LoopReprovador.chamadas = []
    iterator = TaskIterator(
        name="task_iterator_reprovacao",
        code_execute_loop=_LoopReprovador(name="loop_reprovador"),
    )
    sessions = InMemorySessionService()
    runner = Runner(app_name="task_iterator_reprovacao", agent=iterator, session_service=sessions)
    session = await sessions.create_session(
        app_name="task_iterator_reprovacao",
        user_id="user",
        state={"tasks": {"tasks": tasks}},
    )

    _ = [
        event
        async for event in runner.run_async(
            user_id="user",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text="iniciar")]),
        )
    ]

    assert _LoopReprovador.chamadas == ["TASK-001"]
    atualizado = await sessions.get_session(
        app_name="task_iterator_reprovacao", user_id="user", session_id=session.id
    )
    assert atualizado is not None
    assert atualizado.state["task_iteration_status"] == "concluido"
    assert atualizado.state["task_iteration_outcome"] == "parcial"
    assert atualizado.state["task_failure_policy"] == "fail_fast"
    assert atualizado.state["task_iteration_error"] == "falha controlada"
    assert atualizado.state["task_iteration_summary"] == {
        "outcome": "parcial",
        "total": 2,
        "processed": 1,
        "approved": 0,
        "blocked": 1,
        "pending": 1,
    }
    assert atualizado.state["task_results"][0]["status"] == "reprovado"
    assert atualizado.state["task_runtime"]["validation"]["status"] == "reprovado"


class _LoopPorTask(BaseAgent):
    chamadas: ClassVar[list[str]] = []

    async def _run_async_impl(self, ctx):
        task_id = ctx.session.state["task_id"]
        self.chamadas.append(task_id)
        aprovado = task_id == "TASK-003"
        validation = {
            "status": "aprovado" if aprovado else "reprovado",
            "blocking_reason": None if aprovado else "falha da base",
        }
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            actions=EventActions(
                state_delta={"validation": validation, "executor_iteration": 1},
                escalate=aprovado,
            ),
        )


async def test_continue_independent_bloqueia_dependente_e_executa_independente(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace"))
    tasks = [
        _task("TASK-001"),
        {**_task("TASK-002"), "depends_on": ["TASK-001"]},
        _task("TASK-003"),
    ]
    _persistir_tasks(get_agent_workspace("cr_context_engineer"), tasks)
    _LoopPorTask.chamadas = []
    iterator = TaskIterator(
        name="task_iterator_continue",
        code_execute_loop=_LoopPorTask(name="loop_por_task"),
    )
    sessions = InMemorySessionService()
    runner = Runner(app_name="task_iterator_continue", agent=iterator, session_service=sessions)
    session = await sessions.create_session(
        app_name="task_iterator_continue",
        user_id="user",
        state={
            "tasks": {
                "failure_policy": "continue_independent",
                "tasks": tasks,
            }
        },
    )

    _ = [
        event
        async for event in runner.run_async(
            user_id="user",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text="iniciar")]),
        )
    ]

    atualizado = await sessions.get_session(
        app_name="task_iterator_continue", user_id="user", session_id=session.id
    )
    assert atualizado is not None
    assert _LoopPorTask.chamadas == ["TASK-001", "TASK-003"]
    assert atualizado.state["task_failure_policy"] == "continue_independent"
    assert atualizado.state["task_iteration_outcome"] == "parcial"
    assert [item["status"] for item in atualizado.state["task_results"]] == [
        "reprovado",
        "bloqueado_dependencia",
        "aprovado",
    ]
    assert atualizado.state["task_iteration_summary"] == {
        "outcome": "parcial",
        "total": 3,
        "processed": 3,
        "approved": 1,
        "blocked": 2,
        "pending": 0,
    }


class _LoopNuncaChamado(BaseAgent):
    async def _run_async_impl(self, ctx):
        raise AssertionError("loop não deveria ser chamado")
        yield


async def test_runner_sem_tasks_registra_bloqueio_observavel(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace"))
    iterator = TaskIterator(
        name="task_iterator_vazio",
        code_execute_loop=_LoopNuncaChamado(name="loop_nunca_chamado"),
    )
    sessions = InMemorySessionService()
    runner = Runner(app_name="task_iterator_vazio", agent=iterator, session_service=sessions)
    session = await sessions.create_session(
        app_name="task_iterator_vazio",
        user_id="user",
        state={"tasks": {"tasks": []}},
    )

    events = [
        event
        async for event in runner.run_async(
            user_id="user",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text="iniciar")]),
        )
    ]

    atualizado = await sessions.get_session(
        app_name="task_iterator_vazio", user_id="user", session_id=session.id
    )
    assert atualizado is not None
    assert atualizado.state["task_iteration_status"] == "concluido"
    assert atualizado.state["task_iteration_outcome"] == "sem_tasks"
    assert atualizado.state["task_results"] == []
    assert atualizado.state["task_runtime"] is None
    assert atualizado.state["task_iteration_summary"]["processed"] == 0
    textos = [
        part.text
        for event in events
        if event.content
        for part in (event.content.parts or [])
        if part.text
    ]
    assert any("reviewer receberá este bloqueio" in texto for texto in textos)
