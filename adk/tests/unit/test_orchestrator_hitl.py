"""Testes do _PipelineOrchestrator com HITL.

Estratégia: mockar Runner.run_async para emitir Events controlados.
Cada teste constrói um Runner falso, injeta no orchestrator via
monkeypatch do Runner(...) construtor.
"""

from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.adk.events.event import Event
from google.genai import types


# --- Helpers de fixture ---


def _make_text_event(author: str, text: str) -> Event:
    return Event(
        author=author,
        invocation_id="inv-test",
        content=types.Content(role="model", parts=[types.Part(text=text)]),
    )


def _make_long_running_pause_event(
    author: str,
    call_id: str,
    call_name: str = "aguardar_aprovacao_humana",
    call_args: dict | None = None,
) -> Event:
    fc = types.FunctionCall(
        id=call_id,
        name=call_name,
        args=call_args or {
            "checkpoint_id": "ck-1",
            "approval_question": "?",
            "allowed_decisions": ["aprovar", "rejeitar", "solicitar_ajustes"],
        },
    )
    return Event(
        author=author,
        invocation_id="inv-test",
        content=types.Content(role="model", parts=[types.Part(function_call=fc)]),
        long_running_tool_ids={call_id},
    )


class _FakeSession:
    def __init__(self, session_id: str = "inner-sid", user_id: str = "u"):
        self.id = session_id
        self.user_id = user_id


class _FakeSessionService:
    async def create_session(self, *, app_name, user_id, state):
        return _FakeSession()


def _make_fake_runner(events_to_yield: list[Event]) -> MagicMock:
    """Runner falso que retorna eventos pré-definidos em run_async."""
    runner = MagicMock()
    runner.session_service = _FakeSessionService()
    runner.close = AsyncMock(return_value=None)

    async def fake_run_async(**kwargs) -> AsyncGenerator[Event, None]:
        for e in events_to_yield:
            yield e

    runner.run_async = fake_run_async
    return runner


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


# --- U1: FRESH RUN sem pausa ---


@pytest.mark.asyncio
async def test_fresh_run_sem_pausa_executa_4_pipelines(monkeypatch):
    """Todos os 4 pipelines rodam; state.paused_pipeline fica None."""
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    runners_iter = iter([
        _make_fake_runner([_make_text_event("requirements_pipeline", "req-out")]),
        _make_fake_runner([_make_text_event("design_pipeline", "design-out")]),
        _make_fake_runner([_make_text_event("coding_review_pipeline", "cr-out")]),
        _make_fake_runner([_make_text_event("qa_pipeline", "qa-out")]),
    ])
    monkeypatch.setattr(
        "src.agents.orchestrator.agent.Runner",
        lambda **kwargs: next(runners_iter),
    )

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    ctx = _FakeCtx("Prompt do fotógrafo")

    events = [e async for e in orch._run_async_impl(ctx)]

    # Pelo menos 4 textos vistos (um por pipeline)
    texts_seen = [
        p.text
        for e in events
        if e.content
        for p in e.content.parts
        if p.text
    ]
    assert "req-out" in texts_seen
    assert "design-out" in texts_seen
    assert "cr-out" in texts_seen
    assert "qa-out" in texts_seen

    # State final: sem pausa
    assert ctx.session.state.get("paused_pipeline") is None
    assert len(ctx.session.state["accumulated_outputs"]) == 4


# --- U2: FRESH RUN com pausa em qa ---


@pytest.mark.asyncio
async def test_fresh_run_com_pausa_para_em_qa(monkeypatch):
    """qa_pipeline emite long-running call. Iteração para; state.paused_pipeline=qa."""
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    pause_event = _make_long_running_pause_event("qa_pipeline", call_id="call-XYZ")

    runners_iter = iter([
        _make_fake_runner([_make_text_event("requirements_pipeline", "req")]),
        _make_fake_runner([_make_text_event("design_pipeline", "design")]),
        _make_fake_runner([_make_text_event("coding_review_pipeline", "cr")]),
        _make_fake_runner([_make_text_event("qa_pipeline", "planning..."), pause_event]),
    ])
    monkeypatch.setattr(
        "src.agents.orchestrator.agent.Runner",
        lambda **kwargs: next(runners_iter),
    )

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    ctx = _FakeCtx("Prompt do fotógrafo", session_id="outer-1")

    _ = [e async for e in orch._run_async_impl(ctx)]

    assert ctx.session.state["paused_pipeline"] == "qa_pipeline"
    assert ctx.session.state["paused_function_call"]["id"] == "call-XYZ"
    assert ctx.session.state["paused_function_call"]["name"] == "aguardar_aprovacao_humana"
    # _live_runners deve ter o runner do qa
    assert "outer-1" in orch._live_runners
    # 3 outputs antes da pausa
    assert len(ctx.session.state["accumulated_outputs"]) == 3


