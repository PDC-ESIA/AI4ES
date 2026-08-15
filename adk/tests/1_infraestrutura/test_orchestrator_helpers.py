"""Testes dos helpers puros do orchestrator (sem dependência de ADK runtime)."""

import pytest


# --- _parse_decision ---


def test_parse_decision_exato():
    from src.agents.orchestrator._helpers import _parse_decision
    assert _parse_decision("aprovar", ["aprovar", "rejeitar"]) == ("aprovar", "")


def test_parse_decision_case_insensitive():
    from src.agents.orchestrator._helpers import _parse_decision
    assert _parse_decision("APROVAR", ["aprovar"]) == ("aprovar", "")
    assert _parse_decision("Aprovar", ["aprovar"]) == ("aprovar", "")


def test_parse_decision_com_pontuacao_no_primeiro_token():
    from src.agents.orchestrator._helpers import _parse_decision
    assert _parse_decision("aprovar.", ["aprovar"]) == ("aprovar", "")
    assert _parse_decision("aprovar,", ["aprovar"]) == ("aprovar", "")


def test_parse_decision_com_comentarios():
    from src.agents.orchestrator._helpers import _parse_decision
    decision, comments = _parse_decision(
        "aprovar com cuidado em X",
        ["aprovar", "rejeitar"],
    )
    assert decision == "aprovar"
    assert comments == "com cuidado em X"


def test_parse_decision_prefixo_casa():
    from src.agents.orchestrator._helpers import _parse_decision
    # "aprov" é prefixo de "aprovar"
    assert _parse_decision("aprov", ["aprovar"]) == ("aprovar", "")


def test_parse_decision_invalido_levanta():
    from src.agents.orchestrator._helpers import _parse_decision
    with pytest.raises(ValueError, match="oi"):
        _parse_decision("oi", ["aprovar", "rejeitar"])


def test_parse_decision_vazio_levanta():
    from src.agents.orchestrator._helpers import _parse_decision
    with pytest.raises(ValueError, match="vazio"):
        _parse_decision("   ", ["aprovar"])


def test_parse_decision_solicitar_ajustes_com_comentarios():
    from src.agents.orchestrator._helpers import _parse_decision
    decision, comments = _parse_decision(
        "solicitar_ajustes Adicione cenário negativo para upload duplicado",
        ["aprovar", "rejeitar", "solicitar_ajustes"],
    )
    assert decision == "solicitar_ajustes"
    assert comments == "Adicione cenário negativo para upload duplicado"


# --- _is_pending_long_running_call ---


def _make_event(long_running_ids=None, function_call=None):
    """Helper local: monta um Event mínimo com Content + Part."""
    from google.adk.events.event import Event
    from google.genai import types

    parts = []
    if function_call:
        parts.append(types.Part(function_call=function_call))

    content = types.Content(role="model", parts=parts) if parts else None

    return Event(
        author="qa_pipeline",
        invocation_id="inv-1",
        content=content,
        long_running_tool_ids=set(long_running_ids) if long_running_ids else None,
    )


def test_is_pending_long_running_call_detecta_via_ids():
    from google.genai import types
    from src.agents.orchestrator._helpers import _is_pending_long_running_call

    fc = types.FunctionCall(
        id="call-1", name="aguardar_aprovacao_humana", args={}
    )
    event = _make_event(long_running_ids={"call-1"}, function_call=fc)
    part = event.content.parts[0]

    assert _is_pending_long_running_call(part, event) is True


def test_is_pending_long_running_call_ignora_function_call_nao_long_running():
    from google.genai import types
    from src.agents.orchestrator._helpers import _is_pending_long_running_call

    fc = types.FunctionCall(id="call-2", name="tool_normal", args={})
    event = _make_event(long_running_ids=None, function_call=fc)
    part = event.content.parts[0]

    assert _is_pending_long_running_call(part, event) is False


def test_is_pending_long_running_call_part_sem_function_call():
    from google.genai import types
    from src.agents.orchestrator._helpers import _is_pending_long_running_call

    event = _make_event(long_running_ids={"call-1"})
    # part texto, sem function_call
    text_part = types.Part(text="oi")

    assert _is_pending_long_running_call(text_part, event) is False


def test_is_pending_long_running_call_id_diferente():
    from google.genai import types
    from src.agents.orchestrator._helpers import _is_pending_long_running_call

    fc = types.FunctionCall(id="call-X", name="tool", args={})
    event = _make_event(long_running_ids={"call-OTHER"}, function_call=fc)
    part = event.content.parts[0]

    assert _is_pending_long_running_call(part, event) is False


