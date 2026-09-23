"""Avaliação do `cr_context_engineer` — a porta de entrada do Time 4.

Endereçado como sub-agente do pipeline (`agent_name`), sem rodar o pipeline inteiro.

Aqui a métrica nativa não serve: `tool_trajectory_avg_score` exige igualdade **exata
de argumentos**, e os deste agente são descrição em texto livre escrita pelo LLM. Por
isso os casos usam `ai4es_tool_sequence_in_order`, que compara só a sequência de nomes.
"""

import pytest

MODULO = "src.agents.workflow_coding_review.agent"
AGENTE = "cr_context_engineer"


@pytest.mark.eval
async def test_protocolo_de_bloqueio_emite_as_tres_tools(
    workspace_semeado, evalset, rodar_eval
):
    """Manifesto `status: blocked` tem de disparar as três tools, na ordem.

    `tool_gerar_doubt_artifact` → `tool_emitir_manifesto_bloqueado` →
    `aguardar_resolucao_bloqueio`. A terceira é o `LongRunningFunctionTool` que
    **pausa o pipeline** para o humano; sem ela, um doubt escrito em disco não pausa
    nada e o pipeline segue para o coder sem contrato.

    O ADK não aceita chamadas de tool em paralelo, então são três turnos e três
    oportunidades de o modelo abandonar o protocolo no meio. Nenhum teste do
    repositório cobre isso hoje.
    """
    workspace_semeado("projeto_completo")
    await rodar_eval(
        evalset("ce_protocolo_bloqueio"), agent_module=MODULO, agent_name=AGENTE
    )


@pytest.mark.eval
async def test_bloqueia_quando_o_design_erra_o_nome_do_arquivo(
    workspace_semeado, evalset, rodar_eval
):
    """Reproduz o incidente de 13/08 — o portão do Passo 2 é *string matching*.

    Os requisitos estão completos e a análise técnica existe em disco, mas com o nome
    `analise_arquitetural_*.md`. Como `context_engineer_tools.py:332` compara
    `nome.startswith("analise_tecnica_")`, a tool devolve
    `artefatos_minimos_presentes=False` e o agente deve bloquear.

    O PR #405 endureceu o prompt do Time 2 para o nome sair certo; este caso mede a
    outra ponta — se o Time 4 ainda reage corretamente quando sai errado.
    """
    workspace_semeado("projeto_design_torto")
    await rodar_eval(
        evalset("ce_gate_nome_design"), agent_module=MODULO, agent_name=AGENTE
    )


@pytest.mark.eval
async def test_caminho_feliz_age_em_vez_de_narrar(
    workspace_semeado, evalset, rodar_eval
):
    """Com requisitos e design corretos, o agente lê as duas fases e persiste.

    Pega o modo de falha nº 1 da lista do `CLAUDE.md`: no ADK um `LlmAgent` encerra a
    vez ao devolver texto sem function call, e vários agentes escrevem *"Agora vou
    criar as tasks…"* como mensagem final. Trajetória vazia reprova aqui.
    """
    workspace_semeado("projeto_completo")
    await rodar_eval(
        evalset("ce_caminho_feliz"), agent_module=MODULO, agent_name=AGENTE
    )
