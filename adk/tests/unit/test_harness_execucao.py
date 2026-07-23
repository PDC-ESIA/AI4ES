"""Tests para o harness de execução (shared/tools/harness_execucao.py).

Docker, requests e pytest são MOCKADOS — nenhum container real é subido e
nenhuma suíte real é executada. Cobre:
- caminho feliz: 9 estágios concluem, overall_status=sucesso, report bem-formado;
- abort crítico: falha na implantação (estágio 2) aborta 4–7, overall=falha;
- estágio de testes PULADO quando não há suíte;
- serialização JSON + markdown com sobrescrita atômica;
- estágio 7 produz um CriterionEvidence por critério e NUNCA um veredito.
"""

import json
from unittest.mock import MagicMock, patch

import docker
from docker.errors import BuildError

from shared.tools.harness_execucao import executar_harness_validacao
from src.agents.executor.schemas import ExecutionReport

_STAGE_ORDER = [
    "preparacao_ambiente",
    "implantacao_artefato",
    "coleta_logs_implantacao",
    "inicializacao_aplicacao",
    "coleta_logs_execucao",
    "testes_automatizados",
    "validacoes_work_item",
    "consolidacao_evidencias",
    "geracao_relatorio",
]


# ---------------------------------------------------------------------------
# Helpers de mock
# ---------------------------------------------------------------------------

