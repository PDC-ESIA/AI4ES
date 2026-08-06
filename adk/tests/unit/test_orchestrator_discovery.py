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
    """Workflow deve conter iterator entre o context engineer e o reviewer."""
    from src.agents.workflow_coding_review.agent import agent as coding_review

    nomes_subagents = [sa.name for sa in coding_review.sub_agents]
    assert nomes_subagents == [
        "cr_context_engineer",
        "task_iterator",
        "cr_review_analyzer",
    ]

    iterator = coding_review.sub_agents[1]
    assert len(iterator.sub_agents) == 1
    loop_agent = iterator.sub_agents[0]
    assert loop_agent.name == "code_execute_loop"
    loop_sub_names = [sa.name for sa in loop_agent.sub_agents]
    assert loop_sub_names == ["cr_coder_agent", "cr_executor_agent"]
