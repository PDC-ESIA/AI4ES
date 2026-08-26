"""Wiring interno do pipeline workflow_coding_review (escopo: coder_isolado).

Extraído de `test_orchestrator_discovery.py`: os demais testes daquele
arquivo validam o orchestrator (agnóstico de agente); este valida
especificamente a estrutura interna do `workflow_coding_review` — não
depende de nenhum outro agente.
"""


def test_workflow_coding_review_inclui_context_engineer():
    """workflow_coding_review deve ter context_engineer antes do loop coder+executor."""
    from src.agents.workflow_coding_review.agent import agent as coding_review

    nomes_subagents = [sa.name for sa in coding_review.sub_agents]

    assert "cr_context_engineer" in nomes_subagents, (
        f"cr_context_engineer ausente. Sub_agents: {nomes_subagents}"
    )

    # O coder agora vive DENTRO do LoopAgent "code_execute_loop"
    assert "code_execute_loop" in nomes_subagents, (
        f"code_execute_loop ausente. Sub_agents: {nomes_subagents}"
    )

    # Verifica que context_engineer vem ANTES do loop (que contém o coder)
    idx_context = nomes_subagents.index("cr_context_engineer")
    idx_loop = nomes_subagents.index("code_execute_loop")

    assert idx_context < idx_loop, (
        f"Ordem errada: context_engineer={idx_context}, code_execute_loop={idx_loop}"
    )

    # Verifica que o coder está de fato dentro do loop
    loop_agent = coding_review.sub_agents[idx_loop]
    loop_sub_names = [sa.name for sa in loop_agent.sub_agents]
    assert any("coder" in n.lower() for n in loop_sub_names), (
        f"coder não encontrado dentro do loop. Sub_agents do loop: {loop_sub_names}"
    )
