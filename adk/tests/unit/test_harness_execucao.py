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

import pytest
from unittest.mock import MagicMock, patch

from shared.execution.sandbox import CommandResult
from shared.tools.coding_tools.harness_execucao import (
    executar_harness_validacao,
    resultados_por_teste,
)
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
    if m.get("acceptance_tests") and "acceptance_task_id" not in m:
        m["acceptance_task_id"] = "TASK-001"
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

def test_testes_falharam_derrubam_status_tecnico(tmp_path):
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
    # Regressão: build + app no ar não podem esconder uma suíte vermelha. Antes
    # isto produzia overall=sucesso, nota 0.6 e aprovação imediata da task.
    assert result["overall_status"] == "falha"


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
    assert result["overall_status"] == "falha"


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
# Estágio 1 — critérios com identidade (formato novo) e o shim do formato antigo
# ===========================================================================

def test_estagio7_aceita_task_no_formato_novo_de_criterios(tmp_path):
    """Task com critérios como OBJETOS (id/description/automatable).

    O harness lê a task do DISCO, e `tool_salvar_task_cr` grava o JSON cru que o
    LLM produziu — então é este formato, e não o modelo Pydantic, que chega aqui.
    """
    coder, execution, tasks = _dirs(tmp_path)
    criteria = [
        {
            "id": "CA-01",
            "description": "A rota GET / responde 200",
            "automatable": True,
        },
        {
            "id": "CA-02",
            "description": "Consigo criar um Ensaio pela interface web",
            "automatable": False,
        },
    ]
    _write_task(tasks, criteria=criteria)
    _write_manifest(coder, _manifest_service())

    result = _run("TASK-001", coder, execution, tasks, _sandbox_ok())

    # A evidência e o report seguem falando o texto do critério (contrato do
    # validador inalterado nesta fase) — o que muda é a origem, agora estruturada.
    textos = [c["description"] for c in criteria]
    assert result["acceptance_criteria"] == textos
    assert [e["criterion"] for e in result["criteria_evidence"]] == textos

    # A classificação NÃO se confunde com `checkable`: o critério de interface é
    # `automatable=False` na task, mas quem decide `checkable` continua sendo o
    # que o harness conseguiu observar naquela execução.
    assert result["criteria_evidence"][0]["checkable"] is True
    assert result["criteria_evidence"][1]["checkable"] is False


def test_estagio7_task_no_formato_antigo_continua_funcionando(tmp_path):
    """Shim de transição: tasks geradas antes da mudança seguem válidas."""
    coder, execution, tasks = _dirs(tmp_path)
    criteria = ["A rota GET / responde 200", "O sistema deve ser intuitivo"]
    _write_task(tasks, criteria=criteria)
    _write_manifest(coder, _manifest_service())

    result = _run("TASK-001", coder, execution, tasks, _sandbox_ok())

    assert result["acceptance_criteria"] == criteria
    assert [e["criterion"] for e in result["criteria_evidence"]] == criteria


def test_estagio7_criterios_malformados_nao_derrubam_a_execucao(tmp_path):
    """Entrada de LLM inaproveitável degrada para "sem critério", nunca levanta."""
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria="não é uma lista")
    _write_manifest(coder, _manifest_service())

    result = _run("TASK-001", coder, execution, tasks, _sandbox_ok())

    assert result["acceptance_criteria"] == []
    assert result["criteria_evidence"] == []
    assert result["overall_status"] == "sucesso"


# ===========================================================================
# Estágio 1 — mapa teste ↔ critério (Fase 1)
# ===========================================================================

def _criterios_objeto():
    return [
        {"id": "CA-01", "description": "A rota GET / responde 200", "automatable": True},
        {"id": "CA-02", "description": "Persistir o ensaio", "automatable": True},
        {
            "id": "CA-03",
            "description": "Consigo criar um Ensaio pela interface web",
            "automatable": False,
        },
    ]


def _estagio(result, nome):
    return next(s for s in result["stages"] if s["stage"] == nome)