# --- U3: RESUME aprovar conclui ---


@pytest.mark.asyncio
async def test_resume_aprovar_envia_function_response_e_conclui(monkeypatch):
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    resume_runner = _make_fake_runner(
        [_make_text_event("qa_pipeline", "qa-final-output")]
    )
    # Captura o new_message passado para run_async
    captured = {}
    async def fake_resume(**kwargs):
        captured["new_message"] = kwargs.get("new_message")
        captured["session_id"] = kwargs.get("session_id")
        for e in [_make_text_event("qa_pipeline", "qa-final-output")]:
            yield e
    resume_runner.run_async = fake_resume

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    orch._live_runners["outer-1"] = (resume_runner, "inner-qa-sid")

    ctx = _FakeCtx(
        "aprovar com cuidado em X",
        session_id="outer-1",
        state={
            "paused_pipeline": "qa_pipeline",
            "paused_inner_session_id": "inner-qa-sid",
            "paused_function_call": {
                "id": "call-XYZ",
                "name": "aguardar_aprovacao_humana",
                "args": {
                    "checkpoint_id": "ck-1",
                    "allowed_decisions": ["aprovar", "rejeitar", "solicitar_ajustes"],
                },
            },
            "accumulated_outputs": [
                ("requirements_pipeline", "req"),
                ("design_pipeline", "design"),
                ("coding_review_pipeline", "cr"),
            ],
        },
    )

    _ = [e async for e in orch._run_async_impl(ctx)]

    # Foi enviado function_response no session_id correto
    assert captured["session_id"] == "inner-qa-sid"
    msg = captured["new_message"]
    assert msg.role == "user"
    assert len(msg.parts) == 1
    fr = msg.parts[0].function_response
    assert fr is not None
    assert fr.name == "aguardar_aprovacao_humana"
    assert fr.id == "call-XYZ"
    assert fr.response["decision"] == "aprovar"
    assert fr.response["comments"] == "com cuidado em X"
    assert fr.response["checkpoint_id"] == "ck-1"

    # State limpo
    assert ctx.session.state["paused_pipeline"] is None
    assert ctx.session.state["paused_inner_session_id"] is None
    assert ctx.session.state["paused_function_call"] is None
    # accumulated ganhou qa
    nomes = [n for n, _ in ctx.session.state["accumulated_outputs"]]
    assert "qa_pipeline" in nomes
    # runner limpo
    assert "outer-1" not in orch._live_runners
    # runner.close foi chamado
    resume_runner.close.assert_awaited_once()


# --- U4: RESUME rejeitar com comentário ---


@pytest.mark.asyncio
async def test_resume_rejeitar_preserva_comentario(monkeypatch):
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    captured = {}
    async def fake_resume(**kwargs):
        captured["new_message"] = kwargs.get("new_message")
        for e in [_make_text_event("qa_pipeline", "abortado por rejeicao")]:
            yield e

    runner = _make_fake_runner([])
    runner.run_async = fake_resume

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    orch._live_runners["outer-1"] = (runner, "inner-qa-sid")

    ctx = _FakeCtx(
        "rejeitar criterios insuficientes",
        session_id="outer-1",
        state={
            "paused_pipeline": "qa_pipeline",
            "paused_inner_session_id": "inner-qa-sid",
            "paused_function_call": {
                "id": "call-1",
                "name": "aguardar_aprovacao_humana",
                "args": {
                    "checkpoint_id": "ck-1",
                    "allowed_decisions": ["aprovar", "rejeitar", "solicitar_ajustes"],
                },
            },
            "accumulated_outputs": [],
        },
    )

    _ = [e async for e in orch._run_async_impl(ctx)]

    fr = captured["new_message"].parts[0].function_response
    assert fr.response["decision"] == "rejeitar"
    assert fr.response["comments"] == "criterios insuficientes"


# --- U5: RESUME texto inválido mantém pausa ---


@pytest.mark.asyncio
async def test_resume_texto_invalido_yields_erro_e_mantem_pausa(monkeypatch):
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    runner = _make_fake_runner([])
    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    orch._live_runners["outer-1"] = (runner, "inner-qa-sid")

    state_pause = {
        "paused_pipeline": "qa_pipeline",
        "paused_inner_session_id": "inner-qa-sid",
        "paused_function_call": {
            "id": "call-1",
            "name": "aguardar_aprovacao_humana",
            "args": {"checkpoint_id": "ck-1", "allowed_decisions": ["aprovar", "rejeitar"]},
        },
        "accumulated_outputs": [],
    }
    ctx = _FakeCtx("oi", session_id="outer-1", state=dict(state_pause))

    events = [e async for e in orch._run_async_impl(ctx)]

    # Pelo menos um event de erro com texto contendo "Decisão inválida"
    texts = [
        p.text
        for e in events if e.content
        for p in e.content.parts if p.text
    ]
    assert any("inválida" in t.lower() or "invalid" in t.lower() for t in texts)

    # Pausa intacta
    assert ctx.session.state["paused_pipeline"] == "qa_pipeline"
    assert "outer-1" in orch._live_runners
    # runner.close NÃO foi chamado
    runner.close.assert_not_awaited()


