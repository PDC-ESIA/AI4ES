"""Integração da cobertura de critérios: task → harness → nota de aceite.

Exercita a cadeia REAL, sem LLM e sem sandbox de verdade: uma task com critérios
identificados e classificados vai ao harness, o manifesto declara o vínculo
teste ↔ critério, a suíte emite saída verbosa, e o resultado por critério
alimenta a nota de aceite e a nota unificada.

O que estes testes protegem é a costura entre as fases — cada peça tem teste
unitário próprio, mas é aqui que se verifica que o id sobrevive da autoria da
task até a nota final, que é o ponto inteiro do desenho.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shared.execution.sandbox import CommandResult
from shared.tools.coding_tools.harness_execucao import executar_harness_validacao
from src.agents.workflow_coding_review.executor.acceptance_score import (
    calcular_nota_aceite,
    nota_unificada,
)
from src.agents.workflow_coding_review.executor.progress_score import calcular_nota
from src.agents.workflow_coding_review.manifest import resumo_de_aceite


class _Sandbox:
    """Sandbox mínimo: devolve a saída de teste configurada e nada mais."""

    def __init__(self, saida: str, exit_code: int = 0):
        self._saida = saida
        self._exit_code = exit_code
        self.root = Path("/tmp/fake")

    def setup(self, source_dir):  # noqa: D102 - interface do Sandbox
        pass

    def exec(self, command, *, timeout, env=None):  # noqa: D102
        if "pytest" in command:
            return CommandResult(self._exit_code, self._saida, "", False)
        return CommandResult(0, "", "", False)

    def start_service(self, command, *, env=None):  # noqa: D102
        pass

    def logs(self) -> str:  # noqa: D102
        return "INFO app no ar"

    def cleanup(self):  # noqa: D102
        pass


CRITERIOS = [
    {
        "id": "CA-01",
        "description": "Retornar 401 quando as credenciais forem inválidas",
        "automatable": True,
    },
    {
        "id": "CA-02",
        "description": "Persistir o ensaio ao criar",
        "automatable": True,
    },
    {
        "id": "CA-03",
        "description": "Consigo ver a página final do álbum",
        "automatable": False,
    },
]


@pytest.fixture
def workspace(tmp_path):
    coder = tmp_path / "coder" / "src"
    execution = tmp_path / "coder" / "execution"
    tasks = tmp_path / "coder" / "tasks"
    for d in (coder, execution, tasks):
        d.mkdir(parents=True, exist_ok=True)
    (tasks / "TASK-001.json").write_text(
        json.dumps(
            {
                "id": "TASK-001",
                "description": "Cadastro de ensaios",
                "acceptance_criteria": CRITERIOS,
                "contract": {},
            }
        ),
        encoding="utf-8",
    )
    return coder, execution, tasks


def _manifesto(coder, acceptance_tests):
    (coder / "run.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "surface": "service",
                "build": ["pip install -r requirements.txt"],
                "run": "uvicorn main:app --port 8000",
                "test": ["pytest -v"],
                "port": 8000,
                "healthcheck": "/",
                "sandbox": "direct",
                "acceptance_tests": acceptance_tests,
            }
        ),
        encoding="utf-8",
    )


def _executar(workspace, saida, exit_code=0):
    coder, execution, tasks = workspace
    resposta = MagicMock(status_code=200, text="OK")
    resposta.json.return_value = {"paths": {"/": {"get": {}}}}
    with patch(
        "shared.tools.coding_tools.harness_execucao.create_sandbox",
        return_value=_Sandbox(saida, exit_code),
    ), patch("requests.get", return_value=resposta), patch(
        "shared.tools.coding_tools.harness_execucao.time.sleep"
    ):
        return executar_harness_validacao(
            "TASK-001",
            1,
            coder_base_dir=coder,
            execution_base_dir=execution,
            tasks_base_dir=tasks,
        )


def test_cobertura_parcial_percorre_a_cadeia_inteira(workspace):
    """Um critério coberto, um sem teste, um não automatizável.

    A nota de aceite enxerga só o coberto; os outros dois vão para a cobertura.
    E a nota final NÃO é penalizada pelo que não deu para verificar.
    """
    coder, _, _ = workspace
    _manifesto(coder, {"CA-01": ["tests/test_auth.py::test_401"]})

    report = _executar(
        workspace,
        "tests/test_auth.py::test_401 PASSED  [100%]\n1 passed in 0.01s\n",
    )

    assert report["overall_status"] == "sucesso"

    por_id = {e["criterion_id"]: e["outcome"] for e in report["criteria_evidence"]}
    assert por_id == {
        "CA-01": "atendido",
        "CA-02": "sem_teste_mapeado",
        "CA-03": "nao_automatizavel",
    }

    aceite = calcular_nota_aceite(report)
    assert aceite.nota == 1.0
    assert aceite.cobertura == pytest.approx(1 / 3)
    # Só CA-02 é cobrável: CA-03 está fora do alcance de teste de código.
    assert aceite.criterios_enderecaveis == ["CA-02"]

    tecnica = calcular_nota(report).total
    assert nota_unificada(tecnica, aceite.nota) == pytest.approx(tecnica)


def test_criterio_com_teste_vermelho_derruba_a_nota_de_aceite(workspace):
    coder, _, _ = workspace
    _manifesto(
        coder,
        {
            "CA-01": ["tests/test_auth.py::test_401"],
            "CA-02": ["tests/test_ensaios.py::test_persiste"],
        },
    )

    report = _executar(
        workspace,
        "tests/test_auth.py::test_401 PASSED\n"
        "tests/test_ensaios.py::test_persiste FAILED\n"
        "=========================== short test summary info ===========================\n"
        "FAILED tests/test_ensaios.py::test_persiste - AssertionError\n"
        "1 passed, 1 failed\n",
        exit_code=1,
    )

    por_id = {e["criterion_id"]: e["outcome"] for e in report["criteria_evidence"]}
    assert por_id["CA-01"] == "atendido"
    assert por_id["CA-02"] == "nao_atendido"

    aceite = calcular_nota_aceite(report)
    assert aceite.nota == 0.5
    assert aceite.cobertura == pytest.approx(2 / 3)
    # Nada a cobrar do coder: os dois critérios automatizáveis têm teste.
    assert aceite.criterios_enderecaveis == []

    # Suíte vermelha é falha TÉCNICA — o caminho de sempre continua valendo.
    assert report["overall_status"] == "falha"


def test_grafia_divergente_do_id_nao_quebra_o_vinculo(workspace):
    """O coder escreve o mapa lendo a task; a canonização absorve a diferença."""
    coder, _, _ = workspace
    _manifesto(coder, {"ca-1": ["tests/test_auth.py::test_401"]})

    report = _executar(
        workspace, "tests/test_auth.py::test_401 PASSED\n1 passed\n"
    )

    por_id = {e["criterion_id"]: e["outcome"] for e in report["criteria_evidence"]}
    assert por_id["CA-01"] == "atendido"


def test_suite_sem_saida_verbosa_nao_comprova_nada(workspace):
    """Sem `-v` o resultado não tem nome, e nada é dado por comprovado."""
    coder, _, _ = workspace
    _manifesto(coder, {"CA-01": ["tests/test_auth.py::test_401"]})

    report = _executar(workspace, "..\n2 passed in 0.02s\n")

    por_id = {e["criterion_id"]: e["outcome"] for e in report["criteria_evidence"]}
    assert por_id["CA-01"] == "teste_nao_executado"

    aceite = calcular_nota_aceite(report)
    assert aceite.nota is None
    assert aceite.cobertura == 0.0
    # É lacuna endereçável: o coder pode corrigir o comando ou o identificador.
    assert aceite.criterios_enderecaveis == ["CA-01", "CA-02"]


def test_nota_do_manifesto_agrega_o_que_o_harness_produziu(workspace):
    """Fecha a cadeia até o artefato que segue para jusante."""
    coder, _, _ = workspace
    _manifesto(coder, {"CA-01": ["tests/test_auth.py::test_401"]})
    report = _executar(
        workspace, "tests/test_auth.py::test_401 PASSED\n1 passed\n"
    )
    aceite = calcular_nota_aceite(report)

    resumo = resumo_de_aceite(
        {
            "task_results": {
                "TASK-001": {
                    "nota_final": 0.95,
                    "nota_tecnica_final": 1.0,
                    "nota_aceite": aceite.nota,
                    "cobertura_criterios": aceite.cobertura,
                    "conceito": "A",
                    "aceite": aceite.como_dict(),
                }
            }
        }
    )

    assert resumo["criterios_total"] == 3
    assert resumo["criterios_atendidos"] == 1
    assert resumo["criterios_sem_cobertura"] == 2
    assert resumo["nota_aceite"] == 1.0
    assert resumo["cobertura_criterios"] == pytest.approx(1 / 3, abs=1e-4)
