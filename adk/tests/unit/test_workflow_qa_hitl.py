"""Testes do registro de aguardar_aprovacao_humana no workflow_qa."""

from google.adk.tools import LongRunningFunctionTool


def test_workflow_qa_registra_aguardar_aprovacao_como_longrunning():
    """A tool DEVE ser LongRunningFunctionTool, não FunctionTool."""
    from src.agents.workflow_qa.agent import agent

    long_running_tools = [
        t for t in agent.tools if isinstance(t, LongRunningFunctionTool)
    ]
    assert len(long_running_tools) == 1, (
        f"Esperado exatamente 1 LongRunningFunctionTool. "
        f"Encontradas: {[type(t).__name__ for t in agent.tools]}"
    )

    decl = long_running_tools[0]._get_declaration()
    assert decl.name == "aguardar_aprovacao_humana", (
        f"Nome inesperado: {decl.name}"
    )


def test_workflow_qa_instruction_menciona_aguardar_aprovacao():
    """O instruction precisa instruir o LLM a chamar a tool quando hitl_checkpoint.required=true."""
    from src.agents.workflow_qa.agent import agent

    assert "aguardar_aprovacao_humana" in agent.instruction
    assert "hitl_checkpoint" in agent.instruction


def test_workflow_qa_aguardar_aprovacao_schema_nao_quebra_gemini():
    """O FunctionDeclaration não pode ter any_of (Gemini 400 INVALID_ARGUMENT)."""
    from src.agents.workflow_qa.agent import agent

    long_running_tools = [
        t for t in agent.tools if isinstance(t, LongRunningFunctionTool)
    ]
    decl_json = long_running_tools[0]._get_declaration().model_dump_json(
        exclude_none=True, by_alias=True
    )
    assert "any_of" not in decl_json, (
        f"Schema contém any_of (Gemini API rejeita): {decl_json}"
    )
