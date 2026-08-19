"""Testes da helper _is_empty_response (detecção de resposta vazia do LLM)."""

import pytest

from src.agents.orchestrator._helpers import _is_empty_response


def test_string_vazia_e_empty():
    assert _is_empty_response("") is True


def test_so_whitespace_e_empty():
    assert _is_empty_response("   ") is True
    assert _is_empty_response("\n\n") is True
    assert _is_empty_response("\t \n") is True


def test_none_e_empty():
    assert _is_empty_response(None) is True


def test_texto_real_nao_e_empty():
    assert _is_empty_response("ok") is False
    assert _is_empty_response("plan generated") is False


def test_json_curto_nao_e_empty():
    assert _is_empty_response("{}") is False


def test_texto_com_whitespace_lateral_nao_e_empty():
    assert _is_empty_response("  ok  ") is False
