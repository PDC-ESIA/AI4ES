"""Testes do registro de aguardar_resolucao_doubt no pipeline_controller
do workflow_design_pipeline (Time 2 / Design).

Espelha adk/tests/unit/test_workflow_qa_hitl.py.
"""

from google.adk.tools import LongRunningFunctionTool


def test_pipeline_controller_registra_aguardar_resolucao_doubt_como_longrunning():
    """A tool DEVE ser LongRunningFunctionTool, não FunctionTool comum."""
    from src.agents.workflow_design_pipeline.agent import pipeline_controller

    long_running_tools = [
        t for t in pipeline_controller.tools if isinstance(t, LongRunningFunctionTool)
    ]
    assert len(long_running_tools) == 1, (
        f"Esperado exatamente 1 LongRunningFunctionTool. "
        f"Encontradas: {[type(t).__name__ for t in pipeline_controller.tools]}"
    )

    decl = long_running_tools[0]._get_declaration()
    assert decl.name == "aguardar_resolucao_doubt", (
        f"Nome inesperado: {decl.name}"
    )


def test_pipeline_controller_instruction_menciona_aguardar_resolucao_doubt():
    """O instruction precisa instruir o LLM a chamar a tool quando has_blocks=true."""
    from src.agents.workflow_design_pipeline.agent import pipeline_controller

    assert "aguardar_resolucao_doubt" in pipeline_controller.instruction
    assert "has_blocks" in pipeline_controller.instruction
    assert "check_active_blocks" in pipeline_controller.instruction


def test_pipeline_controller_aguardar_resolucao_doubt_schema_nao_quebra_gemini():
    """O FunctionDeclaration não pode ter any_of (Gemini 400 INVALID_ARGUMENT)."""
    from src.agents.workflow_design_pipeline.agent import pipeline_controller

    long_running_tools = [
        t for t in pipeline_controller.tools if isinstance(t, LongRunningFunctionTool)
    ]
    decl_json = long_running_tools[0]._get_declaration().model_dump_json(
        exclude_none=True, by_alias=True
    )
    assert "any_of" not in decl_json, (
        f"Schema contém any_of (Gemini API rejeita): {decl_json}"
    )
