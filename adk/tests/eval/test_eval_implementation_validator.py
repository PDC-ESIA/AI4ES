"""Avaliação do `implementation_validator` — o agente de menor acoplamento do Time 4.

Uma tool, sem workspace binding, e a política de veredito codificada em Python
(`montar_veredito`), o que torna a resposta final estável o bastante para servir de
âncora junto da trajetória.

O par `armadilha_*` é o coração deste arquivo: transforma o achado principal do spike
de 01/09 em regressão executável.
"""

import pytest

MODULO = "src.agents.implementation_validator"


@pytest.mark.eval
async def test_aprova_report_verde_com_state_semeado(
    workspace_semeado, evalset, rodar_eval
):
    """Caminho feliz: trajetória, resposta e contrato de tools, juntos.

    O `session_input.state` traz `task_id` e `report_path` — sem eles o guard de
    segurança do validador rejeita o caminho. Ver `test_armadilha_*`.

    A fixture segue o contrato do `ExecutionReport` desde o #406 (`criterion_id`,
    `automatable`, `outcome`, `linked_tests`). Com `outcome: nao_avaliado` em todo
    critério, `montar_veredito` força cada um a `inconclusivo` com texto fixo e o
    status sai só da execução — a resposta esperada é 100% determinística.

    Histórico: em 16/09, rodado como estava (fixture e resposta de 07/09) sobre a
    `develop` já com o #406, este caso reprovou em `response_match_score` (0.609 <
    0.7) com a trajetória em 1.0 — a mudança de política do validador foi pega
    aqui, e em nenhum teste unitário.
    """
    workspace_semeado("validator_verde")
    await rodar_eval(evalset("validator_aprovado"), agent_module=MODULO)


@pytest.mark.eval
async def test_reprova_quando_a_execucao_falhou(workspace_semeado, evalset, rodar_eval):
    """`overall_status: falha` reprova de imediato, com todos os critérios inconclusivos.

    A política é de `montar_veredito`, não do texto do LLM: mesmo que o modelo julgue
    os critérios como atendidos, a execução malsucedida sobrepõe. (Até o #406 isto se
    chamava "Camada 1"; hoje o veredito é só sobre a execução.)
    """
    workspace_semeado("validator_falha")
    await rodar_eval(evalset("validator_reprovado_execucao"), agent_module=MODULO)


# ---------------------------------------------------------------------------
# A armadilha do spike (§4 de notas/spike-adk-eval.md), como regressão
# ---------------------------------------------------------------------------
# Mesmo eval case, sem `session_input.state`. O validador cai no fail-safe e emite
# `reprovado` por falta de evidência — mas chamou `tool_ler_arquivo` com o caminho
# certo, então a trajetória é idêntica à do caminho feliz.
#
# Os dois testes abaixo formam uma afirmação só: **métrica de trajetória sozinha não
# é gate**. Se algum dia o primeiro falhar ou o segundo passar, a premissa mudou e o
# PLANO_POC/relatório precisam ser revistos — que é justamente o que se quer de um
# teste de regressão sobre um achado.


@pytest.mark.eval
async def test_armadilha_trajetoria_verde_com_agente_em_failsafe(
    workspace_semeado, evalset, rodar_eval
):
    """A trajetória PASSA com o agente rodando degradado. Este é o defeito."""
    workspace_semeado("validator_verde")
    await rodar_eval(evalset("armadilha_so_trajetoria"), agent_module=MODULO)


@pytest.mark.eval
async def test_armadilha_a_ancora_de_resposta_pega_o_que_a_trajetoria_nao_pega(
    workspace_semeado, evalset, rodar_eval
):
    """O mesmo caso REPROVA quando se ancora também no resultado."""
    workspace_semeado("validator_verde")
    with pytest.raises(AssertionError) as excecao:
        await rodar_eval(evalset("armadilha_com_resposta"), agent_module=MODULO)

    assert "response_match_score" in str(excecao.value), (
        "Esperava a reprovação vir de response_match_score. Se a falha veio de "
        "tool_trajectory_avg_score, a armadilha deixou de existir — reveja o "
        "PLANO_POC §6.1 antes de mexer neste teste."
    )


# ---------------------------------------------------------------------------
# Camada de juiz — fora do gate padrão
# ---------------------------------------------------------------------------


@pytest.mark.eval
@pytest.mark.eval_juiz
async def test_juiz_llm_aprova_o_veredito_correto(
    workspace_semeado, evalset, rodar_eval
):
    """`final_response_match_v2` sobre o mesmo caso do caminho feliz.

    Fica fora do gate padrão por causa do custo medido no spike: **+9 chamadas e +92%
    de tokens para um único caso**, porque o juiz sampleia `num_samples=5` vezes por
    invocação e agrega por voto de maioria.

    O juiz precisa ser apontado explicitamente no `test_config.json`: o default de
    `JudgeModelOptions` é `gemini-2.5-flash` (`eval_metrics.py:79`), que falharia aqui
    por falta de credencial Google. O config traz o placeholder `{{JUDGE_MODEL}}`, que
    a fixture `evalset` resolve por `AI4ES_EVAL_JUDGE_MODEL` ou, na falta, pelo
    `ADK_LLM_MODEL` do `.env` — o mesmo modelo do agente, condição de auto-preferência
    (Zheng et al.) que fica declarada como limite, não escondida. Como o juiz resolve o
    modelo pelo `LLMRegistry`, este é o caminho que o **defeito 16** sequestra — roda
    como produção roda, sem o `X-Initiator: user`.
    """
    workspace_semeado("validator_verde")
    await rodar_eval(evalset("juiz_validator_aprovado"), agent_module=MODULO)
