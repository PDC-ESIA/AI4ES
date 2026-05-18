"""Testes do retry layer do _PipelineOrchestrator (bugs 1 e 2).

Quando um pipeline conclui com last_text vazio (sem pending_pause), o
orchestrator reinvoca o mesmo runner com EMPTY_RETRY_PROMPT uma vez
antes de propagar a falha. Estratégia: mockar Runner.run_async via
monkeypatch e contar invocações.
"""

from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.adk.events.event import Event
from google.genai import types


def _make_text_event(author: str, text: str) -> Event:
    return Event(
        author=author,
        invocation_id="inv-test",
        content=types.Content(role="model", parts=[types.Part(text=text)]),
    )


def _make_long_running_pause_event(author: str, call_id: str) -> Event:
    fc = types.FunctionCall(
        id=call_id,
        name="aguardar_aprovacao_humana",
        args={
            "checkpoint_id": "ck-1",
            "approval_question": "?",
            "allowed_decisions": ["aprovar", "rejeitar"],
        },
    )
    return Event(
        author=author,
        invocation_id="inv-test",
        content=types.Content(
            role="model", parts=[types.Part(function_call=fc)]
        ),
        long_running_tool_ids={call_id},
    )


class _FakeSession:
    def __init__(self, session_id: str = "inner-sid", user_id: str = "u"):
        self.id = session_id
        self.user_id = user_id


class _FakeSessionService:
    async def create_session(self, *, app_name, user_id, state):
        return _FakeSession()


def _make_recording_runner(
    sequences: list[list[Event]],
) -> tuple[MagicMock, list[dict]]:
    """Runner que retorna um seq de eventos por chamada e grava cada call.

    sequences[0] vai na 1ª chamada de run_async; sequences[1] na 2ª; etc.
    Retorna (runner, calls), onde `calls` é uma lista de dicts com os
    kwargs de cada invocação.
    """
    runner = MagicMock()
    runner.session_service = _FakeSessionService()
    runner.close = AsyncMock(return_value=None)
    calls: list[dict] = []
    seq_iter = iter(sequences)

    async def fake_run_async(**kwargs) -> AsyncGenerator[Event, None]:
        calls.append(kwargs)
        for e in next(seq_iter):
            yield e

    runner.run_async = fake_run_async
    return runner, calls


class _FakeCtx:
    def __init__(self, user_text: str, session_id: str = "outer-sid",
                 state: dict | None = None):
        self.user_content = types.Content(
            role="user", parts=[types.Part(text=user_text)]
        )
        self.user_id = "test-user"
        self.session = MagicMock()
        self.session.id = session_id
        self.session.state = state if state is not None else {}
        self.artifact_service = MagicMock()
        self.credential_service = MagicMock()
        self.plugin_manager = MagicMock()
        self.plugin_manager.plugins = []


# --- R1: empty na 1ª invocação dispara retry, 2ª devolve texto válido ---


@pytest.mark.asyncio
async def test_empty_response_triggers_retry(monkeypatch):
    """Pipeline retorna empty na 1ª chamada; orchestrator chama 2ª vez."""
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    # 4 runners, um por pipeline. O 1º (requirements) emite empty na 1ª
    # chamada e texto válido na 2ª (após o EMPTY_RETRY_PROMPT).
    req_runner, req_calls = _make_recording_runner([
        [_make_text_event("requirements_pipeline", "")],   # 1ª: empty
        [_make_text_event("requirements_pipeline", "req-ok")],  # 2ª: ok
    ])
    runners_iter = iter([
        req_runner,
        _make_recording_runner([[_make_text_event("design_pipeline", "d")]])[0],
        _make_recording_runner([[_make_text_event("coding_review_pipeline", "c")]])[0],
        _make_recording_runner([[_make_text_event("qa_pipeline", "q")]])[0],
    ])
    monkeypatch.setattr(
        "src.agents.orchestrator.agent.Runner",
        lambda **kwargs: next(runners_iter),
    )

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    ctx = _FakeCtx("prompt inicial")

    _ = [e async for e in orch._run_async_impl(ctx)]

    # requirements runner foi chamado 2x (1 original + 1 retry)
    assert len(req_calls) == 2
    # Conteúdo da 2ª chamada deve ser o EMPTY_RETRY_PROMPT
    from src.agents.orchestrator._helpers import EMPTY_RETRY_PROMPT
    retry_msg = req_calls[1]["new_message"]
    retry_text = retry_msg.parts[0].text
    assert retry_text == EMPTY_RETRY_PROMPT