def _mock_response(status_code=200, json_data=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data if json_data is not None else {"paths": {"/": {"get": {}}}}
    r.text = "OK"
    return r


def _mock_docker(container_status="running", build_raises=None):
    """Cria um client Docker mockado (build/run/cleanup)."""
    client = MagicMock()
    if build_raises is not None:
        client.images.build.side_effect = build_raises
    else:
        image = MagicMock()
        log_gen = [
            {"stream": "Step 1/5 : FROM python:3.12-slim"},
            {"stream": "Successfully built abc123"},
        ]
        client.images.build.return_value = (image, log_gen)

    container = MagicMock()
    container.status = container_status
    container.attrs = {"State": {"ExitCode": 0}}
    container.logs.return_value = (
        b"2026-07-21T10:00:00 INFO [app] Uvicorn running on http://0.0.0.0:8000"
    )
    client.containers.run.return_value = container
    # _cleanup_container: sem container antigo → NotFound (fluxo limpo)
    client.containers.get.side_effect = docker.errors.NotFound("sem container")
    return client, container


def _write_task(tasks_dir, task_id="TASK-001", criteria=None):
    if criteria is None:
        criteria = ["A rota GET / deve responder 200", "O sistema deve ser intuitivo"]
    (tasks_dir / f"{task_id}.json").write_text(
        json.dumps(
            {
                "id": task_id,
                "description": "Descrição da task de teste",
                "acceptance_criteria": criteria,
                "contract": {},
            }
        ),
        encoding="utf-8",
    )


def _write_src(coder_dir, with_suite=False):
    (coder_dir / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8"
    )
    (coder_dir / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
    if with_suite:
        (coder_dir / "test_app.py").write_text(
            "def test_ok():\n    assert True\n", encoding="utf-8"
        )


def _dirs(tmp_path):
    coder = tmp_path / "coder" / "src"
    execution = tmp_path / "coder" / "execution"
    tasks = tmp_path / "coder" / "tasks"
    for d in (coder, execution, tasks):
        d.mkdir(parents=True, exist_ok=True)
    return coder, execution, tasks


def _run(task_id, coder, execution, tasks, client, pytest_result=None):
    """Executa o harness com Docker/requests/pytest/sleep mockados."""
    patches = [
        patch("docker.from_env", return_value=client),
        patch("requests.get", return_value=_mock_response()),
        patch("shared.tools.harness_execucao.time.sleep"),
    ]
    if pytest_result is not None:
        patches.append(
            patch(
                "shared.tools.harness_execucao.executar_pytest_tool",
                return_value=pytest_result,
            )
        )
    with patches[0], patches[1], patches[2]:
        if pytest_result is not None:
            with patches[3]:
                return executar_harness_validacao(
                    task_id, 1,
                    coder_base_dir=coder,
                    execution_base_dir=execution,
                    tasks_base_dir=tasks,
                )
        return executar_harness_validacao(
            task_id, 1,
            coder_base_dir=coder,
            execution_base_dir=execution,
            tasks_base_dir=tasks,
        )


# ===========================================================================
# Caminho feliz
# ===========================================================================

def test_caminho_feliz_nove_estagios_sucesso(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_src(coder, with_suite=True)
    client, _ = _mock_docker()

    result = _run(
        "TASK-001", coder, execution, tasks, client,
        pytest_result={"status": "sucesso", "resultado_resumo": "sucesso_total"},
    )

    # Ordem e completude dos 9 estágios
    nomes = [s["stage"] for s in result["stages"]]
    assert nomes == _STAGE_ORDER
    # Todos os estágios concluíram com sucesso
    assert all(s["status"] == "sucesso" for s in result["stages"])
    assert result["overall_status"] == "sucesso"
    # Report bem-formado (revalida contra o schema Pydantic)
    ExecutionReport(**result)


def test_caminho_feliz_report_persistido(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_src(coder, with_suite=True)
    client, _ = _mock_docker()

    result = _run(
        "TASK-001", coder, execution, tasks, client,
        pytest_result={"status": "sucesso", "resultado_resumo": "sucesso_total"},
    )

    assert result["report_path"].endswith("TASK-001.report.json")
    assert result["work_item_id"] == "TASK-001"
    assert result["iteration"] == 1


# ===========================================================================
# Abort crítico — falha na implantação (estágio 2) aborta 4–7
# ===========================================================================

def test_abort_critico_implantacao_pula_estagios_seguintes(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_src(coder)
    client, _ = _mock_docker(build_raises=BuildError("erro de build simulado", build_log=[]))

    result = _run("TASK-001", coder, execution, tasks, client)

    by_name = {s["stage"]: s for s in result["stages"]}
    # Estágio 2 falhou
    assert by_name["implantacao_artefato"]["status"] == "falha"
    # Estágios 4–7 foram pulados (dependem da implantação)
    for nome in (
        "inicializacao_aplicacao",
        "coleta_logs_execucao",
        "testes_automatizados",
        "validacoes_work_item",
    ):
        assert by_name[nome]["status"] == "pulado", nome
    # Estágio 3 (coleta logs de build) ainda roda — logs existem mesmo em falha
    assert by_name["coleta_logs_implantacao"]["status"] == "sucesso"
    # overall reflete a falha
    assert result["overall_status"] == "falha"
    # Consolidação e geração de relatório sempre acontecem
    assert by_name["consolidacao_evidencias"]["status"] == "sucesso"
    assert by_name["geracao_relatorio"]["status"] == "sucesso"


# ===========================================================================
# Estágio de testes PULADO quando não há suíte
# ===========================================================================

def test_testes_pulado_quando_nao_ha_suite(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_src(coder, with_suite=False)  # sem test_*.py
    client, _ = _mock_docker()

    result = _run("TASK-001", coder, execution, tasks, client)

    by_name = {s["stage"]: s for s in result["stages"]}
    # Sem suíte → PULADO (não é erro)
    assert by_name["testes_automatizados"]["status"] == "pulado"
    # Ausência de suíte NÃO derruba o overall
    assert result["overall_status"] == "sucesso"


# ===========================================================================
# Serialização JSON + markdown + sobrescrita atômica
# ===========================================================================

def test_serializacao_json_markdown_e_sobrescrita_atomica(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_src(coder)
    client, _ = _mock_docker()

    json_path = execution / "TASK-001.report.json"
    md_path = execution / "TASK-001.report.md"
    tmp_path_json = execution / "TASK-001.report.json.tmp"

    _run("TASK-001", coder, execution, tasks, client)

    # Ambos os artefatos existem e o JSON é válido
    assert json_path.is_file()
    assert md_path.is_file()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["work_item_id"] == "TASK-001"
    assert "# Relatório de Execução" in md_path.read_text(encoding="utf-8")
    # Nenhum arquivo temporário deixado para trás (escrita atômica)
    assert not tmp_path_json.exists()

    # Reexecução sobrescreve atomicamente no mesmo path, sem lixo temporário
    _run("TASK-001", coder, execution, tasks, client)
    data2 = json.loads(json_path.read_text(encoding="utf-8"))
    assert data2["work_item_id"] == "TASK-001"
    assert not tmp_path_json.exists()


# ===========================================================================
# Estágio 7 — uma evidência por critério, sem veredito
# ===========================================================================

def test_estagio7_uma_evidencia_por_criterio_sem_veredito(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    criteria = ["A rota GET / responde 200", "O sistema deve ser intuitivo"]
    _write_task(tasks, criteria=criteria)
    _write_src(coder)
    client, _ = _mock_docker()

    result = _run("TASK-001", coder, execution, tasks, client)

    evidencias = result["criteria_evidence"]
    # Exatamente uma evidência por critério, na mesma ordem
    assert len(evidencias) == len(criteria)
    assert [e["criterion"] for e in evidencias] == criteria

    # NENHUM campo de veredito vazou para a evidência
    chaves_veredito = {"status", "verdict", "approved", "aprovado", "atendido", "veredito"}
    for e in evidencias:
        assert not (chaves_veredito & set(e.keys()))

    # Critério com rota é verificável; critério semântico não é
    assert evidencias[0]["checkable"] is True
    assert evidencias[1]["checkable"] is False
