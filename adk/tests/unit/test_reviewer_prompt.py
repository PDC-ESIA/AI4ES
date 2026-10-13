"""Testes do prompt do reviewer do workflow coding_review.

O prompt.py já traz a instrução na forma que o agente usa. Antes, o agent.py
adaptava um texto escrito para "diff git" com .replace() de strings exatas, e
uma edição mínima no prompt.py desfazia a adaptação em silêncio. Estes testes
guardam o que aquelas substituições garantiam.
"""

import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer
from src.agents.workflow_coding_review.reviewer import prompt


def test_agente_usa_o_prompt_sem_adaptacoes_em_runtime():
    assert cr_reviewer._ANALYZER_BASE == prompt.instruction


def test_prompt_le_o_workspace_e_nao_um_diff_git():
    assert "ARQUIVOS A REVISAR" in prompt.instruction
    assert " no diff" not in prompt.instruction
    assert "diff acumulado" not in prompt.instruction


def test_prompt_pede_markdown_com_status_que_o_manifesto_le():
    # O manifesto decide pass/fail procurando "Status: APROVADO|BLOQUEADO".
    assert '"## Status: APROVADO" ou "## Status: BLOQUEADO"' in prompt.instruction
    assert "## Issues" in prompt.instruction


def test_persistencia_fica_com_o_callback():
    assert "persistência em disco" in prompt.instruction
    assert "tool_salvar_relatorio" not in prompt.instruction


def test_template_injeta_os_blocos_de_runtime():
    for marcador in ("__TASK_OUTCOMES__", "__STATIC_FINDINGS__", "__CODER_WS__", "__FILES__"):
        assert marcador in cr_reviewer._ANALYZER_INSTRUCTION_TEMPLATE
