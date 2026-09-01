"""PoC de integração — harness → report → validador → veredito → (exit_loop).

Demonstra, ponta a ponta e com o sandbox stubbado, o contrato final da feature:

  1. o harness RODA sobre uma Task de exemplo, dirigido pelo manifesto run.json;
  2. PERSISTE o ExecutionReport (apenas evidência) em disco;
  3. o validador LÊ o report do disco e EMITE um ValidationVerdict;
  4. o executor SÓ encerraria o loop (exit_loop) se o veredito for 'aprovado'.

O veredito é sobre a EXECUÇÃO: aprova quando o harness conclui com
`overall_status == "sucesso"`. O julgamento semântico dos critérios de aceite
entra no veredito como registro e não altera o status (PoC 3).

Não sobe processo/container real nem chama LLM: o sandbox é substituído por um
`FakeSandbox` (via patch em `create_sandbox`) e o `requests.get` é mockado. A
decisão de execução é determinística (harness) e a política de veredito é
exercida via `montar_veredito` (a mesma regra que o Agente de Validação obedece).
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from shared.execution.sandbox import CommandResult
from shared.tools.coding_tools.harness_execucao import executar_harness_validacao
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
# Stubs de sandbox / HTTP
# ---------------------------------------------------------------------------

def _mock_response():
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = {"paths": {"/": {"get": {}}}}
    r.text = "OK"
    return r


class _FakeSandbox:
    """Sandbox de teste determinístico: build/testes configuráveis por substring."""

    def __init__(self, *, exec_results=None, default_exec=None, logs_text=""):
        self.exec_results = exec_results or {}
        self.default_exec = default_exec or CommandResult(
            exit_code=0, stdout="", stderr="", timed_out=False
        )
        self.logs_text = logs_text
        self._root = Path("/tmp/fake-poc-sandbox")
        self.started_service = None

    @property
    def root(self) -> Path:
        return self._root

    def setup(self, source_dir):
        pass

    def exec(self, command, *, timeout, env=None):
        for key, res in self.exec_results.items():
            if key in command:
                return res
        return self.default_exec

    def start_service(self, command, *, env=None):
        self.started_service = command

    def logs(self):
        return self.logs_text

    def cleanup(self):
        pass


def _sandbox_sucesso():
    """Build ok + suíte que passa."""
    return _FakeSandbox(
        exec_results={
            "pytest": CommandResult(
                exit_code=0, stdout="1 passed in 0.01s", stderr="", timed_out=False
            ),
        },
        logs_text="2026-07-22T10:00:00 INFO [app] serviço no ar",
    )


def _sandbox_build_falha():
    """Comando de build retorna erro → estágio 2 FALHA_BUILD."""
    return _FakeSandbox(
        exec_results={
            "pip install": CommandResult(
                exit_code=1, stdout="", stderr="ERROR: build simulado", timed_out=False
            ),
        }
    )


# ---------------------------------------------------------------------------
# Task de exemplo + manifesto run.json
# ---------------------------------------------------------------------------

def _manifest_service(com_suite=False):
    return {
        "schema_version": "1",
        "surface": "service",
        "build": ["pip install -r requirements.txt"],
        "run": "uvicorn main:app --port 8000",
        "test": ["pytest -q"] if com_suite else [],
        "port": 8000,
        "healthcheck": "/",
        "sandbox": "direct",
    }


def _preparar_workspace(tmp_path, criteria, com_suite=False):
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
    (coder / "run.json").write_text(
        json.dumps(_manifest_service(com_suite=com_suite)), encoding="utf-8"
    )
    if com_suite:
        (coder / "test_main.py").write_text(
            "def test_home():\n    assert True\n", encoding="utf-8"
        )

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


def _rodar_harness(coder, execution, tasks, sandbox):
    with (
        patch(
            "shared.tools.coding_tools.harness_execucao.create_sandbox",
            return_value=sandbox,
        ),
        patch("requests.get", return_value=_mock_response()),
        patch("shared.tools.coding_tools.harness_execucao.time.sleep"),
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
    report = _rodar_harness(coder, execution, tasks, _sandbox_sucesso())
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
    report = _rodar_harness(coder, execution, tasks, _sandbox_build_falha())
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
# PoC 3 — o julgamento semântico de critério NÃO derruba execução bem-sucedida
# ===========================================================================

def test_poc_criterio_nao_comprovado_nao_derruba_execucao_ok(tmp_path):
    """Com overall_status='sucesso', o veredito aprova mesmo com critério em aberto.

    Inversão deliberada de contrato: julgar semanticamente um critério de aceite
    exige comprovar comportamento que o harness não instrumenta, e o julgamento
    honesto do LLM sobre isso era `nao_atendido`/`inconclusivo` rodada após
    rodada. Enquanto isso reprovava, nenhuma task chegava a aprovar — o loop
    perseguia uma aprovação inalcançável até morrer por platô. O veredito passou
    a ser sobre a EXECUÇÃO; o julgamento segue registrado, sem decidir.
    """
    criteria = ["A rota GET / responde 200", "O relatório de auditoria é gerado"]
    coder, execution, tasks = _preparar_workspace(tmp_path, criteria)

    report = _rodar_harness(coder, execution, tasks, _sandbox_sucesso())
    assert report["overall_status"] == "sucesso"  # execução tecnicamente OK

    report_file = execution / f"{_TASK_ID}.report.json"
    disk_report = json.loads(report_file.read_text(encoding="utf-8"))
    criteria_verdicts = [
        CriterionVerdict(criterion=criteria[0], status=CriterionStatus.ATENDIDO, reasoning="HTTP 200"),
        CriterionVerdict(
            criterion=criteria[1],
            status=CriterionStatus.NAO_ATENDIDO,
            reasoning="Nenhuma evidência de relatório de auditoria nos logs.",
        ),
    ]
    veredito = montar_veredito(disk_report, criteria_verdicts)

    assert veredito.status == VerdictStatus.APROVADO
    assert _executor_encerraria(veredito) is True
    # O julgamento continua auditável no veredito, apenas não decide o status —
    # e, como o harness emite `nao_avaliado` para todo critério, o `atendido` e
    # o `nao_atendido` do LLM são neutralizados: evidência técnica e testes do
    # próprio coder não autorizam conclusão semântica.
    assert [v.criterion for v in veredito.criteria_verdicts] == criteria
    assert all(
        v.status == CriterionStatus.INCONCLUSIVO for v in veredito.criteria_verdicts
    )


# ===========================================================================
# PoC 4 — a suíte roda no sandbox (cobre a costura harness↔testes do manifesto)
# ===========================================================================

def test_poc_suite_executada_no_sandbox(tmp_path):
    """Com comandos de teste no manifesto, o estágio 6 executa a suíte no sandbox
    e coleta evidência estruturada — sem inferir stack nem reescrever paths.
    """
    criteria = ["A rota GET / deve responder 200"]
    coder, execution, tasks = _preparar_workspace(tmp_path, criteria, com_suite=True)

    report = _rodar_harness(coder, execution, tasks, _sandbox_sucesso())

    testes = next(s for s in report["stages"] if s["stage"] == "testes_automatizados")
    # Executou os comandos de teste do manifesto e coletou o resumo.
    assert testes["status"] == "sucesso"
    resultados = testes["evidence"]["resultados"]
    assert resultados[0]["comando"] == "pytest -q"
    assert resultados[0]["resumo"]["passaram"] == 1
    assert report["overall_status"] == "sucesso"

    # E o fluxo segue normalmente até o veredito (aprovado) → executor encerraria
    report_file = execution / f"{_TASK_ID}.report.json"
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
    assert _executor_encerraria(veredito) is True
