"""Smoke test: orchestrator é descoberto pelo ADK e expõe root_agent."""

import pytest


def test_orchestrator_root_agent_importavel():
    from src.agents.orchestrator import root_agent
    assert root_agent is not None
    assert root_agent.name == "orchestrator"


def test_orchestrator_tem_4_pipelines():
    """v4: orchestrator é BaseAgent custom que invoca 4 sub-pipelines em sessão isolada."""
    from src.agents.orchestrator import root_agent
    pipelines = type(root_agent)._pipelines
    assert len(pipelines) == 4


def test_orchestrator_pipelines_esperados():
    """v4: pipelines fixos são requirements → design → coding_review → qa (nesta ordem)."""
    from src.agents.orchestrator import root_agent

    pipelines = type(root_agent)._pipelines
    nomes = [p.name for p in pipelines]
    assert nomes == [
        "requirements_pipeline",
        "design_pipeline",
        "coding_review_pipeline",
        "qa_pipeline",
    ], f"Pipelines em ordem inesperada: {nomes}"


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
