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
