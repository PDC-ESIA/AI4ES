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