def test_estagio1_registra_mapa_teste_criterio_do_manifesto(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(
        coder,
        _manifest_service(
            acceptance_tests={
                "CA-01": ["tests/test_rotas.py::test_raiz"],
                "CA-02": ["tests/test_ensaios.py::test_persiste"],
            }
        ),
    )

    result = _run("TASK-001", coder, execution, tasks, _sandbox_ok())
    evidencia = _estagio(result, "preparacao_ambiente")["evidence"]

    assert evidencia["acceptance_tests"] == {
        "CA-01": ["tests/test_rotas.py::test_raiz"],
        "CA-02": ["tests/test_ensaios.py::test_persiste"],
    }
    assert evidencia["acceptance_tests_ids_desconhecidos"] == []
    # Só os automatizáveis entram na conta: CA-03 não é cobrável por teste.
    assert "2/2 automatizáveis com teste declarado" in (
        _estagio(result, "preparacao_ambiente")["summary"]
    )


def test_estagio1_casa_o_mapa_mesmo_com_grafia_diferente_do_id(tmp_path):
    """O coder escreve o mapa lendo a Task; a grafia do id pode variar."""
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(coder, _manifest_service(acceptance_tests={"ca-1": ["t::a"]}))

    result = _run("TASK-001", coder, execution, tasks, _sandbox_ok())
    evidencia = _estagio(result, "preparacao_ambiente")["evidence"]

    assert evidencia["acceptance_tests"] == {"CA-01": ["t::a"]}


def test_estagio1_id_inexistente_no_mapa_nao_falha_a_execucao(tmp_path):
    """Anotação errada é registrada como evidência, nunca como falha técnica."""
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(
        coder,
        _manifest_service(
            acceptance_tests={"CA-01": ["t::a"], "CA-99": ["t::b"], "XPTO": ["t::c"]}
        ),
    )

    result = _run("TASK-001", coder, execution, tasks, _sandbox_ok())
    estagio1 = _estagio(result, "preparacao_ambiente")

    assert estagio1["status"] == "sucesso"
    assert result["overall_status"] == "sucesso"
    assert estagio1["evidence"]["acceptance_tests"] == {"CA-01": ["t::a"]}
    assert sorted(estagio1["evidence"]["acceptance_tests_ids_desconhecidos"]) == [
        "CA-99",
        "XPTO",
    ]


def test_estagio1_manifesto_com_mapa_malformado_nao_aborta(tmp_path):
    """Mapa inválido não pode derrubar o estágio 1 (crítico) e zerar a nota."""
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(coder, _manifest_service(acceptance_tests="CA-01"))

    result = _run("TASK-001", coder, execution, tasks, _sandbox_ok())

    assert _estagio(result, "preparacao_ambiente")["status"] == "sucesso"
    assert result["overall_status"] == "sucesso"
    assert _estagio(result, "preparacao_ambiente")["evidence"]["acceptance_tests"] == {}


def test_estagio1_sem_mapa_declarado_segue_normalmente(tmp_path):
    """Fase 1 só COLETA o vínculo; a ausência dele ainda não tem consequência."""
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(coder, _manifest_service())

    result = _run("TASK-001", coder, execution, tasks, _sandbox_ok())
    estagio1 = _estagio(result, "preparacao_ambiente")

    assert estagio1["status"] == "sucesso"
    assert estagio1["evidence"]["acceptance_tests"] == {}
    assert "0/2 automatizáveis com teste declarado" in estagio1["summary"]


def test_estagio1_ignora_mapa_stale_de_outra_task(tmp_path):
    """CA-01 da task anterior não pode comprovar CA-01 da task corrente."""
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, task_id="TASK-002", criteria=_criterios_objeto())
    _write_manifest(
        coder,
        _manifest_service(
            acceptance_task_id="TASK-001",
            acceptance_tests={"CA-01": ["tests/test_task_1.py::test_antigo"]},
        ),
    )

    result = _run("TASK-002", coder, execution, tasks, _sandbox_ok())
    estagio1 = _estagio(result, "preparacao_ambiente")

    assert estagio1["status"] == "sucesso"
    assert estagio1["evidence"]["acceptance_tests"] == {}
    assert estagio1["evidence"]["acceptance_tests_task_id"] == "TASK-001"
    assert estagio1["evidence"]["acceptance_tests_escopo_valido"] is False
    assert "0/2 automatizáveis com teste declarado" in estagio1["summary"]
    # O descarte tem de aparecer no RELATÓRIO: no log do servidor ele é
    # indistinguível de "o coder não declarou vínculo nenhum".
    assert "descartado" in estagio1["summary"]
    assert "TASK-001" in estagio1["summary"]
    assert "TASK-002" in estagio1["summary"]


