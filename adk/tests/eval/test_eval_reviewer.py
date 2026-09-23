"""Avaliação do `cr_review_analyzer` — o agente com o binding mais rígido do Time 4.

`review_tools.py:35-37` resolve `_CODER_WS`/`_REVIEW_WS` em **tempo de import**, então
este agente só é avaliável porque o `conftest` define `WORKSPACE_OUTPUT_DIR` antes de
qualquer import de agente. A guarda de coerência do conftest existe por causa disto.
"""

import pytest

MODULO = "src.agents.workflow_coding_review.agent"
AGENTE = "cr_review_analyzer"


@pytest.mark.eval
async def test_gate_de_cobertura_sobrepoe_o_veredito_do_llm(
    workspace_semeado, evalset, rodar_eval
):
    """Sem `task_iteration_summary` no state, o reviewer não pode aprovar.

    Duas coisas numa avaliação só:

    1. **Leu o código.** `ai4es_tool_sequence_in_order` exige ao menos um
       `tool_ler_arquivo` — o reviewer não pode opinar sobre arquivos que não abriu.
    2. **O gate sobrepôs.** `_persist_review` roda depois do LLM, em Python puro, e
       `aplicar_gate_de_cobertura` reescreve a linha de status para
       `## Status: BLOQUEADO` e insere o bloco `<!-- task-coverage-gate -->` — não
       importa o que o modelo tenha escrito.

    O corpo da análise continua sendo prosa do LLM, por isso a âncora é
    `ai4es_resposta_contem` (marcadores literais) e não `response_match_score`.
    """
    workspace_semeado("projeto_revisavel")
    await rodar_eval(
        evalset("reviewer_gate_cobertura"), agent_module=MODULO, agent_name=AGENTE
    )
