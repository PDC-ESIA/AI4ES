"""Wiring interno do pipeline workflow_coding_review (escopo: coder_isolado).

Extraído de `test_orchestrator_discovery.py`: os demais testes daquele
arquivo validam o orchestrator (agnóstico de agente); este valida
especificamente a estrutura interna do `workflow_coding_review` — não
depende de nenhum outro agente.

A lógica deste teste foi atualizada a partir da versão em `develop`, que
refletiu uma mudança de arquitetura: o `code_execute_loop` deixou de ser
sub-agente direto do pipeline e passou a ser encapsulado pelo
`task_iterator` (que o invoca uma vez por task).
"""


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