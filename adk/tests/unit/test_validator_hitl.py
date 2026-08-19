"""Testes do registro de aguardar_decisao_validacao no agente validator
(Time 2 / Design).

Mesmo padrão de adk/tests/unit/test_workflow_qa_hitl.py.
"""

from google.adk.tools import LongRunningFunctionTool


def test_validator_registra_aguardar_decisao_validacao_como_longrunning():
    """A tool DEVE ser LongRunningFunctionTool, não FunctionTool comum."""
    from src.agents.validator.agent import agent

    long_running_tools = [
        t for t in agent.tools if isinstance(t, LongRunningFunctionTool)
    ]
    assert len(long_running_tools) == 1, (
        f"Esperado exatamente 1 LongRunningFunctionTool. "
        f"Encontradas: {[type(t).__name__ for t in agent.tools]}"
    )

    decl = long_running_tools[0]._get_declaration()
    assert decl.name == "aguardar_decisao_validacao", (
        f"Nome inesperado: {decl.name}"
    )


def test_validator_instruction_menciona_aguardar_decisao_validacao():
    """O instruction precisa instruir o LLM a chamar a tool ao esgotar as 2 tentativas."""
    from src.agents.validator.agent import agent

    assert "aguardar_decisao_validacao" in agent.instruction
    assert "2 ciclos" in agent.instruction or "2 tentativas" in agent.instruction


def test_validator_aguardar_decisao_validacao_schema_nao_quebra_gemini():
    """O FunctionDeclaration não pode ter any_of (Gemini 400 INVALID_ARGUMENT)."""
    from src.agents.validator.agent import agent

    long_running_tools = [
        t for t in agent.tools if isinstance(t, LongRunningFunctionTool)
    ]
    decl_json = long_running_tools[0]._get_declaration().model_dump_json(
        exclude_none=True, by_alias=True
    )
    assert "any_of" not in decl_json, (
        f"Schema contém any_of (Gemini API rejeita): {decl_json}"
    )
