"""Tests para workflow_qa/tools/planner_wrapper.py — retry de action_planner."""

import json

import pytest

from src.agents.workflow_qa.tools.planner_wrapper import (
    _is_empty,
    _FALLBACK_BLOCKED_JSON,
)


def test_is_empty_string_vazia():
    assert _is_empty("") is True


def test_is_empty_none():
    assert _is_empty(None) is True


def test_is_empty_apenas_whitespace():
    assert _is_empty("   \n\t  ") is True


def test_is_empty_apenas_backticks():
    """LLMs às vezes devolvem só markers de code block vazios."""
    assert _is_empty("```") is True
    assert _is_empty("``` ```") is True


def test_is_empty_json_valido_pequeno():
    """JSON de bloqueio mínimo (~60 chars) NÃO é empty."""
    json_str = '{"tipo_entrada":"requisito","lifecycle":{"status":"bloqueado"}}'
    assert _is_empty(json_str) is False


def test_is_empty_json_valido_grande():
    """JSON completo do action_planner (~500+ chars) NÃO é empty."""
    json_str = '{"tipo_entrada":"requisito","modo":"requisito","tools":["receber_requisitos"],"casos_de_teste_propostos":["Cenario 1"],"lifecycle":{"status":"planejado_para_execucao","execution_allowed":true,"next_step":"executar_plano"}}'
    assert _is_empty(json_str) is False


def test_fallback_blocked_json_e_parseavel():
    """O fallback DEVE ser JSON parseável com status=bloqueado."""
    parsed = json.loads(_FALLBACK_BLOCKED_JSON)
    assert parsed["lifecycle"]["status"] == "bloqueado"
    assert parsed["lifecycle"]["execution_allowed"] is False
    assert "erro" in parsed
