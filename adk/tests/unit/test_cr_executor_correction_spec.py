"""Regressões do feedback determinístico que substituiu o antigo CorrectionSpec."""

import json

from src.agents.executor.error_report import montar_error_report
from src.agents.executor.estagnacao import MARCADOR_ESTAGNACAO, hash_codigo, resumo_bloqueado


class _Context:
    def __init__(self, state):
        self.state = state


def _validation(status="reprovado"):
    return {
        "work_item_id": "TASK-001",
        "status": status,
        "blocking_reason": "Testes falharam.",
        "criteria_verdicts": [
            {
                "criterion": "GET / deve responder 200",
                "status": "nao_atendido",
                "reasoning": "HTTP 500 observado.",
                "evidence_ref": "testes_automatizados",
            },
            {
                "criterion": "README presente",
                "status": "atendido",
                "reasoning": "Arquivo encontrado.",
                "evidence_ref": None,
            },
        ],
    }


def test_error_report_sem_report_em_disco_ainda_preserva_veredito():
    ctx = _Context({"validation": _validation(), "task_id": "TASK-001"})

    content = montar_error_report(ctx)

    assert content is not None
    report = json.loads(content.parts[0].text)
    assert report["work_item_id"] == "TASK-001"
    assert report["verdict_status"] == "reprovado"
    assert len(report["failed_criteria"]) == 1
    assert report["failed_criteria"][0]["criterion"] == "GET / deve responder 200"
    assert report["failed_stages"] == []
    assert ctx.state["error_report"] == report


def test_error_report_nao_emitido_sem_reprovacao():
    assert montar_error_report(_Context({})) is None
    assert montar_error_report(_Context({"validation": _validation("aprovado")})) is None


def test_error_report_nao_sobrescreve_estagnacao():
    ctx = _Context(
        {
            "validation": _validation(),
            "execution_result": resumo_bloqueado("Testes falharam.", 3),
        }
    )
    assert montar_error_report(ctx) is None


def test_hash_codigo_estavel_e_sensivel_ao_conteudo(tmp_path):
    (tmp_path / "main.py").write_text("print('a')\n", encoding="utf-8")
    primeiro = hash_codigo(tmp_path)
    assert primeiro == hash_codigo(tmp_path)

    (tmp_path / "main.py").write_text("print('b')\n", encoding="utf-8")
    assert hash_codigo(tmp_path) != primeiro


def test_hash_codigo_respeita_dockerignore_e_dotfiles(tmp_path):
    (tmp_path / ".dockerignore").write_text("generated/\n*.log\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("ok\n", encoding="utf-8")
    (tmp_path / "generated").mkdir()
    (tmp_path / "generated" / "asset.js").write_text("a\n", encoding="utf-8")
    (tmp_path / "run.log").write_text("a\n", encoding="utf-8")
    inicial = hash_codigo(tmp_path)

    (tmp_path / "generated" / "asset.js").write_text("b\n", encoding="utf-8")
    (tmp_path / "run.log").write_text("b\n", encoding="utf-8")
    (tmp_path / ".cache").write_text("b\n", encoding="utf-8")
    assert hash_codigo(tmp_path) == inicial


def test_resumo_bloqueado_mantem_semantica_de_reprovacao():
    resumo = resumo_bloqueado("Mesmo erro.", 3)
    assert resumo.startswith(MARCADOR_ESTAGNACAO)
    assert "Mesmo erro." in resumo
    assert "3 iterações" in resumo
    assert "NÃO é aprovação" in resumo