# --- U6: RESUME sem _live_runners (servidor reiniciou) ---


@pytest.mark.asyncio
async def test_resume_sem_live_runner_volta_erro_e_limpa_state():
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    # _live_runners vazio; servidor "foi reiniciado"

    ctx = _FakeCtx(
        "aprovar",
        session_id="outer-1",
        state={
            "paused_pipeline": "qa_pipeline",
            "paused_inner_session_id": "inner-qa-sid",
            "paused_function_call": {
                "id": "call-1", "name": "aguardar_aprovacao_humana",
                "args": {"checkpoint_id": "ck-1", "allowed_decisions": ["aprovar"]},
            },
            "accumulated_outputs": [],
        },
    )

    events = [e async for e in orch._run_async_impl(ctx)]

    texts = [
        p.text
        for e in events if e.content
        for p in e.content.parts if p.text
    ]
    assert any("expirada" in t.lower() or "reinic" in t.lower() for t in texts)
    # State limpo
    assert ctx.session.state["paused_pipeline"] is None


# --- U7: RESUME com pausa encadeada ---


@pytest.mark.asyncio
async def test_resume_com_pausa_encadeada_mantem_runner_e_atualiza_state():
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    second_pause = _make_long_running_pause_event(
        "qa_pipeline", call_id="call-SECOND",
        call_args={
            "checkpoint_id": "ck-2",
            "approval_question": "?",
            "allowed_decisions": ["aprovar", "rejeitar"],
        },
    )

    async def fake_resume(**kwargs):
        for e in [_make_text_event("qa_pipeline", "another check..."), second_pause]:
            yield e

    runner = _make_fake_runner([])
    runner.run_async = fake_resume

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    orch._live_runners["outer-1"] = (runner, "inner-qa-sid")

    ctx = _FakeCtx(
        "aprovar",
        session_id="outer-1",
        state={
            "paused_pipeline": "qa_pipeline",
            "paused_inner_session_id": "inner-qa-sid",
            "paused_function_call": {
                "id": "call-1", "name": "aguardar_aprovacao_humana",
                "args": {"checkpoint_id": "ck-1", "allowed_decisions": ["aprovar", "rejeitar"]},
            },
            "accumulated_outputs": [],
        },
    )

    _ = [e async for e in orch._run_async_impl(ctx)]

    # Estado de pausa atualizado para o segundo call
    assert ctx.session.state["paused_pipeline"] == "qa_pipeline"
    assert ctx.session.state["paused_function_call"]["id"] == "call-SECOND"
    assert ctx.session.state["paused_function_call"]["args"]["checkpoint_id"] == "ck-2"
    # Runner permanece vivo, close NÃO chamado
    assert "outer-1" in orch._live_runners
    runner.close.assert_not_awaited()


# --- U8: preflight ok=False aborta sem rodar pipelines ---


@pytest.mark.asyncio
async def test_preflight_falha_aborta_sem_rodar_pipelines(monkeypatch):
    """Se o health-check de LLM falhar, o orchestrator emite a mensagem de
    abort e NÃO instancia nenhum Runner (nenhum pipeline roda)."""
    from src.agents.orchestrator.agent import _PipelineOrchestrator
    from shared.preflight import PreflightResult

    async def _fail(model=None):
        return PreflightResult(
            ok=False,
            message="[preflight] LLM indisponível. Rode adk/scripts/copilot_auth.py",
        )

    # Sobrescreve o stub autouse (que devolve ok=True) só neste teste.
    monkeypatch.setattr("src.agents.orchestrator.agent.ensure_llm_ready", _fail)

    def _runner_proibido(**kwargs):
        raise AssertionError("Runner não deve ser criado quando o preflight falha")

    monkeypatch.setattr("src.agents.orchestrator.agent.Runner", _runner_proibido)

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    ctx = _FakeCtx("prompt inicial do usuário")

    events = [e async for e in orch._run_async_impl(ctx)]

    texts = [
        p.text
        for e in events if e.content
        for p in e.content.parts if p.text
    ]
    assert any("preflight" in t.lower() for t in texts)
    assert any("copilot_auth.py" in t for t in texts)
    # Abortou antes de _handle_fresh_run → state intacto (sem accumulated_outputs).
    assert "accumulated_outputs" not in ctx.session.state

