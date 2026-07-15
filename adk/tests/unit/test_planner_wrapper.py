"""Tests para workflow_qa/tools/planner_wrapper.py — retry de action_planner."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.workflow_qa.tools.planner_wrapper import (
    _is_empty,
    _FALLBACK_BLOCKED_JSON,
    _normalize_structured_json,
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


def test_normalize_structured_json_rejeita_texto_nao_json():
    assert _normalize_structured_json("ERROR: TimeoutError: boom") is None
    assert _normalize_structured_json("resposta livre") is None


def test_normalize_structured_json_rejeita_json_sem_lifecycle_status():
    assert _normalize_structured_json('{"foo": "bar"}') is None
    assert _normalize_structured_json('{"lifecycle": {}}') is None


def test_normalize_structured_json_aceita_json_valido():
    text = '{"tipo_entrada":"requisito","lifecycle":{"status":"ok"}}'
    normalized = _normalize_structured_json(text)
    assert normalized is not None
    parsed = json.loads(normalized)
    assert parsed["lifecycle"]["status"] == "ok"


def test_normalize_structured_json_aceita_json_em_code_fence():
    fenced = """```json
{"tipo_entrada":"requisito","lifecycle":{"status":"ok"}}
```"""
    normalized = _normalize_structured_json(fenced)
    assert normalized is not None
    parsed = json.loads(normalized)
    assert parsed["lifecycle"]["status"] == "ok"


@pytest.mark.asyncio
async def test_invocar_retorna_first_quando_valido():
    """Primeira chamada retorna JSON válido → não tenta segunda."""
    from src.agents.workflow_qa.tools import planner_wrapper

    valid_json = '{"tipo_entrada":"requisito","lifecycle":{"status":"ok"}}'

    with patch.object(planner_wrapper, "_invoke_once", AsyncMock(return_value=valid_json)) as mock_invoke:
        result = await planner_wrapper.invocar_planejamento_qa("req")

    assert json.loads(result) == json.loads(valid_json)
    assert mock_invoke.await_count == 1


@pytest.mark.asyncio
async def test_invocar_tenta_segunda_quando_first_empty():
    """Primeira call empty + segunda call JSON válido → retorna o JSON da segunda."""
    from src.agents.workflow_qa.tools import planner_wrapper

    valid_json = '{"tipo_entrada":"requisito","lifecycle":{"status":"ok"}}'

    with patch.object(
        planner_wrapper, "_invoke_once",
        AsyncMock(side_effect=["", valid_json]),
    ) as mock_invoke:
        result = await planner_wrapper.invocar_planejamento_qa("req")

    assert json.loads(result) == json.loads(valid_json)
    assert mock_invoke.await_count == 2


@pytest.mark.asyncio
async def test_invocar_tenta_segunda_quando_first_timeout_error():
    """Primeira call com erro do runner deve acionar segunda tentativa."""
    from src.agents.workflow_qa.tools import planner_wrapper

    valid_json = '{"tipo_entrada":"requisito","lifecycle":{"status":"ok"}}'

    with patch.object(
        planner_wrapper, "_invoke_once",
        AsyncMock(side_effect=["ERROR: TimeoutError: boom", valid_json]),
    ) as mock_invoke:
        result = await planner_wrapper.invocar_planejamento_qa("req")

    assert json.loads(result) == json.loads(valid_json)
    assert mock_invoke.await_count == 2


@pytest.mark.asyncio
async def test_invocar_tenta_segunda_quando_first_invalido_nao_vazio():
    """Payload não-vazio porém inválido deve ser tratado como falha recuperável."""
    from src.agents.workflow_qa.tools import planner_wrapper

    valid_json = '{"tipo_entrada":"requisito","lifecycle":{"status":"ok"}}'

    with patch.object(
        planner_wrapper, "_invoke_once",
        AsyncMock(side_effect=["resposta livre inválida", valid_json]),
    ) as mock_invoke:
        result = await planner_wrapper.invocar_planejamento_qa("req")

    assert json.loads(result) == json.loads(valid_json)
    assert mock_invoke.await_count == 2


@pytest.mark.asyncio
async def test_invocar_fallback_quando_ambas_empty():
    """Ambas as calls empty → devolve _FALLBACK_BLOCKED_JSON."""
    from src.agents.workflow_qa.tools import planner_wrapper

    with patch.object(
        planner_wrapper, "_invoke_once",
        AsyncMock(side_effect=["", "   "]),
    ) as mock_invoke:
        result = await planner_wrapper.invocar_planejamento_qa("req")

    assert result == planner_wrapper._FALLBACK_BLOCKED_JSON
    assert mock_invoke.await_count == 2
    parsed = json.loads(result)
    assert parsed["lifecycle"]["status"] == "bloqueado"


@pytest.mark.asyncio
async def test_invocar_fallback_quando_duas_falhas_timeout():
    """Timeout/erro nas duas tentativas deve devolver JSON de bloqueio."""
    from src.agents.workflow_qa.tools import planner_wrapper

    with patch.object(
        planner_wrapper, "_invoke_once",
        AsyncMock(side_effect=["ERROR: TimeoutError: one", "ERROR: TimeoutError: two"]),
    ) as mock_invoke:
        result = await planner_wrapper.invocar_planejamento_qa("req")

    assert result == planner_wrapper._FALLBACK_BLOCKED_JSON
    assert mock_invoke.await_count == 2
    parsed = json.loads(result)
    assert parsed["lifecycle"]["status"] == "bloqueado"


@pytest.mark.asyncio
async def test_invocar_retry_suffix_adicionado_na_segunda_call():
    """Segunda call recebe request + retry suffix com aviso ANTI-EMPTY."""
    from src.agents.workflow_qa.tools import planner_wrapper

    valid_json = '{"tipo_entrada":"requisito","lifecycle":{"status":"ok"}}'
    mock_invoke = AsyncMock(side_effect=["", valid_json])

    with patch.object(planner_wrapper, "_invoke_once", mock_invoke):
        await planner_wrapper.invocar_planejamento_qa("requisito original")

    # Segunda chamada (índice 1) deve incluir o request + suffix de retry
    second_call_args = mock_invoke.await_args_list[1]
    second_request = second_call_args[0][0]  # primeiro arg posicional
    assert "requisito original" in second_request
    assert "ATENÇÃO" in second_request
    assert "PROTOCOLO ANTI-EMPTY" in second_request


def test_workflow_qa_usa_function_tool_e_nao_agent_tool_para_planner():
    """qa_pipeline.tools NÃO contém mais AgentTool(action_planner_agent);
    contém FunctionTool(invocar_planejamento_qa)."""
    from src.agents.workflow_qa.agent import agent as qa_pipeline

    tool_names = []
    for t in qa_pipeline.tools:
        if hasattr(t, "func"):
            tool_names.append(t.func.__name__)
        elif hasattr(t, "agent"):
            tool_names.append(f"AgentTool({t.agent.name})")
        else:
            tool_names.append(type(t).__name__)

    assert "invocar_planejamento_qa" in tool_names
    assert "AgentTool(action_planner)" not in tool_names


def test_workflow_qa_instruction_menciona_invocar_planejamento_qa():
    """_INSTRUCTION foi atualizado pra referenciar a nova tool."""
    from src.agents.workflow_qa.agent import agent as qa_pipeline
    assert "invocar_planejamento_qa" in qa_pipeline.instruction
    # E NÃO menciona mais "Encaminhe a entrada ao action_planner_agent"
    # (pode mencionar action_planner_agent como conceito histórico em outro lugar)
    assert "Encaminhe a entrada ao action_planner_agent" not in qa_pipeline.instruction
