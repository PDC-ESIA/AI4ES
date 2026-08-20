"""Smoke test: orchestrator é descoberto pelo ADK e expõe root_agent."""


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
    """context_engineer vem antes do task_iterator, que encapsula o loop coder+executor."""
    from src.agents.workflow_coding_review.agent import agent as coding_review

    nomes_subagents = [sa.name for sa in coding_review.sub_agents]

    assert "cr_context_engineer" in nomes_subagents, (
        f"cr_context_engineer ausente. Sub_agents: {nomes_subagents}"
    )

    # O loop deixou de ser sub_agent do topo: quem o invoca (uma vez por task)
    # é o task_iterator, seu único parent.
    assert "task_iterator" in nomes_subagents, (
        f"task_iterator ausente. Sub_agents: {nomes_subagents}"
    )

    # Verifica que context_engineer vem ANTES do iterator (que contém o loop)
    idx_context = nomes_subagents.index("cr_context_engineer")
    idx_iterator = nomes_subagents.index("task_iterator")

    assert idx_context < idx_iterator, (
        f"Ordem errada: context_engineer={idx_context}, task_iterator={idx_iterator}"
    )

    # Verifica que o loop está dentro do iterator, e o coder dentro do loop
    iterator_agent = coding_review.sub_agents[idx_iterator]
    iterator_sub_names = [sa.name for sa in iterator_agent.sub_agents]
    assert iterator_sub_names == ["code_execute_loop"], (
        f"task_iterator deve ter o loop como único sub_agent. "
        f"Sub_agents: {iterator_sub_names}"
    )

    loop_agent = iterator_agent.sub_agents[0]
    loop_sub_names = [sa.name for sa in loop_agent.sub_agents]
    assert any("coder" in n.lower() for n in loop_sub_names), (
        f"coder não encontrado dentro do loop. Sub_agents do loop: {loop_sub_names}"
    )
