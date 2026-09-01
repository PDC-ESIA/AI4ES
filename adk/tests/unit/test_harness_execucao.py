"""Tests para o harness de execução (shared/tools/coding_tools/harness_execucao.py).

Após o desacoplamento de tecnologias (issue #370), o harness é dirigido por três
contratos declarativos — manifesto `run.json`, perfil de execução e sandbox — e
não conhece mais Docker/FastAPI diretamente. Estes testes são herméticos: o
sandbox é substituído por um `FakeSandbox` (via patch em `create_sandbox`) e o
`requests.get` é mockado. Nenhum processo/container real é iniciado.

Cobre:
- caminho feliz nos três perfis (S=service, C=command, B=none);
- manifesto ausente / inválido → estágio 1 ERRO, estágios seguintes pulados;
- falha de build (estágio 2) aborta 4–7, overall=falha;
- healthcheck/execução que falham marcam o estágio, sem veredito;
- estágio de testes: sucesso, falha, timeout e PULADO (sem comandos);
- estágio 7 produz uma evidência por critério e NUNCA um veredito;
- perfis sem HTTP produzem evidência textual (checkable=False);
- serialização JSON + markdown com sobrescrita atômica;
- o sandbox é sempre encerrado (cleanup) ao final.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from shared.execution.sandbox import CommandResult
from shared.tools.coding_tools.harness_execucao import executar_harness_validacao
from shared.tools.coding_tools.harness_schemas import ExecutionReport

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
# Fake sandbox — implementa a interface Sandbox de forma determinística
# ---------------------------------------------------------------------------

class FakeSandbox:
    """Sandbox de teste: registra chamadas e devolve resultados configuráveis.

    `exec_results` mapeia uma substring do comando → CommandResult. O primeiro
    match vence; sem match, usa `default_exec` (sucesso vazio).
    """

    def __init__(self, *, exec_results=None, default_exec=None, logs_text=""):
        self.exec_results = exec_results or {}
        self.default_exec = default_exec or CommandResult(
            exit_code=0, stdout="", stderr="", timed_out=False
        )
        self.logs_text = logs_text
        self._root = Path("/tmp/fake-sandbox")
        self.setup_called = False
        self.cleanup_called = False
        self.started_service = None
        self.exec_calls: list[str] = []

    @property
    def root(self) -> Path:
        return self._root

    def setup(self, source_dir: Path) -> None:
        self.setup_called = True

    def exec(self, command, *, timeout, env=None):
        self.exec_calls.append(command)
        for key, res in self.exec_results.items():
            if key in command:
                return res
        return self.default_exec

    def start_service(self, command, *, env=None) -> None:
        self.started_service = command

    def logs(self) -> str:
        return self.logs_text

    def cleanup(self) -> None:
        self.cleanup_called = True


# ---------------------------------------------------------------------------
# Helpers de fixtures em disco
# ---------------------------------------------------------------------------

def _mock_response(status_code=200, json_data=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data if json_data is not None else {"paths": {"/": {"get": {}}}}
    r.text = "OK"
    return r


def _dirs(tmp_path):
    coder = tmp_path / "coder" / "src"
    execution = tmp_path / "coder" / "execution"
    tasks = tmp_path / "coder" / "tasks"
    for d in (coder, execution, tasks):
        d.mkdir(parents=True, exist_ok=True)
    return coder, execution, tasks


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


def _write_macro(tasks_dir, product_type="api_service"):
    (tasks_dir / "_macro_context.json").write_text(
        json.dumps({"product_type": product_type}), encoding="utf-8"
    )


def _manifest_service(**over):
    m = {
        "schema_version": "1",
        "surface": "service",
        "build": ["pip install -r requirements.txt"],
        "run": "uvicorn main:app --port 8000",
        "test": ["pytest -q"],
        "port": 8000,
        "healthcheck": "/",
        "sandbox": "direct",
    }
    m.update(over)
    return m


def _manifest_command(**over):
    m = {
        "surface": "command",
        "build": ["pip install -r requirements.txt"],
        "run": "python pipeline.py",
        "test": ["pytest -q"],
        "sandbox": "direct",
    }
    m.update(over)
    return m


def _manifest_none(**over):
    m = {
        "surface": "none",
        "build": ["pip install ."],
        "test": ["pytest -q"],
        "sandbox": "direct",
    }
    m.update(over)
    return m


def _write_manifest(coder_dir, manifest: dict):
    (coder_dir / "run.json").write_text(json.dumps(manifest), encoding="utf-8")


def _run(task_id, coder, execution, tasks, sandbox, *, response=None):
    resp = response if response is not None else _mock_response()
    with patch(
        "shared.tools.coding_tools.harness_execucao.create_sandbox",
        return_value=sandbox,
    ), patch("requests.get", return_value=resp), patch(
        "shared.tools.coding_tools.harness_execucao.time.sleep"
    ):
        return executar_harness_validacao(
            task_id,
            1,
            coder_base_dir=coder,
            execution_base_dir=execution,
            tasks_base_dir=tasks,
        )


def _sandbox_ok(tests_passed=1):
    """FakeSandbox de caminho feliz: build ok e testes que passam."""
    return FakeSandbox(
        exec_results={
            "pytest": CommandResult(
                exit_code=0,
                stdout=f"{tests_passed} passed in 0.01s",
                stderr="",
                timed_out=False,
            ),
        },
        logs_text="INFO [app] serviço no ar",
    )


# ===========================================================================
# Caminho feliz — perfil S (service)
# ===========================================================================

def test_caminho_feliz_service_nove_estagios_sucesso(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_macro(tasks, "api_service")
    _write_manifest(coder, _manifest_service())
    sandbox = _sandbox_ok()

    result = _run("TASK-001", coder, execution, tasks, sandbox)

    nomes = [s["stage"] for s in result["stages"]]
    assert nomes == _STAGE_ORDER
    assert all(s["status"] == "sucesso" for s in result["stages"])
    assert result["overall_status"] == "sucesso"
    ExecutionReport(**result)

    # O serviço foi iniciado em segundo plano e o sandbox foi encerrado.
    assert sandbox.started_service == "uvicorn main:app --port 8000"
    assert sandbox.setup_called is True
    assert sandbox.cleanup_called is True


def test_caminho_feliz_service_report_persistido(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_manifest(coder, _manifest_service())
    sandbox = _sandbox_ok()

    result = _run("TASK-001", coder, execution, tasks, sandbox)

    assert result["report_path"].endswith("TASK-001.report.json")
    assert result["work_item_id"] == "TASK-001"
    assert result["iteration"] == 1

    testes = next(s for s in result["stages"] if s["stage"] == "testes_automatizados")
    assert testes["status"] == "sucesso"
    resultados = testes["evidence"]["resultados"]
    assert resultados[0]["resumo"]["passaram"] == 1
    assert resultados[0]["comando"] == "pytest -q"


# ===========================================================================
# Caminho feliz — perfil C (command): estágio 4 executa o `run` (exit-code)
# ===========================================================================

def test_caminho_feliz_command_executa_run(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=["O pipeline processa o arquivo de entrada"])
    _write_macro(tasks, "data_pipeline")
    _write_manifest(coder, _manifest_command())
    sandbox = FakeSandbox(
        exec_results={
            "pipeline.py": CommandResult(
                exit_code=0, stdout="processado", stderr="", timed_out=False
            ),
            "pytest": CommandResult(
                exit_code=0, stdout="2 passed", stderr="", timed_out=False
            ),
        }
    )

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    by_name = {s["stage"]: s for s in result["stages"]}

    # Não sobe serviço; o `run` é executado como comando único no estágio 4.
    assert sandbox.started_service is None
    assert "python pipeline.py" in sandbox.exec_calls
    init = by_name["inicializacao_aplicacao"]
    assert init["status"] == "sucesso"
    assert init["evidence"]["exit_code"] == 0
    assert result["overall_status"] == "sucesso"

    # Perfil sem HTTP → evidências textuais (não verificáveis automaticamente).
    for e in result["criteria_evidence"]:
        assert e["checkable"] is False


def test_command_run_falha_marca_estagio4(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=["O pipeline processa o arquivo"])
    _write_manifest(coder, _manifest_command())
    sandbox = FakeSandbox(
        exec_results={
            "pipeline.py": CommandResult(
                exit_code=2, stdout="", stderr="boom", timed_out=False
            ),
        }
    )

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    by_name = {s["stage"]: s for s in result["stages"]}

    init = by_name["inicializacao_aplicacao"]
    assert init["status"] == "falha"
    assert init["error_code"] == "EXECUCAO_FALHOU"
    assert init["evidence"]["exit_code"] == 2


# ===========================================================================
# Caminho feliz — perfil B (none): estágio 4 pulado; foco em build+testes
# ===========================================================================

def test_caminho_feliz_none_pula_inicializacao(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=["A biblioteca expõe a função parse()"])
    _write_macro(tasks, "library")
    _write_manifest(coder, _manifest_none())
    sandbox = _sandbox_ok()

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    by_name = {s["stage"]: s for s in result["stages"]}

    assert sandbox.started_service is None
    # Sem superfície de topo: inicialização é pulada, mas isso NÃO derruba o overall.
    assert by_name["inicializacao_aplicacao"]["status"] == "pulado"
    assert by_name["testes_automatizados"]["status"] == "sucesso"
    assert result["overall_status"] == "sucesso"
    for e in result["criteria_evidence"]:
        assert e["checkable"] is False


# ===========================================================================
# Manifesto ausente / inválido — estágio 1 ERRO, seguintes pulados
# ===========================================================================

def test_manifesto_ausente_erro_estagio1(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    # NÃO escreve run.json
    sandbox = _sandbox_ok()

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    by_name = {s["stage"]: s for s in result["stages"]}

    prep = by_name["preparacao_ambiente"]
    assert prep["status"] == "erro"
    assert prep["error_code"] == "MANIFESTO_AUSENTE"
    assert by_name["implantacao_artefato"]["status"] == "pulado"
    assert result["overall_status"] == "erro"
    # Sandbox nem chegou a ser criado/usado.
    assert sandbox.setup_called is False


def test_manifesto_invalido_erro_estagio1(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    # surface=service sem port/run → incoerente (ManifestError na carga).
    _write_manifest(coder, {"surface": "service"})
    sandbox = _sandbox_ok()

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    prep = next(s for s in result["stages"] if s["stage"] == "preparacao_ambiente")

    assert prep["status"] == "erro"
    assert prep["error_code"] == "MANIFESTO_INVALIDO"
    assert result["overall_status"] == "erro"


# ===========================================================================
# Falha de build (estágio 2) aborta 4–7
# ===========================================================================

def test_falha_build_pula_estagios_seguintes(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_manifest(coder, _manifest_service())
    sandbox = FakeSandbox(
        exec_results={
            "pip install": CommandResult(
                exit_code=1, stdout="", stderr="ERROR: no matching distribution", timed_out=False
            ),
        }
    )

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    by_name = {s["stage"]: s for s in result["stages"]}

    assert by_name["implantacao_artefato"]["status"] == "falha"
    assert by_name["implantacao_artefato"]["error_code"] == "FALHA_BUILD"
    for nome in (
        "inicializacao_aplicacao",
        "coleta_logs_execucao",
        "testes_automatizados",
        "validacoes_work_item",
    ):
        assert by_name[nome]["status"] == "pulado", nome
    # Estágio 3 (coleta logs de build) ainda roda — logs existem mesmo em falha.
    assert by_name["coleta_logs_implantacao"]["status"] == "sucesso"
    assert result["overall_status"] == "falha"
    assert by_name["consolidacao_evidencias"]["status"] == "sucesso"
    assert by_name["geracao_relatorio"]["status"] == "sucesso"
    # Serviço nunca foi iniciado; sandbox foi encerrado mesmo assim.
    assert sandbox.started_service is None
    assert sandbox.cleanup_called is True


def test_falha_npm_ci_preserva_causa_e_diagnostica_lockfile(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    manifesto = _manifest_service()
    manifesto["build"] = ["npm ci"]
    _write_manifest(coder, manifesto)
    causa = (
        "npm error `npm ci` can only install packages when your package.json "
        "and package-lock.json are in sync.\n"
    )
    sandbox = FakeSandbox(
        exec_results={
            "npm ci": CommandResult(
                exit_code=1,
                stdout="",
                stderr=causa + ("npm help option\n" * 500),
                timed_out=False,
            ),
        }
    )

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    implantacao = next(
        stage
        for stage in result["stages"]
        if stage["stage"] == "implantacao_artefato"
    )

    assert "fora de sincronia" in implantacao["summary"]
    assert "fora de sincronia" in implantacao["evidence"]["diagnostico"]
    assert causa.strip() in implantacao["evidence"]["build_logs_excerpt"]
    assert "caracteres omitidos" in implantacao["evidence"]["build_logs_excerpt"]


# ===========================================================================
# Healthcheck do serviço falha → estágio 4 FALHA
# ===========================================================================

def test_healthcheck_falha_marca_inicializacao(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_manifest(coder, _manifest_service())
    sandbox = _sandbox_ok()

    # requests.get retorna 500 no healthcheck → app não sobe.
    result = _run(
        "TASK-001", coder, execution, tasks, sandbox, response=_mock_response(500)
    )
    by_name = {s["stage"]: s for s in result["stages"]}

    init = by_name["inicializacao_aplicacao"]
    assert init["status"] == "falha"
    assert init["error_code"] == "APP_NAO_INICIALIZOU"
    # Testes ainda rodam (gatilham em deploy_ok, não em app_ok).
    assert by_name["testes_automatizados"]["status"] == "sucesso"
    # Estágio 7: app não subiu → evidências não verificáveis.
    for e in result["criteria_evidence"]:
        assert e["checkable"] is False
    # Inicialização é crítica no perfil S → overall falha.
    assert result["overall_status"] == "falha"


# ===========================================================================
# Estágio de testes: sucesso, falha, timeout, pulado
# ===========================================================================

def test_testes_falharam_marcam_falha_sem_veredito(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_manifest(coder, _manifest_service())
    sandbox = FakeSandbox(
        exec_results={
            "pytest": CommandResult(
                exit_code=1, stdout="1 failed in 0.02s", stderr="", timed_out=False
            ),
        },
        logs_text="INFO no ar",
    )

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    testes = next(s for s in result["stages"] if s["stage"] == "testes_automatizados")

    assert testes["status"] == "falha"
    assert testes["error_code"] == "TESTES_FALHARAM"
    assert testes["evidence"]["resultados"][0]["resumo"]["falharam"] == 1
    # Nenhum campo de veredito vazou.
    assert not ({"verdict", "aprovado", "veredito", "approved"} & set(testes["evidence"].keys()))
    # Testes não são estágio crítico: a falha deles NÃO derruba o overall.
    assert result["overall_status"] == "sucesso"


def test_testes_timeout_marca_falha(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_manifest(coder, _manifest_service())
    sandbox = FakeSandbox(
        exec_results={
            "pytest": CommandResult(
                exit_code=None, stdout="", stderr="", timed_out=True
            ),
        },
        logs_text="INFO no ar",
    )

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    testes = next(s for s in result["stages"] if s["stage"] == "testes_automatizados")

    assert testes["status"] == "falha"
    assert testes["error_code"] == "TESTES_TIMEOUT"


def test_testes_pulado_quando_manifesto_sem_test(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_manifest(coder, _manifest_service(test=[]))
    sandbox = _sandbox_ok()

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    testes = next(s for s in result["stages"] if s["stage"] == "testes_automatizados")

    assert testes["status"] == "pulado"
    assert result["overall_status"] == "sucesso"


# ===========================================================================
# Estágio 7 — uma evidência por critério, sem veredito
# ===========================================================================

def test_estagio7_uma_evidencia_por_criterio_sem_veredito(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    criteria = ["A rota GET / responde 200", "O sistema deve ser intuitivo"]
    _write_task(tasks, criteria=criteria)
    _write_manifest(coder, _manifest_service())
    sandbox = _sandbox_ok()

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    evidencias = result["criteria_evidence"]

    assert len(evidencias) == len(criteria)
    assert [e["criterion"] for e in evidencias] == criteria

    chaves_veredito = {"status", "verdict", "approved", "aprovado", "atendido", "veredito"}
    for e in evidencias:
        assert not (chaves_veredito & set(e.keys()))

    # Critério com rota GET é verificável; critério semântico não é.
    assert evidencias[0]["checkable"] is True
    assert evidencias[1]["checkable"] is False


def test_estagio7_verbo_com_payload_nao_e_checado_via_get(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    criteria = [
        "POST /usuarios deve retornar 201",
        "Após o POST /itens, o GET /itens deve listar o item",
        "A rota GET /status responde 200",
    ]
    _write_task(tasks, criteria=criteria)
    _write_manifest(coder, _manifest_service())
    sandbox = _sandbox_ok()

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    ev = {e["criterion"]: e for e in result["criteria_evidence"]}

    assert ev[criteria[0]]["checkable"] is False
    assert "POST" in ev[criteria[0]]["check_performed"]
    assert not ev[criteria[0]]["check_performed"].startswith("Requisição HTTP GET")

    assert ev[criteria[1]]["checkable"] is False
    assert "POST" in ev[criteria[1]]["check_performed"]

    assert ev[criteria[2]]["checkable"] is True
    assert ev[criteria[2]]["check_performed"].startswith("Requisição HTTP GET")


# ===========================================================================
# Serialização JSON + markdown + sobrescrita atômica
# ===========================================================================

def test_serializacao_json_markdown_e_sobrescrita_atomica(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_manifest(coder, _manifest_service())

    json_path = execution / "TASK-001.report.json"
    md_path = execution / "TASK-001.report.md"
    tmp_path_json = execution / "TASK-001.report.json.tmp"

    _run("TASK-001", coder, execution, tasks, _sandbox_ok())

    assert json_path.is_file()
    assert md_path.is_file()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["work_item_id"] == "TASK-001"
    assert "# Relatório de Execução" in md_path.read_text(encoding="utf-8")
    assert not tmp_path_json.exists()

    # Reexecução sobrescreve atomicamente no mesmo path, sem lixo temporário.
    _run("TASK-001", coder, execution, tasks, _sandbox_ok())
    data2 = json.loads(json_path.read_text(encoding="utf-8"))
    assert data2["work_item_id"] == "TASK-001"
    assert not tmp_path_json.exists()


# ===========================================================================
# Task ausente — estágio 1 ERRO antes de tocar no manifesto/sandbox
# ===========================================================================

def test_task_ausente_erro_estagio1(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_manifest(coder, _manifest_service())
    sandbox = _sandbox_ok()

    result = _run("TASK-404", coder, execution, tasks, sandbox)
    prep = next(s for s in result["stages"] if s["stage"] == "preparacao_ambiente")

    assert prep["status"] == "erro"
    assert prep["error_code"] == "TASK_NAO_ENCONTRADA"
    assert sandbox.setup_called is False
