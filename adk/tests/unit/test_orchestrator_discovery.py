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


def test_workflow_coding_inclui_context_engineer():
    """workflow_coding deve ter context_engineer entre requirements e architect."""
    from src.agents.workflow_coding.agent import agent as workflow_coding

    nomes_subagents = [sa.name for sa in workflow_coding.sub_agents]

    assert "context_engineer" in nomes_subagents, (
        f"context_engineer ausente. Sub_agents: {nomes_subagents}"
    )

    # Verifica que vem APÓS requirements e ANTES de architect
    idx_requirements = next(
        (i for i, sa in enumerate(workflow_coding.sub_agents) if "requirements" in sa.name.lower()),
        None
    )
    idx_context = nomes_subagents.index("context_engineer")
    idx_architect = next(
        (i for i, sa in enumerate(workflow_coding.sub_agents) if "architect" in sa.name.lower()),
        None
    )

    assert idx_requirements is not None, "requirements_agent não encontrado no pipeline"
    assert idx_architect is not None, "architect_agent não encontrado no pipeline"
    assert idx_requirements < idx_context < idx_architect, (
        f"Ordem errada: requirements={idx_requirements}, context_engineer={idx_context}, architect={idx_architect}"
    )
