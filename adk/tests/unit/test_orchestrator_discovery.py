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


def test_workflow_coding_review_inclui_context_engineer():
    """workflow_coding_review deve ter context_engineer antes do coder."""
    from src.agents.workflow_coding_review.agent import agent as coding_review

    nomes_subagents = [sa.name for sa in coding_review.sub_agents]

    assert "cr_context_engineer" in nomes_subagents, (
        f"cr_context_engineer ausente. Sub_agents: {nomes_subagents}"
    )

    # Verifica que vem ANTES do coder
    idx_context = nomes_subagents.index("cr_context_engineer")
    idx_coder = next(
        (i for i, sa in enumerate(coding_review.sub_agents) if "coder" in sa.name.lower()),
        None
    )

    assert idx_coder is not None, "cr_coder_agent não encontrado no pipeline"
    assert idx_context < idx_coder, (
        f"Ordem errada: context_engineer={idx_context}, coder={idx_coder}"
    )
