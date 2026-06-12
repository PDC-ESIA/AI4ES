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
    """workflow_coding deve ter context_engineer entre requirements e implementation."""
    from src.agents.workflow_coding.agent import CodingOrchestrator

    stages = CodingOrchestrator._stages
    nomes_stages = [sa.name for sa in stages]

    assert "context_engineer" in nomes_stages, (
        f"context_engineer ausente. Stages: {nomes_stages}"
    )

    # Verifica que vem APÓS requirements e ANTES de implementation
    # (architecture_agent está desativado no pipeline atual)
    idx_requirements = next(
        (i for i, sa in enumerate(stages) if "requirements" in sa.name.lower()),
        None
    )
    idx_context = nomes_stages.index("context_engineer")
    idx_implementation = next(
        (i for i, sa in enumerate(stages) if "coder" in sa.name.lower()),
        None
    )

    assert idx_requirements is not None, "requirements_agent não encontrado no pipeline"
    assert idx_implementation is not None, "coder_agent não encontrado no pipeline"
    assert idx_requirements < idx_context < idx_implementation, (
        f"Ordem errada: requirements={idx_requirements}, context_engineer={idx_context}, implementation={idx_implementation}"
    )

