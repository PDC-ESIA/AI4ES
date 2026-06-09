"""Testes da função aguardar_aprovacao_humana (HITL tool do qa_pipeline).

A função em si é um stub — quando registrada como LongRunningFunctionTool,
o ADK pausa antes do corpo executar. Os testes garantem:
  1. Assinatura compatível com Gemini schema (sem `str | None`).
  2. Retorno tipado com as chaves contratuais.
  3. Comportamento determinístico em chamada direta (importante para
     testes integration que invocam sem passar pelo runner).
"""

import inspect

import pytest


@pytest.mark.asyncio
async def test_aguardar_aprovacao_humana_retorna_none_para_pausar_adk():
    """LongRunningFunctionTool só pausa o agente se a função retornar None.

    Referência: google/adk/flows/llm_flows/functions.py:579-583
        if tool.is_long_running:
            if not function_response:
                return None  # não emite function_response → agente pendura

    Retorno truthy (dict, str, etc.) faria ADK emitir function_response
    imediatamente e o LLM continuaria sem aguardar decisão humana.
    """
    from adk.shared.tools.hitl_tool import aguardar_aprovacao_humana

    resultado = await aguardar_aprovacao_humana(
        checkpoint_id="abc",
        approval_question="Você aprova?",
        allowed_decisions=["aprovar", "rejeitar"],
        pause_reason="motivo",
    )

    assert resultado is None, (
        "Stub deve retornar None para que ADK pause o agente. "
        f"Got: {resultado!r}"
    )


def test_aguardar_aprovacao_humana_schema_compativel_com_gemini():
    """Gemini API rejeita anyOf no schema. ADK gera anyOf p/ Union types
    quando empacotados como FunctionTool, e isso bate na Gemini.

    Este teste embrulha a função em LongRunningFunctionTool (mesma classe
    usada em workflow_qa/agent.py) e inspeciona o JSON do
    FunctionDeclaration. O teste falha se o schema gerado contiver
    "any_of" — sinal de que algum parâmetro virou Union no schema.

    Reference: gotcha registrada em CLAUDE.md "Schemas de tool incompatíveis
    com Gemini API".
    """
    from google.adk.tools import LongRunningFunctionTool

    from adk.shared.tools.hitl_tool import aguardar_aprovacao_humana

    tool = LongRunningFunctionTool(aguardar_aprovacao_humana)
    decl_json = tool._get_declaration().model_dump_json(
        exclude_none=True, by_alias=True
    )
    assert "any_of" not in decl_json, (
        f"FunctionDeclaration contém any_of (Gemini API rejeita). "
        f"Confira annotations da função. Schema: {decl_json}"
    )


@pytest.mark.asyncio
async def test_pause_reason_pode_ser_omitido():
    """pause_reason é Optional — função aceita chamada sem ele."""
    from adk.shared.tools.hitl_tool import aguardar_aprovacao_humana

    resultado = await aguardar_aprovacao_humana(
        checkpoint_id="x",
        approval_question="?",
        allowed_decisions=["aprovar"],
    )
    assert resultado is None


def test_aguardar_aprovacao_humana_reexportada_no_init():
    """Tools do qa_agent devem ser importáveis do pacote tools/."""
    from src.agents.qa_agent.tools import aguardar_aprovacao_humana as exported
    from adk.shared.tools.hitl_tool import aguardar_aprovacao_humana as direct
    assert exported is direct
