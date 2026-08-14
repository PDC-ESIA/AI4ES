"""Integração interna do QA Agent — Cenário 2: propagação de erros entre camadas.

Cobre três trilhas de erro reais dentro do QA Agent: código de teste inválido
gerado pelo LLM (sanitizer → orchestration), timeout de execução do pytest
(pytest_runner) e a trava de loop (pytest_runner → Doubt Artifact). Nenhum
teste depende de LLM real.
"""

import json
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def tmp_workspace(tmp_path: Path, monkeypatch) -> Path:
    """Workspace isolado por teste, substituindo workspace_output."""
    ws = tmp_path / "workspace_output"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / ".ai4se_workspace").write_text("marker", encoding="utf-8")
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws))

    from shared import workspace as _ws_mod

    monkeypatch.setattr(_ws_mod, "_DEFAULT_WORKSPACE", str(ws))
    return ws


# ──────────────────────────────────────────────────────────────────────────────
# sanitizer → orchestration: código inválido pós-LLM vira "falha", não exceção
# ──────────────────────────────────────────────────────────────────────────────


def test_sanitizer_invalido_vira_falha(
    tmp_workspace: Path, monkeypatch
):
    """Código sintaticamente inválido (mesmo após sanitização) não derruba o
    lote inteiro: o artefato específico fica com status 'falha' e erro legível."""
    from src.agents.qa_agent.subagents.receive_requirements import orchestration

    codigo_invalido = "def test_quebrado(:\n    assert True\n"
    monkeypatch.setattr(
        orchestration, "_gerar_pytest_via_llm", lambda **kwargs: codigo_invalido
    )

    artefato = {
        "id_artefato": "RF-INVALIDO",
        "tipo": "RF",
        "conteudo": "Requisito valido.",
        "modulo": "mod",
        "criticidade": "alta",
    }
    resultado = orchestration.receber_requisitos(json.dumps([artefato]))

    assert resultado["resumo"]["falhas"] == 1
    detalhe = resultado["detalhes"][0]
    assert detalhe["status"] == "falha"
    assert detalhe["arquivo_gerado"] is None
    assert "RF-INVALIDO" in detalhe["erro"]


# ──────────────────────────────────────────────────────────────────────────────
# pytest_runner: timeout vira estrutura de erro consistente (nunca exceção crua)
# ──────────────────────────────────────────────────────────────────────────────


def test_timeout_gera_erro_estruturado(
    tmp_workspace: Path, monkeypatch
):
    from shared.tools import pytest_runner as pr

    slug_dir = tmp_workspace / "tests" / "inputs" / "hu_timeout"
    slug_dir.mkdir(parents=True)
    arquivo = slug_dir / "test_hu_timeout.py"
    arquivo.write_text("def test_x():\n    assert True\n", encoding="utf-8")

    def _fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="pytest", timeout=30)

    monkeypatch.setattr(pr.subprocess, "run", _fake_run)

    resultado = pr.executar_pytest_tool(str(arquivo))

    assert resultado["status"] == "falha"
    assert resultado["agente_origem"] == "pytest_runner"
    assert resultado["proxima_acao_orquestrador"] == "trigger_correcao_matunag"
    assert resultado["erros"][0]["codigo"] == "ERR_TIMEOUT"
    assert resultado["testes_gerados"][0]["arquivo"] == str(arquivo)


# ──────────────────────────────────────────────────────────────────────────────
# pytest_runner: trava de loop gera Doubt Artifact após MAX_TENTATIVAS
# ──────────────────────────────────────────────────────────────────────────────


def test_loop_guard_gera_doubt(
    tmp_workspace: Path,
):
    from shared.tools import pytest_runner as pr

    slug_dir = tmp_workspace / "tests" / "inputs" / "hu_loop"
    slug_dir.mkdir(parents=True)
    arquivo = slug_dir / "test_hu_loop.py"
    arquivo.write_text("def test_sempre_falha():\n    assert False\n", encoding="utf-8")

    resultado = None
    for _ in range(pr.MAX_TENTATIVAS + 1):
        resultado = pr.executar_pytest_tool(str(arquivo))

    assert resultado["status"] == "falha"
    assert resultado["erros"][0]["codigo"] == "ERR_LOOP"

    doubt_dir = tmp_workspace / "tests" / "inputs" / "doubt_artifacts"
    doubts = list(doubt_dir.glob("Doubt_Artifact_test_hu_loop_*.md"))
    assert len(doubts) == 1
    conteudo = doubts[0].read_text(encoding="utf-8")
    assert "BLOQUEADO" in conteudo
