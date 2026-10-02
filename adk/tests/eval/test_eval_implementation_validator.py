"""Avaliação do `implementation_validator`: o veredito sai de `montar_veredito`, em Python,
então a resposta final é determinística e serve de âncora junto da trajetória."""

import pytest

MODULO = "src.agents.implementation_validator"


@pytest.mark.eval
async def test_aprova_report_verde_com_state_semeado(
    workspace_semeado, evalset, rodar_eval
):
    """Com execução verde, lê o report pelo caminho do state e aprova com a resposta exata."""
    workspace_semeado("validator_verde")
    await rodar_eval(evalset("validator_aprovado"), agent_module=MODULO)


@pytest.mark.eval
async def test_reprova_quando_a_execucao_falhou(workspace_semeado, evalset, rodar_eval):
    """Com a execução falha, reprova, qualquer que seja o julgamento do LLM sobre os critérios."""
    workspace_semeado("validator_falha")
    await rodar_eval(evalset("validator_reprovado_execucao"), agent_module=MODULO)


@pytest.mark.eval
@pytest.mark.eval_juiz
async def test_juiz_llm_aprova_o_veredito_correto(
    workspace_semeado, evalset, rodar_eval
):
    """Um juiz LLM considera a resposta do caminho feliz equivalente à referência."""
    workspace_semeado("validator_verde")
    await rodar_eval(evalset("juiz_validator_aprovado"), agent_module=MODULO)
