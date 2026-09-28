"""Avaliação do `cr_review_analyzer`, endereçado como sub-agente do pipeline de codificação.
Só é avaliável porque o conftest fixa o workspace antes de o reviewer ser importado."""

import pytest

MODULO = "src.agents.workflow_coding_review.agent"
AGENTE = "cr_review_analyzer"


@pytest.mark.eval
async def test_gate_de_cobertura_sobrepoe_o_veredito_do_llm(
    workspace_semeado, evalset, rodar_eval
):
    """Lê o código antes de opinar e, sem cobertura das tasks comprovada, o status sai BLOQUEADO."""
    workspace_semeado("projeto_revisavel")
    await rodar_eval(
        evalset("reviewer_gate_cobertura"), agent_module=MODULO, agent_name=AGENTE
    )
