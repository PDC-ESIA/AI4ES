"""Testes das funções aguardar_resolucao_doubt / aguardar_decisao_validacao
(HITL tools do Time 2 / Design).

Espelha adk/tests/unit/test_hitl_tool.py — mesmo padrão, uma rodada por
função.
"""

import pytest


@pytest.mark.asyncio
async def test_aguardar_resolucao_doubt_retorna_none_para_pausar_adk():
    """LongRunningFunctionTool só pausa o agente se a função retornar None.

    Referência: google/adk/flows/llm_flows/functions.py:579-583
    """
    from adk.shared.tools.design_hitl_tool import aguardar_resolucao_doubt

    resultado = await aguardar_resolucao_doubt(
        checkpoint_id="HU-001,HU-002",
        approval_question="Resolva os bloqueios?",
        allowed_decisions=["retomar", "cancelar"],
        pause_reason="Doubt_Artifacts bloqueados",
    )

    assert resultado is None, (
        "Stub deve retornar None para que ADK pause o agente. "
        f"Got: {resultado!r}"
    )


def test_aguardar_resolucao_doubt_schema_compativel_com_gemini():
    """Gemini API rejeita anyOf no schema gerado a partir de Union types."""
    from google.adk.tools import LongRunningFunctionTool

    from adk.shared.tools.design_hitl_tool import aguardar_resolucao_doubt

    tool = LongRunningFunctionTool(aguardar_resolucao_doubt)
    decl_json = tool._get_declaration().model_dump_json(
        exclude_none=True, by_alias=True
    )
    assert "any_of" not in decl_json, (
        f"FunctionDeclaration contém any_of (Gemini API rejeita). "
        f"Confira annotations da função. Schema: {decl_json}"
    )


@pytest.mark.asyncio
async def test_aguardar_resolucao_doubt_pause_reason_pode_ser_omitido():
    """pause_reason é Optional — função aceita chamada sem ele."""
    from adk.shared.tools.design_hitl_tool import aguardar_resolucao_doubt

    resultado = await aguardar_resolucao_doubt(
        checkpoint_id="HU-001",
        approval_question="?",
        allowed_decisions=["retomar", "cancelar"],
    )
    assert resultado is None


def test_aguardar_resolucao_doubt_reexportada_no_init():
    """Tool deve ser importável do pacote adk/shared/tools/."""
    from adk.shared.tools import aguardar_resolucao_doubt as exported
    from adk.shared.tools.design_hitl_tool import (
        aguardar_resolucao_doubt as direct,
    )
    assert exported is direct


@pytest.mark.asyncio
async def test_aguardar_decisao_validacao_retorna_none_para_pausar_adk():
    """LongRunningFunctionTool só pausa o agente se a função retornar None."""
    from adk.shared.tools.design_hitl_tool import aguardar_decisao_validacao

    resultado = await aguardar_decisao_validacao(
        checkpoint_id="diagrama_HU-001_cadastro.mmd",
        approval_question="Resolvido fora do ciclo automático ou abandonar o artefato?",
        allowed_decisions=["resolvido", "abandonar_artefato"],
        pause_reason="camada semântica falhou após 2 tentativas",
    )

    assert resultado is None, (
        "Stub deve retornar None para que ADK pause o agente. "
        f"Got: {resultado!r}"
    )


def test_aguardar_decisao_validacao_schema_compativel_com_gemini():
    """Gemini API rejeita anyOf no schema gerado a partir de Union types."""
    from google.adk.tools import LongRunningFunctionTool

    from adk.shared.tools.design_hitl_tool import aguardar_decisao_validacao

    tool = LongRunningFunctionTool(aguardar_decisao_validacao)
    decl_json = tool._get_declaration().model_dump_json(
        exclude_none=True, by_alias=True
    )
    assert "any_of" not in decl_json, (
        f"FunctionDeclaration contém any_of (Gemini API rejeita). "
        f"Confira annotations da função. Schema: {decl_json}"
    )


@pytest.mark.asyncio
async def test_aguardar_decisao_validacao_pause_reason_pode_ser_omitido():
    """pause_reason é Optional — função aceita chamada sem ele."""
    from adk.shared.tools.design_hitl_tool import aguardar_decisao_validacao

    resultado = await aguardar_decisao_validacao(
        checkpoint_id="HU-001",
        approval_question="?",
        allowed_decisions=["resolvido", "abandonar_artefato"],
    )
    assert resultado is None


def test_aguardar_decisao_validacao_reexportada_no_init():
    """Tool deve ser importável do pacote adk/shared/tools/."""
    from adk.shared.tools import aguardar_decisao_validacao as exported
    from adk.shared.tools.design_hitl_tool import (
        aguardar_decisao_validacao as direct,
    )
    assert exported is direct