# --- R2: retry sucede → accumulated_outputs recebe o texto da 2ª ---


@pytest.mark.asyncio
async def test_retry_succeeds_then_propagates(monkeypatch):
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    req_runner, _ = _make_recording_runner([
        [_make_text_event("requirements_pipeline", "")],
        [_make_text_event("requirements_pipeline", "req-retry-ok")],
    ])
    runners_iter = iter([
        req_runner,
        _make_recording_runner([[_make_text_event("design_pipeline", "d")]])[0],
        _make_recording_runner([[_make_text_event("coding_review_pipeline", "c")]])[0],
        _make_recording_runner([[_make_text_event("qa_pipeline", "q")]])[0],
    ])
    monkeypatch.setattr(
        "src.agents.orchestrator.agent.Runner",
        lambda **kwargs: next(runners_iter),
    )

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    ctx = _FakeCtx("prompt inicial")
    _ = [e async for e in orch._run_async_impl(ctx)]

    accumulated = ctx.session.state["accumulated_outputs"]
    # primeiro item é (nome_pipeline, last_text). Esperamos last_text = retry ok
    names = [name for name, _ in accumulated]
    texts = dict(accumulated)
    assert "requirements_pipeline" in names
    assert texts["requirements_pipeline"] == "req-retry-ok"


# --- R3: duas empties consecutivas marcam falha ---


@pytest.mark.asyncio
async def test_double_empty_marks_failure(monkeypatch):
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    req_runner, _ = _make_recording_runner([
        [_make_text_event("requirements_pipeline", "")],
        [_make_text_event("requirements_pipeline", "")],
    ])
    runners_iter = iter([
        req_runner,
        _make_recording_runner([[_make_text_event("design_pipeline", "d")]])[0],
        _make_recording_runner([[_make_text_event("coding_review_pipeline", "c")]])[0],
        _make_recording_runner([[_make_text_event("qa_pipeline", "q")]])[0],
    ])
    monkeypatch.setattr(
        "src.agents.orchestrator.agent.Runner",
        lambda **kwargs: next(runners_iter),
    )

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    ctx = _FakeCtx("prompt inicial")
    _ = [e async for e in orch._run_async_impl(ctx)]

    texts = dict(ctx.session.state["accumulated_outputs"])
    assert "retornou empty após retry" in texts["requirements_pipeline"]


# --- R4: pending_pause NÃO dispara retry ---


@pytest.mark.asyncio
async def test_pending_pause_no_retry(monkeypatch):
    """qa emite pause; mesmo sem texto, orchestrator NÃO faz retry."""
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    pause_event = _make_long_running_pause_event("qa_pipeline", "call-1")
    qa_runner, qa_calls = _make_recording_runner([
        [pause_event],  # só pause, sem texto
    ])
    runners_iter = iter([
        _make_recording_runner([[_make_text_event("requirements_pipeline", "r")]])[0],
        _make_recording_runner([[_make_text_event("design_pipeline", "d")]])[0],
        _make_recording_runner([[_make_text_event("coding_review_pipeline", "c")]])[0],
        qa_runner,
    ])
    monkeypatch.setattr(
        "src.agents.orchestrator.agent.Runner",
        lambda **kwargs: next(runners_iter),
    )

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    ctx = _FakeCtx("prompt", session_id="outer-1")
    _ = [e async for e in orch._run_async_impl(ctx)]

    # qa runner foi chamado APENAS 1x (sem retry, porque pausa é sucesso)
    assert len(qa_calls) == 1
    assert ctx.session.state["paused_pipeline"] == "qa_pipeline"
