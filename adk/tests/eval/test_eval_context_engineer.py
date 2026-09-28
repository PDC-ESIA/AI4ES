"""Avaliação do `cr_context_engineer`, endereçado como sub-agente do pipeline de codificação.
Os argumentos das tools são texto livre do LLM, então os casos comparam só nomes."""

import pytest

MODULO = "src.agents.workflow_coding_review.agent"
AGENTE = "cr_context_engineer"


@pytest.mark.eval
async def test_protocolo_de_bloqueio_emite_as_tres_tools(
    workspace_semeado, evalset, rodar_eval
):
    """Com requisitos bloqueados, chama as três tools do protocolo na ordem, até a que pausa o pipeline."""
    workspace_semeado("projeto_completo")
    await rodar_eval(
        evalset("ce_protocolo_bloqueio"), agent_module=MODULO, agent_name=AGENTE
    )


@pytest.mark.eval
async def test_nao_bloqueia_por_nome_de_arquivo_do_design(
    workspace_semeado, evalset, rodar_eval
):
    """Não bloqueia só porque a análise técnica tem nome fora da convenção."""
    workspace_semeado("projeto_design_torto")
    await rodar_eval(
        evalset("ce_gate_nome_design"), agent_module=MODULO, agent_name=AGENTE
    )


@pytest.mark.eval
async def test_caminho_feliz_age_em_vez_de_narrar(
    workspace_semeado, evalset, rodar_eval
):
    """Com requisitos e design completos, lê as duas fases e persiste tasks e contexto, em vez de só anunciar."""
    workspace_semeado("projeto_completo")
    await rodar_eval(
        evalset("ce_caminho_feliz"), agent_module=MODULO, agent_name=AGENTE
    )
