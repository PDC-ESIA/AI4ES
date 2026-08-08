"""Tests para o harness de execução (shared/tools/harness_execucao.py).

Docker e requests são MOCKADOS — nenhum container real é subido. O estágio 6
roda pytest DENTRO do container via `container.exec_run`, também mockado
(ver `_make_exec_run`), então nenhuma suíte real é executada. Cobre:
- caminho feliz: 9 estágios concluem, overall_status=sucesso, report bem-formado;
- abort crítico: falha na implantação (estágio 2) aborta 4–7, overall=falha;
- estágio de testes PULADO quando não há suíte;
- testes que FALHAM viram FALHA no estágio, mas o harness não emite veredito;
- fallback para modo 'plain' quando os plugins de report/cov não estão na imagem;
- serialização JSON + markdown com sobrescrita atômica;
- estágio 7 produz um CriterionEvidence por critério e NUNCA um veredito.
"""

import json
from unittest.mock import MagicMock, patch

import docker
from docker.errors import BuildError

from shared.tools.coding_tools.harness_execucao import (
    _MANIFEST_NAME,
    executar_harness_validacao,
)
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


class _ExecResult:
    """Imita o ExecResult do docker-py (exit_code + output)."""

    def __init__(self, exit_code, output):
        self.exit_code = exit_code
        self.output = output


def _make_exec_run(pytest_exit=0, has_pytest=True, json_plugin=True, report=None, cov=None):
    """Fabrica um `exec_run` que simula os comandos que o estágio 6 dispara no
    container: probe do pytest, execução da suíte e `cat` dos relatórios.

    - pytest_exit: exit code do pytest (0 ok, 1 falhas, 5 nada coletado, 124 timeout).
    - has_pytest: se False, o probe falha e a instalação em runtime não resolve.
    - json_plugin: se False, `--json-report` é rejeitado (exit 4) → fallback plain.
    """
    report = report or {
        "summary": {"passed": 1, "failed": 0, "error": 0, "skipped": 0, "total": 1},
        "tests": [],
    }
    cov = cov or {"totals": {"percent_covered": 100.0, "covered_lines": 3, "num_statements": 3}}

    def exec_run(cmd, workdir=None, demux=False):
        shell = cmd[-1] if isinstance(cmd, (list, tuple)) else cmd

        def out(s):
            b = s.encode()
            return (b, b"") if demux else b

        if "pytest --version" in shell:
            return _ExecResult(0 if has_pytest else 1, out("pytest 8.2.0" if has_pytest else ""))
        if shell.startswith("pip install"):
            return _ExecResult(0, out("installed"))
        if shell.startswith("cat ") and "report.json" in shell:
            return _ExecResult(0, out(json.dumps(report)))
        if shell.startswith("cat ") and "cov.json" in shell:
            return _ExecResult(0, out(json.dumps(cov)))
        if "python -m pytest" in shell:
            if "--json-report" in shell and not json_plugin:
                return _ExecResult(4, out("error: unrecognized arguments: --json-report"))
            texto = "1 passed in 0.01s" if pytest_exit == 0 else "1 failed in 0.01s"
            return _ExecResult(pytest_exit, out(texto))
        return _ExecResult(0, out(""))

    return exec_run


