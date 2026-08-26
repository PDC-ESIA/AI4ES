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
