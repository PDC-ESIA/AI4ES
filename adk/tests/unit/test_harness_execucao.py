"""Tests para o harness de execução (shared/tools/harness_execucao.py).

Docker e requests são MOCKADOS — nenhum container real é subido. O estágio 6
roda o comando de teste resolvido pelo chamador DENTRO do container via
`container.exec_run`, também mockado (ver `_make_exec_run`), então nenhum
comando real é executado. Cobre:
- caminho feliz: 9 estágios concluem, overall_status=sucesso, report bem-formado;
- abort crítico: falha na implantação (estágio 2) aborta 4–7, overall=falha;
- estágio de testes PULADO quando nenhum comando de teste é fornecido;
- testes que FALHAM viram FALHA no estágio, mas o harness não emite veredito;
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


class _ExecResult:
    """Imita o ExecResult do docker-py (exit_code + output)."""

    def __init__(self, exit_code, output):
        self.exit_code = exit_code
        self.output = output


def _make_exec_run(exit_code=0, stdout=None, stderr=""):
    """Fabrica um `exec_run` que simula o ÚNICO comando que o estágio 6 dispara
    no container: `timeout 120 <comando_teste>`.

    O harness não conhece o test runner — classifica só pelo exit code — então
    o mock responde sempre a mesma coisa, qualquer que seja o comando.

    - exit_code: 0 passou, 124 timeout, 126/127 comando inválido, resto falhou.
    - stdout/stderr: saída bruta do comando (vira `saida_tail` na evidência).
    """
    if stdout is None:
        stdout = "1 passed in 0.01s" if exit_code == 0 else "1 failed in 0.01s"

    def exec_run(cmd, workdir=None, demux=False):
        out, err = stdout.encode(), stderr.encode()
        return _ExecResult(exit_code, (out, err) if demux else out)

    return exec_run


def _mock_docker(
    container_status="running",
    build_raises=None,
    exit_code=0,
    stdout=None,
    stderr="",
):
    """Cria um client Docker mockado (build/run/cleanup) cujo container expõe
    um `exec_run` que simula a execução do comando de teste dentro do container."""
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
        exit_code=exit_code, stdout=stdout, stderr=stderr
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


def _write_src(coder_dir):
    (coder_dir / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8"
    )
    (coder_dir / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")


def _dirs(tmp_path):
    coder = tmp_path / "coder" / "src"
    execution = tmp_path / "coder" / "execution"
    tasks = tmp_path / "coder" / "tasks"
    for d in (coder, execution, tasks):
        d.mkdir(parents=True, exist_ok=True)
    return coder, execution, tasks


def _run(task_id, coder, execution, tasks, client, comando_teste=None):
    """Executa o harness com Docker, requests e time.sleep mockados.

    O Dockerfile não é passado de fora: cai no caminho standalone e é lido de
    `coder_dir/Dockerfile` (escrito por `_write_src`). Já o comando de teste do
    estágio 6 SEMPRE vem do chamador — sem `comando_teste`, o estágio é pulado
    por definição. Quando informado, roda "dentro do container" via
    `container.exec_run`, mockado em `_mock_docker` — nenhum container real é
    subido nem comando real é executado.
    """
    probe_result = [{"status": 200, "error": None, "body": "OK"}]
    with patch("docker.from_env", return_value=client), \
         patch("shared.tools.harness_execucao.probe.executar_probe", return_value=probe_result), \
         patch("shared.tools.harness_execucao.time.sleep"):
        return executar_harness_validacao(
            task_id, 1,
            coder_base_dir=coder,
            execution_base_dir=execution,
            tasks_base_dir=tasks,
            comando_teste=comando_teste,
            comando_teste_origem="llm" if comando_teste else None,
        )


# ===========================================================================
# Caminho feliz
# ===========================================================================

def test_caminho_feliz_nove_estagios_sucesso(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_src(coder)
    client, _ = _mock_docker()

    result = _run("TASK-001", coder, execution, tasks, client, comando_teste="pytest")

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
    _write_src(coder)
    client, _ = _mock_docker()

    result = _run("TASK-001", coder, execution, tasks, client, comando_teste="pytest")

    assert result["report_path"].endswith("TASK-001.report.json")
    assert result["work_item_id"] == "TASK-001"
    assert result["iteration"] == 1

    # O estágio 6 rodou o comando entregue pelo chamador DENTRO do container e
    # registrou só evidência bruta: o comando, sua origem e o exit code.
    testes = next(s for s in result["stages"] if s["stage"] == "testes_automatizados")
    assert testes["status"] == "sucesso"
    assert testes["evidence"]["comando"] == "pytest"
    assert testes["evidence"]["comando_origem"] == "llm"
    assert testes["evidence"]["exit_code"] == 0
    assert "passed" in testes["evidence"]["saida_tail"]


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
# Estágio de testes PULADO quando nenhum comando de teste é fornecido
# ===========================================================================

def test_testes_pulado_quando_nao_ha_comando(tmp_path):
    """O comando de teste é resolvido FORA do harness. Sem ele, o estágio 6 não
    tem o que rodar e sai como PULADO — evidência honesta, não erro."""
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_src(coder)
    client, _ = _mock_docker()

    # _run sem `comando_teste` → o estágio 6 nem chega a chamar o container
    result = _run("TASK-001", coder, execution, tasks, client)

    by_name = {s["stage"]: s for s in result["stages"]}
    testes = by_name["testes_automatizados"]
    assert testes["status"] == "pulado"
    assert "comando de teste" in testes["summary"]
    # Ausência de comando NÃO derruba o overall
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
    _write_src(coder)
    # o comando de teste sai com 1 (houve falhas)
    client, _ = _mock_docker(exit_code=1, stdout="1 failed, 0 passed in 0.01s")

    result = _run("TASK-001", coder, execution, tasks, client, comando_teste="pytest")
    by_name = {s["stage"]: s for s in result["stages"]}
    testes = by_name["testes_automatizados"]

    # O estágio marca FALHA e registra o código, mas continua sendo só evidência
    assert testes["status"] == "falha"
    assert testes["error_code"] == "TESTES_FALHARAM"
    assert testes["evidence"]["exit_code"] == 1
    assert "1 failed" in testes["evidence"]["saida_tail"]
    # Nenhum campo de veredito vazou para a evidência do estágio
    assert not ({"verdict", "aprovado", "veredito", "approved"} & set(testes["evidence"].keys()))
    # Testes não são estágio crítico: a falha deles NÃO derruba o status agregado
    # (o julgamento é do implementation_validator, não do harness).
    assert result["overall_status"] == "sucesso"


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