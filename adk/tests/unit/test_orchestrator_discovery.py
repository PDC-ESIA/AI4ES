"""Smoke test: orchestrator é descoberto pelo ADK e expõe root_agent."""

import pytest


def test_orchestrator_root_agent_importavel():
    from src.agents.orchestrator import root_agent
    assert root_agent is not None
    assert root_agent.name == "orchestrator"


def test_orchestrator_tem_5_workflows_e_4_tools():
    from src.agents.orchestrator import root_agent
    # 5 workflows (AgentTool) + 4 FunctionTools = 9 tools
    assert len(root_agent.tools) == 9


def test_orchestrator_nomes_dos_workflows_presentes():
    """Cada AgentTool deve apontar para um workflow esperado."""
    from src.agents.orchestrator import root_agent
    from google.adk.tools.agent_tool import AgentTool

    nomes_esperados = {
        "requirements_pipeline",
        "design_pipeline",
        "coding_review_pipeline",
        "sdlc_pipeline",
        "qa_pipeline",
    }
    nomes_encontrados = set()
    for t in root_agent.tools:
        if isinstance(t, AgentTool):
            nomes_encontrados.add(t.agent.name)
    assert nomes_esperados.issubset(nomes_encontrados), (
        f"Faltam workflows: {nomes_esperados - nomes_encontrados}"
    )
