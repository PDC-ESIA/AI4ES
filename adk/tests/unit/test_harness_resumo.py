"""Testes do resumo que o harness devolve ao LLM (`_resumir_report`).

O relatório COMPLETO continua sendo persistido em disco e é dele que o
validador e o ErrorReport se alimentam. O que a tool devolve ao executor é um
resumo: o retorno entra no contexto do LoopAgent e é reenviado a cada iteração
da task, então evidência bruta ali dentro cresce de forma multiplicativa.

Estes testes travam esse contrato — uma "melhoria" que volte a devolver o
relatório inteiro faria o consumo inflar de novo sem quebrar nada mais.
"""

import json
from unittest.mock import patch

from shared.tools.coding_tools import harness_execucao
from shared.tools.coding_tools.harness_execucao import _resumir_report


def _payload_completo():
    """ExecutionReport como o harness o produz, com evidência bruta volumosa."""
    return {
        "work_item_id": "TASK-007",
        "iteration": 3,
        "overall_status": "falha",
        "report_path": "/ws/coder/execution/TASK-007.report.json",
        "acceptance_criteria": ["Critério A", "Critério B"],
        "criteria_evidence": [
            {"criterion": "Critério A", "observed": "x" * 2000, "checkable": True},
            {"criterion": "Critério B", "observed": "y" * 2000, "checkable": False},
        ],
        "stages": [
            {"stage": "preparacao_ambiente", "status": "sucesso", "summary": "ok",
             "evidence": {"log": "L" * 5000}},
            {"stage": "testes_automatizados", "status": "falha",
             "error_code": "TESTES_FALHARAM", "summary": "0 passaram, 5 falharam",
             "evidence": {"stdout": "T" * 9000, "traceback": "B" * 9000}},
            {"stage": "inicializacao_aplicacao", "status": "pulado",
             "summary": "Abortado: build falhou", "evidence": {}},
            {"stage": "coleta_logs_execucao", "status": "erro",
             "error_code": "LOGS_INDISPONIVEIS", "summary": "sem logs",
             "evidence": {"stderr": "E" * 4000}},
        ],
        "total_duration_seconds": 12.5,
    }


def test_resumo_preserva_campos_de_orquestracao():
    """O executor precisa de report_path (para o validador) e do status técnico."""
    resumo = _resumir_report(_payload_completo())

    assert resumo["work_item_id"] == "TASK-007"
    assert resumo["iteration"] == 3
    assert resumo["overall_status"] == "falha"
    assert resumo["report_path"] == "/ws/coder/execution/TASK-007.report.json"


def test_resumo_inclui_somente_estagios_em_falha():
    """Sucesso não traz informação acionável; PULADO é cascata do que falhou antes."""
    resumo = _resumir_report(_payload_completo())

    estagios = {e["stage"] for e in resumo["stages_com_falha"]}
    assert estagios == {"testes_automatizados", "coleta_logs_execucao"}
    assert all(e["status"] in ("falha", "erro") for e in resumo["stages_com_falha"])


def test_resumo_nao_carrega_evidencia_bruta():
    """A regressão que este módulo existe para impedir: logs voltando ao prompt."""
    payload = _payload_completo()
    serializado = json.dumps(_resumir_report(payload), ensure_ascii=False)

    for ruido in ("T" * 100, "B" * 100, "E" * 100, "L" * 100, "x" * 100, "y" * 100):
        assert ruido not in serializado, "evidência bruta vazou para o resumo"
    assert "evidence" not in serializado
    # Ordens de grandeza: o payload real da run tinha ~11k chars por chamada.
    assert len(serializado) < 2000


def test_resumo_trunca_summary_longo():
    """Resumos de estágio são de uma linha hoje, mas nada garante isso no futuro."""
    payload = _payload_completo()
    payload["stages"][1]["summary"] = "S" * 5000

    resumo = _resumir_report(payload)
    summary = next(
        e["summary"] for e in resumo["stages_com_falha"]
        if e["stage"] == "testes_automatizados"
    )
    assert len(summary) <= 500


def test_resumo_tolera_payload_incompleto():
    """Chamadas diretas/testes passam payloads mínimos — não pode levantar."""
    resumo = _resumir_report({"work_item_id": "TASK-001"})

    assert resumo["work_item_id"] == "TASK-001"
    assert resumo["overall_status"] is None
    assert resumo["stages_com_falha"] == []
    assert resumo["total_criterios_com_evidencia"] == 0


def test_tool_resume_mas_execucao_direta_devolve_report_completo():
    """A fronteira: só o que vai ao LLM é enxuto.

    `executar_harness_validacao` (usada por testes, PoC e pelo caminho que
    persiste o report) segue devolvendo tudo; `executar_harness_tool`, que é a
    FunctionTool exposta ao executor, devolve o resumo.
    """
    payload = _payload_completo()

    with patch.object(
        harness_execucao, "executar_harness_validacao", return_value=payload
    ):
        resumo = harness_execucao.executar_harness_tool("TASK-007", 3)

    assert "stages" not in resumo and "criteria_evidence" not in resumo
    assert resumo["report_path"] == payload["report_path"]
    # O payload original não é mutado — quem lê o report em disco não é afetado.
    assert len(payload["stages"]) == 4
    assert payload["stages"][1]["evidence"]["stdout"].startswith("T")