def test_estagio1_com_mapa_em_escopo_nao_avisa_descarte(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(coder, _manifest_service(acceptance_tests={"CA-01": ["t::a"]}))

    result = _run("TASK-001", coder, execution, tasks, _sandbox_ok())

    assert "descartado" not in _estagio(result, "preparacao_ambiente")["summary"]


def test_estagio1_ignora_mapa_sem_namespace_da_task(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(
        coder,
        _manifest_service(
            acceptance_task_id=None,
            acceptance_tests={"CA-01": ["tests/test_antigo.py::test_stale"]},
        ),
    )

    result = _run("TASK-001", coder, execution, tasks, _sandbox_ok())
    evidencia = _estagio(result, "preparacao_ambiente")["evidence"]

    assert evidencia["acceptance_tests"] == {}
    assert evidencia["acceptance_tests_escopo_valido"] is False


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


# ===========================================================================
# Estágio 6 — desfecho por teste individual (Fase 2)
# ===========================================================================

_SAIDA_VERBOSA = """\
============================= test session starts ==============================
collected 3 items

tests/test_a.py::test_passa PASSED                                       [ 33%]
tests/test_a.py::test_quebra FAILED                                      [ 66%]
tests/test_b.py::test_pula SKIPPED                                       [100%]

=========================== short test summary info ============================
FAILED tests/test_a.py::test_quebra - AssertionError: esperado 1, obtido 2
========================= 1 passed, 1 failed, 1 skipped ========================
"""


def test_estagio6_identifica_desfecho_de_cada_teste(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_manifest(coder, _manifest_service())
    sandbox = FakeSandbox(
        exec_results={"pytest": CommandResult(1, _SAIDA_VERBOSA, "", False)},
        logs_text="",
    )

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    estagio = _estagio(result, "testes_automatizados")
    testes = {t["nodeid"]: t["outcome"] for t in estagio["evidence"]["resultados"][0]["testes"]}

    assert testes == {
        "tests/test_a.py::test_passa": "passou",
        "tests/test_a.py::test_quebra": "falhou",
        "tests/test_b.py::test_pula": "pulado",
    }
    assert estagio["evidence"]["testes_identificados"] == 3


def test_estagio6_resumo_agregado_permanece_intacto(tmp_path):
    """A nota de progresso e a assinatura de erro leem `resumo` — é contrato."""
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_manifest(coder, _manifest_service())
    sandbox = FakeSandbox(
        exec_results={"pytest": CommandResult(1, _SAIDA_VERBOSA, "", False)},
        logs_text="",
    )

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    resumo = _estagio(result, "testes_automatizados")["evidence"]["resultados"][0]["resumo"]

    assert resumo == {"passaram": 1, "falharam": 1, "erros": 0, "total": 2}


def test_estagio6_sem_saida_verbosa_nao_infere_que_passou(tmp_path):
    """Suíte verde sem `-v`: nenhum teste NOMEADO, e nada é dado por comprovado."""
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_manifest(coder, _manifest_service())

    result = _run("TASK-001", coder, execution, tasks, _sandbox_ok(tests_passed=5))
    estagio = _estagio(result, "testes_automatizados")

    assert estagio["status"] == "sucesso"
    assert estagio["evidence"]["resultados"][0]["resumo"]["passaram"] == 5
    assert estagio["evidence"]["resultados"][0]["testes"] == []
    assert estagio["evidence"]["testes_identificados"] == 0


def test_estagio6_sem_verbose_ainda_capta_os_que_falharam(tmp_path):
    """O resumo final do pytest lista os que falharam mesmo sem `-v`."""
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_manifest(coder, _manifest_service())
    saida = (
        "tests/test_a.py .F\n"
        "=========================== short test summary info ===========================\n"
        "FAILED tests/test_a.py::test_quebra - AssertionError\n"
        "========================= 1 passed, 1 failed =========================\n"
    )
    sandbox = FakeSandbox(
        exec_results={"pytest": CommandResult(1, saida, "", False)}, logs_text=""
    )

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    testes = _estagio(result, "testes_automatizados")["evidence"]["resultados"][0]["testes"]

    assert testes == [{"nodeid": "tests/test_a.py::test_quebra", "outcome": "falhou"}]


def test_estagio6_desfecho_mais_severo_vence_quando_ha_duas_leituras(tmp_path):
    """Linha verbosa e resumo final discordando: nunca inflar para 'passou'."""
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_manifest(coder, _manifest_service())
    saida = (
        "tests/test_a.py::test_x PASSED\n"
        "=========================== short test summary info ===========================\n"
        "ERROR tests/test_a.py::test_x - fixture quebrou no teardown\n"
    )
    sandbox = FakeSandbox(
        exec_results={"pytest": CommandResult(1, saida, "", False)}, logs_text=""
    )

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    testes = _estagio(result, "testes_automatizados")["evidence"]["resultados"][0]["testes"]

    assert testes == [{"nodeid": "tests/test_a.py::test_x", "outcome": "erro"}]


def test_estagio6_saida_colorida_e_parseada(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks)
    _write_manifest(coder, _manifest_service())
    saida = "tests/test_a.py::test_x \x1b[32mPASSED\x1b[0m  [100%]\n1 passed in 0.01s\n"
    sandbox = FakeSandbox(
        exec_results={"pytest": CommandResult(0, saida, "", False)}, logs_text=""
    )

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    testes = _estagio(result, "testes_automatizados")["evidence"]["resultados"][0]["testes"]

    assert testes == [{"nodeid": "tests/test_a.py::test_x", "outcome": "passou"}]


# ---------------------------------------------------------------------------
# resultados_por_teste — leitura consolidada da evidência
# ---------------------------------------------------------------------------


def test_resultados_por_teste_consolida_varios_comandos():
    estagio = {
        "evidence": {
            "resultados": [
                {"testes": [{"nodeid": "t::a", "outcome": "passou"}]},
                {"testes": [{"nodeid": "t::b", "outcome": "falhou"}]},
            ]
        }
    }

    assert resultados_por_teste(estagio) == {"t::a": "passou", "t::b": "falhou"}


def test_resultados_por_teste_mantem_o_desfecho_mais_severo():
    """Mesmo teste em dois comandos: prevalece o que NÃO comprova."""
    estagio = {
        "evidence": {
            "resultados": [
                {"testes": [{"nodeid": "t::a", "outcome": "passou"}]},
                {"testes": [{"nodeid": "t::a", "outcome": "falhou"}]},
            ]
        }
    }

    assert resultados_por_teste(estagio) == {"t::a": "falhou"}


@pytest.mark.parametrize(
    "estagio",
    [
        None,
        "texto",
        {},
        {"evidence": None},
        {"evidence": {"resultados": None}},
        {"evidence": {"resultados": ["texto"]}},
        {"evidence": {"resultados": [{"testes": [{"nodeid": 7, "outcome": "passou"}]}]}},
        {"evidence": {"resultados": [{"testes": [{"nodeid": "t::a", "outcome": "xpto"}]}]}},
    ],
)
def test_resultados_por_teste_ignora_evidencia_inutilizavel(estagio):
    assert resultados_por_teste(estagio) == {}


# ===========================================================================
# Estágio 7 — resultado por critério a partir dos testes vinculados (Fase 3)
# ===========================================================================

def _sandbox_com_testes(*linhas_verbosas, exit_code=0):
    """FakeSandbox cuja suíte emite saída verbosa com os testes informados."""
    corpo = "\n".join(linhas_verbosas)
    return FakeSandbox(
        exec_results={
            "pytest": CommandResult(exit_code, f"{corpo}\n1 passed in 0.01s", "", False)
        },
        logs_text="INFO [app] serviço no ar",
    )


def _evidencia_por_id(result):
    return {e["criterion_id"]: e for e in result["criteria_evidence"]}


def test_criterio_com_teste_que_passou_permanece_nao_avaliado(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(
        coder, _manifest_service(acceptance_tests={"CA-01": ["tests/t.py::test_ok"]})
    )
    sandbox = _sandbox_com_testes("tests/t.py::test_ok PASSED  [100%]")

    ev = _evidencia_por_id(_run("TASK-001", coder, execution, tasks, sandbox))

    assert ev["CA-01"]["outcome"] == "nao_avaliado"
    assert ev["CA-01"]["linked_tests"] == ["tests/t.py::test_ok"]
    assert ev["CA-01"]["checkable"] is False
    assert "tests/t.py::test_ok → passou" in ev["CA-01"]["observed"]
    assert "não usados para avaliar semanticamente" in ev["CA-01"]["observed"]


def test_criterio_com_teste_que_falhou_permanece_nao_avaliado(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(
        coder, _manifest_service(acceptance_tests={"CA-01": ["tests/t.py::test_ko"]})
    )
    sandbox = _sandbox_com_testes("tests/t.py::test_ko FAILED  [100%]", exit_code=1)

    ev = _evidencia_por_id(_run("TASK-001", coder, execution, tasks, sandbox))

    assert ev["CA-01"]["outcome"] == "nao_avaliado"
    assert "tests/t.py::test_ko → falhou" in ev["CA-01"]["observed"]


def test_criterio_com_teste_declarado_que_nao_rodou(tmp_path):
    """Nodeid errado continua auditável, mas não avalia o critério."""
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(
        coder,
        _manifest_service(acceptance_tests={"CA-01": ["tests/t.py::test_inexistente"]}),
    )
    sandbox = _sandbox_com_testes("tests/t.py::test_outro PASSED")

    ev = _evidencia_por_id(_run("TASK-001", coder, execution, tasks, sandbox))

    assert ev["CA-01"]["outcome"] == "nao_avaliado"
    assert "Sem resultado observado" in ev["CA-01"]["observed"]


def test_criterio_automatizavel_sem_teste_declarado(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(coder, _manifest_service())

    ev = _evidencia_por_id(_run("TASK-001", coder, execution, tasks, _sandbox_ok()))

    assert ev["CA-01"]["outcome"] == "nao_avaliado"
    assert ev["CA-02"]["outcome"] == "nao_avaliado"


def test_criterio_nao_automatizavel_tambem_permanece_nao_avaliado(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(coder, _manifest_service())

    ev = _evidencia_por_id(_run("TASK-001", coder, execution, tasks, _sandbox_ok()))

    assert ev["CA-03"]["outcome"] == "nao_avaliado"
    assert ev["CA-03"]["automatable"] is False


def test_vinculo_declarado_nao_prevalece_sobre_a_politica(tmp_path):
    """Nem um vínculo explícito transforma teste técnico em aceite."""
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(
        coder, _manifest_service(acceptance_tests={"CA-03": ["tests/t.py::test_ui"]})
    )
    sandbox = _sandbox_com_testes("tests/t.py::test_ui PASSED")

    ev = _evidencia_por_id(_run("TASK-001", coder, execution, tasks, sandbox))

    assert ev["CA-03"]["outcome"] == "nao_avaliado"
    assert ev["CA-03"]["automatable"] is False


def test_cobertura_parcial_nao_avalia_o_criterio(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(
        coder,
        _manifest_service(
            acceptance_tests={"CA-01": ["tests/t.py::test_a", "tests/t.py::test_b"]}
        ),
    )
    sandbox = _sandbox_com_testes(
        "tests/t.py::test_a PASSED", "tests/t.py::test_b FAILED", exit_code=1
    )

    ev = _evidencia_por_id(_run("TASK-001", coder, execution, tasks, sandbox))

    assert ev["CA-01"]["outcome"] == "nao_avaliado"


def test_teste_pulado_nao_comprova_o_criterio(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(
        coder, _manifest_service(acceptance_tests={"CA-01": ["tests/t.py::test_skip"]})
    )
    sandbox = _sandbox_com_testes("tests/t.py::test_skip SKIPPED")

    ev = _evidencia_por_id(_run("TASK-001", coder, execution, tasks, sandbox))

    assert ev["CA-01"]["outcome"] == "nao_avaliado"


def test_estagio7_resume_a_contagem_por_resultado(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(
        coder, _manifest_service(acceptance_tests={"CA-01": ["tests/t.py::test_ok"]})
    )
    sandbox = _sandbox_com_testes("tests/t.py::test_ok PASSED")

    result = _run("TASK-001", coder, execution, tasks, sandbox)
    evidencia = _estagio(result, "validacoes_work_item")["evidence"]

    assert evidencia["total_criterios"] == 3
    assert evidencia["criterios_avaliados"] == 0
    assert evidencia["por_resultado"] == {"nao_avaliado": 3}


def test_task_no_formato_antigo_produz_evidencia_com_id_gerado(tmp_path):
    """Sem classificação declarada, o critério legado é tratado como automatizável."""
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=["Critério legado A", "Critério legado B"])
    _write_manifest(coder, _manifest_service())

    ev = _evidencia_por_id(_run("TASK-001", coder, execution, tasks, _sandbox_ok()))

    assert set(ev) == {"CA-01", "CA-02"}
    assert all(e["outcome"] == "nao_avaliado" for e in ev.values())
    assert all(e["automatable"] is True for e in ev.values())


def test_teste_ausente_nao_avalia_o_criterio(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(
        coder,
        _manifest_service(
            acceptance_tests={
                "CA-01": ["tests/t.py::test_a", "tests/t.py::test_ausente"]
            }
        ),
    )
    sandbox = _sandbox_com_testes("tests/t.py::test_a PASSED")

    ev = _evidencia_por_id(_run("TASK-001", coder, execution, tasks, sandbox))

    assert ev["CA-01"]["outcome"] == "nao_avaliado"
    assert "tests/t.py::test_ausente" in ev["CA-01"]["observed"]


def test_falha_observada_com_teste_ausente_nao_avalia_o_criterio(tmp_path):
    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(
        coder,
        _manifest_service(
            acceptance_tests={
                "CA-01": [
                    "tests/t.py::test_a",
                    "tests/t.py::test_b",
                    "tests/t.py::test_ausente",
                ]
            }
        ),
    )
    sandbox = _sandbox_com_testes(
        "tests/t.py::test_a PASSED", "tests/t.py::test_b FAILED", exit_code=1
    )

    ev = _evidencia_por_id(_run("TASK-001", coder, execution, tasks, sandbox))

    assert ev["CA-01"]["outcome"] == "nao_avaliado"


def test_criterio_nao_avaliado_nao_pede_novo_teste(tmp_path):
    """A política não cria loop para tentar converter teste em aceite."""
    from src.agents.workflow_coding_review.executor.acceptance_score import (
        calcular_nota_aceite,
    )

    coder, execution, tasks = _dirs(tmp_path)
    _write_task(tasks, criteria=_criterios_objeto())
    _write_manifest(
        coder,
        _manifest_service(
            acceptance_tests={
                "CA-01": ["tests/t.py::test_a", "tests/t.py::test_ausente"]
            }
        ),
    )
    sandbox = _sandbox_com_testes("tests/t.py::test_a PASSED")

    aceite = calcular_nota_aceite(_run("TASK-001", coder, execution, tasks, sandbox))

    assert aceite.criterios_enderecaveis == []
    assert aceite.nota is None