def _mock_docker(
    container_status="running",
    build_raises=None,
    pytest_exit=0,
    has_pytest=True,
    json_plugin=True,
    report=None,
):
    """Cria um client Docker mockado (build/run/cleanup) cujo container expõe
    um `exec_run` que simula a execução do pytest dentro do container."""
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
    container.exec_run.side_effect = _make_exec_run(
        pytest_exit=pytest_exit,
        has_pytest=has_pytest,
        json_plugin=json_plugin,
        report=report,
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


def _run(task_id, coder, execution, tasks, client):
    """Executa o harness com Docker, requests e time.sleep mockados.

    O pytest do estágio 6 roda "dentro do container" via `container.exec_run`,
    também mockado em `_mock_docker` — nenhum container real é subido nem
    suíte real é executada.
    """
    with patch("docker.from_env", return_value=client), \
         patch("requests.get", return_value=_mock_response()), \
         patch("shared.tools.coding_tools.harness_execucao.time.sleep"):
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

    result = _run("TASK-001", coder, execution, tasks, client)

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

    result = _run("TASK-001", coder, execution, tasks, client)

    assert result["report_path"].endswith("TASK-001.report.json")
    assert result["work_item_id"] == "TASK-001"
    assert result["iteration"] == 1

    # O estágio 6 rodou a suíte DENTRO do container: o alvo é o path /app,
    # não um path reescrito para o workspace do qa_agent (regressão do bug).
    testes = next(s for s in result["stages"] if s["stage"] == "testes_automatizados")
    assert testes["status"] == "sucesso"
    assert testes["evidence"]["alvo_container"] == "/app/test_app.py"
    assert testes["evidence"]["modo"] == "json"


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


# ===========================================================================
# Testes que FALHAM → estágio FALHA, mas o harness NÃO emite veredito
# ===========================================================================

def test_testes_falharam_marcam_falha_sem_veredito(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_src(coder, with_suite=True)
    # pytest sai com 1 (houve falhas); report reflete 1 falha
    client, _ = _mock_docker(
        pytest_exit=1,
        report={
            "summary": {"passed": 0, "failed": 1, "error": 0, "skipped": 0, "total": 1},
            "tests": [
                {
                    "nodeid": "test_app.py::test_ok",
                    "outcome": "failed",
                    "call": {"crash": {"lineno": 2, "message": "AssertionError"}},
                }
            ],
        },
    )

    result = _run("TASK-001", coder, execution, tasks, client)
    by_name = {s["stage"]: s for s in result["stages"]}
    testes = by_name["testes_automatizados"]

    # O estágio marca FALHA e registra o código, mas continua sendo só evidência
    assert testes["status"] == "falha"
    assert testes["error_code"] == "TESTES_FALHARAM"
    assert testes["evidence"]["resumo"]["falharam"] == 1
    # Nenhum campo de veredito vazou para a evidência do estágio
    assert not ({"verdict", "aprovado", "veredito", "approved"} & set(testes["evidence"].keys()))
    # Testes não são estágio crítico: a falha deles NÃO derruba o status agregado
    # (o julgamento é do implementation_validator, não do harness).
    assert result["overall_status"] == "sucesso"


# ===========================================================================
# Sem plugins de report/cov na imagem → fallback para modo 'plain'
# ===========================================================================

def test_fallback_plain_quando_sem_plugin_json(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_src(coder, with_suite=True)
    # pytest existe, mas --json-report/--cov não são reconhecidos (exit 4)
    client, _ = _mock_docker(pytest_exit=0, json_plugin=False)

    result = _run("TASK-001", coder, execution, tasks, client)
    testes = next(s for s in result["stages"] if s["stage"] == "testes_automatizados")

    # Caiu para o modo texto, mas ainda classificou o resultado a partir do exit code
    assert testes["status"] == "sucesso"
    assert testes["evidence"]["modo"] == "plain"
    assert testes["evidence"]["resumo"]["passaram"] == 1


# ===========================================================================
# Estágio 7 — critérios com POST/PUT/PATCH/DELETE não são checados via GET
# ===========================================================================

def test_estagio7_verbo_com_payload_nao_e_checado_via_get(tmp_path):
    """Critério que exige POST/PUT/PATCH/DELETE não pode ser 'verificado' com um
    GET desalinhado: deve sair como checkable=False, com o motivo registrado,
    para não induzir o validador (ex.: 405 num endpoint POST é o esperado para
    um GET, não uma falha do critério)."""
    coder, execution, tasks = _dirs(tmp_path)
    criteria = [
        "POST /usuarios deve retornar 201",                      # verbo com payload
        "Após o POST /itens, o GET /itens deve listar o item",   # verbos mistos
        "A rota GET /status responde 200",                       # GET puro → checável
    ]
    _write_task(tasks, criteria=criteria)
    _write_src(coder)
    client, _ = _mock_docker()

    result = _run("TASK-001", coder, execution, tasks, client)
    ev = {e["criterion"]: e for e in result["criteria_evidence"]}

    # POST puro: não checável, e o motivo cita o verbo não derivável
    assert ev[criteria[0]]["checkable"] is False
    assert "POST" in ev[criteria[0]]["check_performed"]
    # Nenhuma requisição desalinhada foi registrada como checagem
    assert not ev[criteria[0]]["check_performed"].startswith("Requisição HTTP GET")

    # Verbos mistos (GET + POST): a parte não-executável contamina o todo → não checável
    assert ev[criteria[1]]["checkable"] is False
    assert "POST" in ev[criteria[1]]["check_performed"]

    # GET puro continua checável, com a requisição registrada
    assert ev[criteria[2]]["checkable"] is True
    assert ev[criteria[2]]["check_performed"].startswith("Requisição HTTP GET")

    
def test_container_nao_inicia_preserva_logs_na_evidence(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_src(coder)
    client, _ = _mock_docker(container_status="exited")

    result = _run("TASK-001", coder, execution, tasks, client)
    implant = next(s for s in result["stages"] if s["stage"] == "implantacao_artefato")

    assert implant["status"] == "falha"
    assert implant["error_code"] == "CONTAINER_NAO_INICIOU"
    assert "Uvicorn running" in implant["evidence"]["runtime_logs_tail"]


# ===========================================================================
# Modo 'command' — artefato roda e TERMINA (benchmark/CLI/função/biblioteca).
#
# Diferente do modo 'service' (container fica ouvindo e é sondado por HTTP), o
# container roda o comando de entrega e espera-se que encerre com um exit code.
# Nada de Docker/HTTP real: o container é MOCKADO já em estado "exited", e o
# `client.containers.run` devolve, em sequência, o container do artefato e (se
# houver test.cmd) o container efêmero da suíte.
# ===========================================================================

def _make_command_container(exit_code=0, logs=b""):
    """Container mockado já FINALIZADO (imita o SDK após o processo encerrar)."""
    c = MagicMock()
    c.status = "exited"
    c.attrs = {"State": {"ExitCode": exit_code}}
    c.logs.return_value = logs
    return c


def _mock_docker_command(artifact_exit=0, test_exit=0, build_raises=None):
    """Client Docker mockado para o modo 'command'.

    `containers.run` é chamado uma vez para o artefato e, quando há test.cmd,
    outra vez para a suíte — por isso o `side_effect` com dois containers.
    """
    client = MagicMock()
    if build_raises is not None:
        client.images.build.side_effect = build_raises
    else:
        image = MagicMock()
        client.images.build.return_value = (
            image,
            [
                {"stream": "Step 1/4 : FROM python:3.12-slim"},
                {"stream": "Successfully built abc123"},
            ],
        )

    artifact = _make_command_container(
        exit_code=artifact_exit,
        logs=b"2026-07-21T10:00:00 INFO [bench] score=0.87 concluido",
    )
    test_c = _make_command_container(
        exit_code=test_exit, logs=b"collected 3 items\n3 passed in 0.02s"
    )
    client.containers.run.side_effect = [artifact, test_c]
    client.containers.get.side_effect = docker.errors.NotFound("sem container")
    return client, artifact, test_c


def _write_command_src(coder_dir, manifest, with_dockerfile=True):
    """Fonte + manifesto (.ai4se_run.json) de uma entrega em modo 'command'.

    O modo 'command' EXIGE Dockerfile do coder (não há fallback); `with_dockerfile`
    permite exercitar a ausência dele.
    """
    (coder_dir / "main.py").write_text(
        "print('benchmark done')\n", encoding="utf-8"
    )
    if with_dockerfile:
        (coder_dir / "Dockerfile").write_text(
            'FROM python:3.12-slim\nCOPY . /app\nWORKDIR /app\n'
            'CMD ["python", "main.py"]\n',
            encoding="utf-8",
        )
    (coder_dir / _MANIFEST_NAME).write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def test_command_mode_caminho_feliz_sem_testes(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_command_src(
        coder,
        {
            "delivery_mode": "command",
            "language": "python",
            "run": {"success_exit_codes": [0]},
        },
    )
    client, _, _ = _mock_docker_command(artifact_exit=0)

    result = _run("TASK-001", coder, execution, tasks, client)
    by_name = {s["stage"]: s for s in result["stages"]}

    # Ordem/completude dos 9 estágios preservada
    assert [s["stage"] for s in result["stages"]] == _STAGE_ORDER
    # Implantação: o comando rodou até o fim e o exit foi capturado
    assert by_name["implantacao_artefato"]["status"] == "sucesso"
    assert by_name["implantacao_artefato"]["evidence"]["exit_code"] == 0
    # Inicialização: exit dentro dos esperados (sem healthcheck HTTP)
    assert by_name["inicializacao_aplicacao"]["status"] == "sucesso"
    # Sem test.cmd → estágio de testes PULADO (não é erro)
    assert by_name["testes_automatizados"]["status"] == "pulado"
    # Evidência de critério: nada verificável via HTTP neste modo
    assert result["criteria_evidence"]
    assert all(e["checkable"] is False for e in result["criteria_evidence"])
    assert result["overall_status"] == "sucesso"
    ExecutionReport(**result)


def test_command_mode_exit_fora_do_esperado_reprova_inicializacao(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_command_src(
        coder,
        {"delivery_mode": "command", "run": {"success_exit_codes": [0]}},
    )
    client, _, _ = _mock_docker_command(artifact_exit=2)

    result = _run("TASK-001", coder, execution, tasks, client)
    by_name = {s["stage"]: s for s in result["stages"]}

    # O comando rodou até o fim (implantação ok), mas o exit inesperado
    # reprova a inicialização — que é estágio CRÍTICO.
    assert by_name["implantacao_artefato"]["status"] == "sucesso"
    assert by_name["inicializacao_aplicacao"]["status"] == "falha"
    assert by_name["inicializacao_aplicacao"]["error_code"] == "COMANDO_EXIT_NAO_ESPERADO"
    # Estágios dependentes da inicialização são pulados
    assert by_name["testes_automatizados"]["status"] == "pulado"
    assert by_name["validacoes_work_item"]["status"] == "pulado"
    assert result["overall_status"] == "falha"


def test_command_mode_success_exit_codes_customizado(tmp_path):
    """Cenário benchmark: um exit code != 0 pode significar sucesso se declarado."""
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_command_src(
        coder,
        {"delivery_mode": "command", "run": {"success_exit_codes": [0, 3]}},
    )
    client, _, _ = _mock_docker_command(artifact_exit=3)

    result = _run("TASK-001", coder, execution, tasks, client)
    by_name = {s["stage"]: s for s in result["stages"]}

    assert by_name["inicializacao_aplicacao"]["status"] == "sucesso"
    assert by_name["inicializacao_aplicacao"]["evidence"]["exit_code"] == 3
    assert result["overall_status"] == "sucesso"


def test_command_mode_testes_com_test_cmd_passa(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_command_src(
        coder,
        {
            "delivery_mode": "command",
            "run": {"success_exit_codes": [0]},
            "test": {"cmd": "pytest -q"},
        },
    )
    client, _, _ = _mock_docker_command(artifact_exit=0, test_exit=0)

    result = _run("TASK-001", coder, execution, tasks, client)
    testes = next(s for s in result["stages"] if s["stage"] == "testes_automatizados")

    # Suíte rodou num container efêmero e passou
    assert testes["status"] == "sucesso"
    assert testes["evidence"]["test_cmd"] == "pytest -q"
    assert testes["evidence"]["exit_code"] == 0
    assert result["overall_status"] == "sucesso"


def test_command_mode_testes_falharam_nao_derrubam_overall(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_command_src(
        coder,
        {
            "delivery_mode": "command",
            "run": {"success_exit_codes": [0]},
            "test": {"cmd": "pytest -q"},
        },
    )
    client, _, _ = _mock_docker_command(artifact_exit=0, test_exit=1)

    result = _run("TASK-001", coder, execution, tasks, client)
    testes = next(s for s in result["stages"] if s["stage"] == "testes_automatizados")

    assert testes["status"] == "falha"
    assert testes["error_code"] == "TESTES_FALHARAM"
    # Testes NÃO são estágio crítico: a falha vira evidência, não veredito.
    assert result["overall_status"] == "sucesso"


def test_command_mode_sem_dockerfile_erra_na_preparacao(tmp_path):
    """Sem Dockerfile do coder o harness não adivinha o runtime em modo command."""
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_command_src(coder, {"delivery_mode": "command"}, with_dockerfile=False)
    client, _, _ = _mock_docker_command()

    result = _run("TASK-001", coder, execution, tasks, client)
    by_name = {s["stage"]: s for s in result["stages"]}

    assert by_name["preparacao_ambiente"]["status"] == "erro"
    assert by_name["preparacao_ambiente"]["error_code"] == "DOCKERFILE_AUSENTE"
    # Preparação é crítica → implantação e demais estágios pulados
    assert by_name["implantacao_artefato"]["status"] == "pulado"
    assert result["overall_status"] == "erro"


def test_command_mode_ativado_pelo_delivery_mode_da_task(tmp_path):
    """Sem 'delivery_mode' no manifesto, o modo vem da Task (fonte primária)."""
    coder, execution, tasks = _dirs(tmp_path)
    # Task declara o modo; manifesto do coder omite delivery_mode.
    (tasks / "TASK-001.json").write_text(
        json.dumps(
            {
                "id": "TASK-001",
                "description": "Função de benchmark",
                "acceptance_criteria": ["Deve calcular a métrica corretamente"],
                "contract": {},
                "delivery_mode": "command",
            }
        ),
        encoding="utf-8",
    )
    _write_command_src(coder, {"run": {"success_exit_codes": [0]}})
    client, _, _ = _mock_docker_command(artifact_exit=0)

    result = _run("TASK-001", coder, execution, tasks, client)
    prep = next(s for s in result["stages"] if s["stage"] == "preparacao_ambiente")

    assert prep["evidence"]["delivery_mode"] == "command"
    assert result["overall_status"] == "sucesso"