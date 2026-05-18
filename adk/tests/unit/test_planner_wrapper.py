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


from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_invoke_once_retorna_texto_do_evento():
    """_invoke_once coleta texto dos events do Runner."""
    from src.agents.workflow_qa.tools import planner_wrapper

    fake_part = MagicMock()
    fake_part.text = '{"tipo_entrada":"requisito","lifecycle":{"status":"ok"}}'
    fake_event = MagicMock()
    fake_event.content.parts = [fake_part]

    async def fake_run_async(*args, **kwargs):
        yield fake_event

    fake_runner = MagicMock()
    fake_runner.run_async = fake_run_async
    fake_runner.close = AsyncMock()
    fake_session = MagicMock()
    fake_session.id = "sid-test"
    fake_session.user_id = "uid-test"
    fake_runner.session_service.create_session = AsyncMock(return_value=fake_session)

    with patch.object(planner_wrapper, "Runner", return_value=fake_runner):
        result = await planner_wrapper._invoke_once("request body")

    assert "tipo_entrada" in result
    fake_runner.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_invoke_once_exception_retorna_marker_de_erro():
    """Se o Runner explodir, _invoke_once devolve string 'ERROR: ...' (não levanta)."""
    from src.agents.workflow_qa.tools import planner_wrapper

    with patch.object(planner_wrapper, "Runner", side_effect=RuntimeError("boom")):
        result = await planner_wrapper._invoke_once("request body")

    assert result.startswith("ERROR:")
    # Documenta que 'ERROR: ...' tem mais de 8 chars úteis, então não é
    # considerado empty pelo _is_empty — quem decide o retry é invocar_planejamento_qa
    assert planner_wrapper._is_empty(result) is False
