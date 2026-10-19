"""Testes da saída estruturada do reviewer (ReviewOutput + decisão em código)."""

import json
from types import SimpleNamespace

import pytest

from src.agents.workflow_coding_review.reviewer import structured_output as so

_SUMMARY_OK = {
    "input_valid": True,
    "input_errors": [],
    "expected_task_ids": ["TASK-001"],
    "processed_task_ids": ["TASK-001"],
    "approved_task_ids": ["TASK-001"],
    "accepted_task_ids": [],
    "task_results": {"TASK-001": {"status": "aprovado"}},
    "cobertura_completa": True,
    "qualidade_completa": True,
}


def _resposta(status_md: str, payload: dict | str) -> str:
    bloco = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return f"## Status: {status_md}\n\n## Issues\n- x\n\n## Resumo\nok\n\n```json\n{bloco}\n```\n"


def _issue(severity: str, layer: str = "corretude") -> dict:
    return {"severity": severity, "description": "d", "file": "solution.py", "layer": layer}


@pytest.fixture
def contexto(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))

    def _ctx(texto: str, summary: dict | None = _SUMMARY_OK):
        state = {"review_analysis": texto}
        if summary is not None:
            state["task_iteration_summary"] = summary
        return SimpleNamespace(state=state)

    return _ctx


def _json_gravado():
    from pathlib import Path

    caminho = Path(so._review_ws()) / so.JSON_FILENAME
    return json.loads(caminho.read_text(encoding="utf-8")) if caminho.is_file() else None


# ---------------------------------------------------------------------------
# extrair_review_output
# ---------------------------------------------------------------------------


def test_extrai_e_normaliza():
    texto = _resposta("BLOQUEADO", {"status": "bloqueado", "issues": [_issue("Crítico", " Corretude ")]})
    saida = so.extrair_review_output(texto)
    assert saida.status == "BLOQUEADO"
    assert (saida.issues[0].severity, saida.issues[0].layer) == ("critical", "corretude")
    assert saida.report_path == so.REPORT_FILENAME


def test_usa_o_ultimo_bloco_json():
    texto = "```json\n{\"status\": \"APROVADO\", \"issues\": []}\n```\n" + _resposta(
        "BLOQUEADO", {"status": "BLOQUEADO", "issues": [_issue("critical")]}
    )
    assert so.extrair_review_output(texto).status == "BLOQUEADO"


@pytest.mark.parametrize(
    "bloco",
    ["{status: APROVADO}", "[1, 2]", '{"issues": []}', '{"status": "APROVADO", "issues": [{"severity": "info"}]}'],
)
def test_json_invalido_devolve_none(bloco):
    assert so.extrair_review_output(_resposta("APROVADO", bloco)) is None


def test_sem_bloco_json_devolve_none():
    assert so.extrair_review_output("## Status: APROVADO\n\nsem json") is None


# ---------------------------------------------------------------------------
# decidir_status
# ---------------------------------------------------------------------------


def test_critical_bloqueia_mesmo_se_o_llm_aprovou():
    saida = so.extrair_review_output(_resposta("APROVADO", {"status": "APROVADO", "issues": [_issue("critical")]}))
    assert so.decidir_status(saida, cobertura_ok=True) == "BLOQUEADO"


def test_so_warnings_aprova_mesmo_se_o_llm_bloqueou():
    saida = so.extrair_review_output(_resposta("BLOQUEADO", {"status": "BLOQUEADO", "issues": [_issue("warning")]}))
    assert so.decidir_status(saida, cobertura_ok=True) == "APROVADO"


def test_gate_de_cobertura_vence():
    saida = so.extrair_review_output(_resposta("APROVADO", {"status": "APROVADO", "issues": []}))
    assert so.decidir_status(saida, cobertura_ok=False) == "BLOQUEADO"


# ---------------------------------------------------------------------------
# registrar_saida_estruturada
# ---------------------------------------------------------------------------


def test_consistente_grava_json_e_nao_altera_o_markdown(contexto):
    texto = _resposta("BLOQUEADO", {"status": "BLOQUEADO", "issues": [_issue("critical")]})
    ctx = contexto(texto)

    assert so.registrar_saida_estruturada(ctx) is None
    assert ctx.state["review_analysis"] == texto
    gravado = _json_gravado()
    assert gravado["status"] == "BLOQUEADO" and gravado["status_ajustado"] is False


def test_contradicao_corrige_o_markdown(contexto):
    texto = _resposta("APROVADO", {"status": "APROVADO", "issues": [_issue("critical")]})
    ctx = contexto(texto)

    conteudo = so.registrar_saida_estruturada(ctx)

    assert conteudo is not None
    assert ctx.state["review_analysis"].startswith("## Status: BLOQUEADO")
    assert "Status: APROVADO" not in ctx.state["review_analysis"]
    assert _json_gravado()["status_llm"] == "APROVADO"
    assert _json_gravado()["status_ajustado"] is True


def test_sem_summary_o_gate_bloqueia(contexto):
    ctx = contexto(_resposta("BLOQUEADO", {"status": "APROVADO", "issues": []}), summary=None)
    so.registrar_saida_estruturada(ctx)
    assert _json_gravado()["status"] == "BLOQUEADO"


def test_sem_json_nao_grava_nada(contexto):
    ctx = contexto("## Status: APROVADO\n\nsem json")
    assert so.registrar_saida_estruturada(ctx) is None
    assert _json_gravado() is None
