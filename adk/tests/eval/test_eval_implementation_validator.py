"""Avaliação do `implementation_validator` — o agente de menor acoplamento do Time 4.

Uma tool, sem workspace binding, e a política de veredito codificada em Python
(`montar_veredito`), o que torna a resposta final estável o bastante para servir de
âncora junto da trajetória.
"""

import pytest

MODULO = "src.agents.implementation_validator"


@pytest.mark.eval
async def test_aprova_report_verde_com_state_semeado(
    workspace_semeado, evalset, rodar_eval
):
    """Caminho feliz: trajetória, resposta e contrato de tools, juntos.

    O `session_input.state` traz `task_id` e `report_path` — sem eles o guard de
    segurança do validador rejeita o caminho e o agente cai no fail-safe.

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
# Camada de juiz — fora do gate padrão
# ---------------------------------------------------------------------------


@pytest.mark.eval
@pytest.mark.eval_juiz
async def test_juiz_llm_aprova_o_veredito_correto(
    workspace_semeado, evalset, rodar_eval
):
    """`final_response_match_v2` sobre o mesmo caso do caminho feliz.

    Fica fora do gate padrão por causa do custo medido: **+9 chamadas e +92%
    de tokens para um único caso**, porque o juiz sampleia `num_samples=5` vezes por
    invocação e agrega por voto de maioria.

    O juiz precisa ser apontado explicitamente no `test_config.json`: o default de
    `JudgeModelOptions` é `gemini-2.5-flash` (`eval_metrics.py:79`), que falharia aqui
    por falta de credencial Google. O config traz o placeholder `{{JUDGE_MODEL}}`, que
    a fixture `evalset` resolve por `AI4ES_EVAL_JUDGE_MODEL` ou, na falta, pelo
    `ADK_LLM_MODEL` do `.env` — o mesmo modelo do agente, condição de auto-preferência
    (Zheng et al.) que fica declarada como limite, não escondida. Como o juiz resolve o
    modelo pelo `LLMRegistry`, passa pelo mesmo registro de `app/main.py` que anula as
    subclasses de `shared/llm.py` — roda como produção roda, sem o `X-Initiator: user`.
    """
    workspace_semeado("validator_verde")
    await rodar_eval(evalset("juiz_validator_aprovado"), agent_module=MODULO)