# --- _set_pause_state / _clear_pause_state ---


def test_set_pause_state_grava_tres_chaves():
    from src.agents.orchestrator._helpers import _set_pause_state

    state = {}
    _set_pause_state(
        state,
        pipeline_name="qa_pipeline",
        inner_session_id="sid-abc",
        function_call_id="call-1",
        function_call_name="aguardar_aprovacao_humana",
        function_call_args={"checkpoint_id": "ck-1", "allowed_decisions": ["aprovar"]},
    )

    assert state["paused_pipeline"] == "qa_pipeline"
    assert state["paused_inner_session_id"] == "sid-abc"
    assert state["paused_function_call"] == {
        "id": "call-1",
        "name": "aguardar_aprovacao_humana",
        "args": {"checkpoint_id": "ck-1", "allowed_decisions": ["aprovar"]},
    }


def test_clear_pause_state_zera_tres_chaves():
    from src.agents.orchestrator._helpers import _clear_pause_state

    state = {
        "paused_pipeline": "qa_pipeline",
        "paused_inner_session_id": "sid",
        "paused_function_call": {"id": "x"},
        "accumulated_outputs": [("req", "...")],  # NÃO deve ser limpo
    }
    _clear_pause_state(state)

    assert state["paused_pipeline"] is None
    assert state["paused_inner_session_id"] is None
    assert state["paused_function_call"] is None
    # accumulated_outputs preservado
    assert state["accumulated_outputs"] == [("req", "...")]


# --- _extract_user_text ---


class _FakePart:
    def __init__(self, text):
        self.text = text


class _FakeUserContent:
    def __init__(self, parts):
        self.parts = parts


class _FakeCtx:
    def __init__(self, user_content):
        self.user_content = user_content


def test_extract_user_text_concatena_parts():
    from src.agents.orchestrator._helpers import _extract_user_text

    ctx = _FakeCtx(_FakeUserContent([_FakePart("foo"), _FakePart("bar")]))
    assert _extract_user_text(ctx) == "foo\nbar"


def test_extract_user_text_sem_content():
    from src.agents.orchestrator._helpers import _extract_user_text
    ctx = _FakeCtx(None)
    assert _extract_user_text(ctx) == ""


def test_extract_user_text_part_sem_text():
    from src.agents.orchestrator._helpers import _extract_user_text

    class P:
        text = None
    ctx = _FakeCtx(_FakeUserContent([P(), _FakePart("hello")]))
    assert _extract_user_text(ctx) == "hello"


# --- _build_input ---


def test_build_input_sem_accumulated():
    from src.agents.orchestrator._helpers import _build_input
    assert _build_input("prompt original", []) == "prompt original"


def test_build_input_com_accumulated():
    from src.agents.orchestrator._helpers import _build_input
    result = _build_input(
        "prompt",
        [("requirements_pipeline", "RF-001: criar ensaio"), ("design_pipeline", "diag.md")],
    )
    assert "prompt" in result
    assert "CONTEXTO DAS FASES ANTERIORES" in result
    assert "### Output de requirements_pipeline" in result
    assert "RF-001: criar ensaio" in result
    assert "### Output de design_pipeline" in result
    assert "diag.md" in result


def test_build_input_trunca_output_em_8000_chars():
    from src.agents.orchestrator._helpers import _build_input
    huge = "x" * 20000
    result = _build_input("prompt", [("req", huge)])
    # 8000 chars do output devem aparecer; o resto não
    assert "x" * 8000 in result
    # Tolerância: pode ter sufixo de truncagem; verifica que não tem 20000 x's seguidos
    assert "x" * 20000 not in result


# --- _build_function_response_payload ---


def test_build_function_response_payload_estrutura():
    from src.agents.orchestrator._helpers import _build_function_response_payload

    p = _build_function_response_payload(
        decision="aprovar",
        comments="cuidado em X",
        checkpoint_id="ck-1",
    )
    assert p["decision"] == "aprovar"
    assert p["comments"] == "cuidado em X"
    assert p["checkpoint_id"] == "ck-1"
    assert p["reviewer"] == "usuario"
    # validated_at é ISO-8601 UTC com sufixo Z
    assert p["validated_at"].endswith("Z")
    assert "T" in p["validated_at"]
