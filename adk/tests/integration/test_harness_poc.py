"""PoC de integração — harness → report → validador → veredito → (exit_loop).

Demonstra, ponta a ponta e com Docker stubbado, o contrato final da feature:

  1. o harness RODA sobre uma Task de exemplo (app FastAPI mínima);
  2. PERSISTE o ExecutionReport (apenas evidência) em disco;
  3. o validador LÊ o report do disco e EMITE um ValidationVerdict;
  4. o executor SÓ encerraria o loop (exit_loop) se o veredito for 'aprovado' —
     nunca pelo status técnico de execução do harness.

Não sobe container real nem chama LLM: a decisão de execução é determinística
(harness) e a política de veredito é exercida via `montar_veredito` (a mesma
regra que o Agente de Validação deve obedecer).
"""

import json
from unittest.mock import MagicMock, patch

import docker
from docker.errors import BuildError

from shared.tools.harness_execucao import executar_harness_validacao
from src.agents.implementation_validator.agent import montar_veredito
from src.agents.implementation_validator.schemas import (
    CriterionStatus,
    CriterionVerdict,
    VerdictStatus,
)

_TASK_ID = "TASK-POC-001"


# ---------------------------------------------------------------------------
# Regra de encerramento do executor (a única fonte de verdade é o veredito)
# ---------------------------------------------------------------------------

def _executor_encerraria(verdict) -> bool:
    """O executor só chama exit_loop se o veredito for 'aprovado'."""
    return verdict.status == VerdictStatus.APROVADO


# ---------------------------------------------------------------------------
# Stubs de Docker / HTTP
# ---------------------------------------------------------------------------

def _mock_response():
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = {"paths": {"/": {"get": {}}}}
    r.text = "OK"
    return r


def _mock_docker(build_raises=None):
    client = MagicMock()
    if build_raises is not None:
        client.images.build.side_effect = build_raises
    else:
        client.images.build.return_value = (
            MagicMock(),
            [{"stream": "Successfully built abc123"}],
        )
    container = MagicMock()
    container.status = "running"
    container.attrs = {"State": {"ExitCode": 0}}
    container.logs.return_value = b"2026-07-22T10:00:00 INFO [app] Uvicorn running"
    client.containers.run.return_value = container
    client.containers.get.side_effect = docker.errors.NotFound("sem container")
    return client


# ---------------------------------------------------------------------------
# Task de exemplo + app FastAPI mínima
# ---------------------------------------------------------------------------

def _preparar_workspace(tmp_path, criteria):
    coder = tmp_path / "coder" / "src"
    execution = tmp_path / "coder" / "execution"
    tasks = tmp_path / "coder" / "tasks"
    for d in (coder, execution, tasks):
        d.mkdir(parents=True, exist_ok=True)

    (coder / "main.py").write_text(
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n\n"
        "@app.get('/')\n"
        "def home():\n"
        "    return {'ok': True}\n",
        encoding="utf-8",
    )
    (coder / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")

    (tasks / f"{_TASK_ID}.json").write_text(
        json.dumps(
            {
                "id": _TASK_ID,
                "description": "Expor uma rota raiz que responde 200.",
                "acceptance_criteria": criteria,
                "contract": {},
            }
        ),
        encoding="utf-8",
    )
    return coder, execution, tasks


def _rodar_harness(coder, execution, tasks, client):
    with (
        patch("docker.from_env", return_value=client),
        patch("requests.get", return_value=_mock_response()),
        patch("shared.tools.harness_execucao.time.sleep"),
    ):
        return executar_harness_validacao(
            _TASK_ID,
            1,
            coder_base_dir=coder,
            execution_base_dir=execution,
            tasks_base_dir=tasks,
        )


# ===========================================================================
# PoC 1 — execução com sucesso → veredito aprovado → executor encerraria
# ===========================================================================

def test_poc_fluxo_aprovado_encerra(tmp_path):
    criteria = ["A rota GET / deve responder 200"]
    coder, execution, tasks = _preparar_workspace(tmp_path, criteria)

    # (1) harness RODA
    report = _rodar_harness(coder, execution, tasks, _mock_docker())
    assert report["overall_status"] == "sucesso"

    # (2) report PERSISTIDO em disco
    report_file = execution / f"{_TASK_ID}.report.json"
    assert report_file.is_file()

    # (3) o validador LÊ o report do disco e EMITE o veredito.
    #     Camada 2: a evidência mostra HTTP 200 → critério 'atendido'.
    disk_report = json.loads(report_file.read_text(encoding="utf-8"))
    criteria_verdicts = [
        CriterionVerdict(
            criterion=c,
            status=CriterionStatus.ATENDIDO,
            reasoning="Evidência do harness confirma HTTP 200 na rota.",
        )
        for c in disk_report["acceptance_criteria"]
    ]
    veredito = montar_veredito(disk_report, criteria_verdicts)
    assert veredito.status == VerdictStatus.APROVADO

    # (4) o executor SÓ encerraria porque o veredito é 'aprovado'
    assert _executor_encerraria(veredito) is True


# ===========================================================================
# PoC 2 — execução falha → veredito reprovado (Camada 1) → NÃO encerra
# ===========================================================================

def test_poc_fluxo_execucao_falha_nao_encerra(tmp_path):
    criteria = ["A rota GET / deve responder 200"]
    coder, execution, tasks = _preparar_workspace(tmp_path, criteria)

    # (1) harness RODA, mas o build falha → overall_status técnico = 'falha'
    client = _mock_docker(build_raises=BuildError("erro de build simulado", build_log=[]))
    report = _rodar_harness(coder, execution, tasks, client)
    assert report["overall_status"] == "falha"

    # (2) report PERSISTIDO mesmo em falha
    report_file = execution / f"{_TASK_ID}.report.json"
    assert report_file.is_file()

    # (3) o validador LÊ o report; a Camada 1 (determinística) REPROVA de imediato
    disk_report = json.loads(report_file.read_text(encoding="utf-8"))
    veredito = montar_veredito(disk_report)
    assert veredito.status == VerdictStatus.REPROVADO
    assert veredito.blocking_reason  # motivo do bloqueio preenchido
    # Todos os critérios ficam inconclusivos (execução não permitiu comprovar)
    assert all(cv.status == CriterionStatus.INCONCLUSIVO for cv in veredito.criteria_verdicts)

    # (4) o executor NÃO encerraria — o veredito não é 'aprovado'
    assert _executor_encerraria(veredito) is False


# ===========================================================================
# PoC 3 — o status técnico de execução, sozinho, NUNCA encerra
# ===========================================================================

def test_poc_status_execucao_sozinho_nao_encerra(tmp_path):
    """Mesmo com overall_status='sucesso', se um critério não é atendido, reprova."""
    criteria = ["A rota GET / responde 200", "O relatório de auditoria é gerado"]
    coder, execution, tasks = _preparar_workspace(tmp_path, criteria)

    report = _rodar_harness(coder, execution, tasks, _mock_docker())
    assert report["overall_status"] == "sucesso"  # execução tecnicamente OK

    report_file = execution / f"{_TASK_ID}.report.json"
    disk_report = json.loads(report_file.read_text(encoding="utf-8"))
    # A Camada 2 julga um critério como nao_atendido (evidência não sustenta).
    criteria_verdicts = [
        CriterionVerdict(criterion=criteria[0], status=CriterionStatus.ATENDIDO, reasoning="HTTP 200"),
        CriterionVerdict(
            criterion=criteria[1],
            status=CriterionStatus.NAO_ATENDIDO,
            reasoning="Nenhuma evidência de relatório de auditoria nos logs.",
        ),
    ]
    veredito = montar_veredito(disk_report, criteria_verdicts)

    # Execução bem-sucedida NÃO basta: o veredito é 'reprovado' → não encerra.
    assert veredito.status == VerdictStatus.REPROVADO
    assert _executor_encerraria(veredito) is False
