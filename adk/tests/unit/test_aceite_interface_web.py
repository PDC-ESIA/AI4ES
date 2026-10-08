"""Homologação pela interface em produto web — sempre pelo navegador.

Critério de aceite é homologação. Em `web_app`, todo critério não técnico é
comprovado por `test_interface_<TASK>.py`, com Playwright contra a aplicação no
ar, partindo da página inicial. Critério técnico (`tecnico: true`) é testado,
mas nunca reprova: vira nota no relatório.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from shared.execution.sandbox import CommandResult
from shared.tools.coding_tools import aceite_independente as ai
from shared.tools.coding_tools import jornada as jn
from shared.tools.coding_tools.criterios_aceite import normalizar_criterios
from tests.unit import test_harness_execucao as th

_ARQ = ai.caminho_relativo("TASK-001")
_ARQ_UI = ai.caminho_relativo_interface("TASK-001")


@pytest.fixture
def ligada(monkeypatch):
    monkeypatch.setenv("AI4ES_ACEITE_INDEPENDENTE", "true")


# ── Critério e prompts ─────────────────────────────────────────────────────


def test_criterio_le_a_marca_de_tecnico():
    criterios = normalizar_criterios(
        [
            {"id": "CA-01", "description": "pela tela", "automatable": True},
            {"id": "CA-02", "description": "sqlite", "automatable": True, "tecnico": True},
            {"id": "CA-03", "description": "5s", "técnico": "true"},
            "formato antigo",
        ]
    )
    assert [c.tecnico for c in criterios] == [False, True, True, False]


def test_context_engineer_exige_criterio_de_interface_em_web_app():
    from src.agents.workflow_coding_review.context_engineer.prompt import instruction

    assert "PRODUTO WEB (product_type = web_app) — REGRA FIXA, VALE SEMPRE" in instruction
    assert '"tecnico": true' in instruction and "HOMOLOGAÇÃO" in instruction


@pytest.mark.parametrize(
    "produto, presente", [("web_app", True), (" Web_App ", True), ("api_service", False), (None, False)]
)
def test_coder_recebe_a_secao_de_produto_web_so_em_web_app(produto, presente):
    from src.agents.workflow_coding_review.coder.prompt import secao_produto_web

    assert ("PRODUTO WEB" in secao_produto_web(produto)) is presente


def test_secao_de_produto_web_nao_tem_chaves_para_o_templating():
    from src.agents.workflow_coding_review.coder.prompt import SECAO_PRODUTO_WEB

    assert "{" not in SECAO_PRODUTO_WEB and "}" not in SECAO_PRODUTO_WEB


# ── Mapa com dois arquivos ─────────────────────────────────────────────────


def test_mapa_mescla_arquivo_principal_e_de_interface(tmp_path):
    ai.gravar_mapa(tmp_path, "TASK-001", _ARQ, {"CA-01": [f"{_ARQ}::test_CA_01_a"]}, mesclar=True)
    ai.gravar_mapa(tmp_path, "TASK-001", _ARQ_UI, {"CA-02": [f"{_ARQ_UI}::test_CA_02_b"]}, mesclar=True)
    # Salvar de novo o de interface substitui só os testes dele.
    ai.gravar_mapa(tmp_path, "TASK-001", _ARQ_UI, {"CA-02": [f"{_ARQ_UI}::test_CA_02_c"]}, mesclar=True)

    mapa = ai.ler_mapa(tmp_path, "TASK-001")
    assert mapa["arquivo"] == _ARQ
    assert mapa["arquivos"] == [_ARQ, _ARQ_UI]
    assert mapa["por_criterio"] == {
        "CA-01": [f"{_ARQ}::test_CA_01_a"],
        "CA-02": [f"{_ARQ_UI}::test_CA_02_c"],
    }


def test_mapa_antigo_sem_lista_de_arquivos_continua_legivel(tmp_path):
    ai.caminho_mapa(tmp_path, "TASK-001").write_text(
        json.dumps({"task_id": "TASK-001", "arquivo": _ARQ, "por_criterio": {}})
    )
    assert ai.ler_mapa(tmp_path, "TASK-001")["arquivos"] == [_ARQ]


def test_falhas_aceitas_agrupadas_pelo_arquivo_de_cada_teste(tmp_path):
    ai.gravar_mapa(tmp_path, "TASK-001", _ARQ, {"CA-01": [f"{_ARQ}::a"]})
    ai.gravar_mapa(tmp_path, "TASK-001", _ARQ_UI, {"CA-02": [f"{_ARQ_UI}::b"]}, mesclar=True)
    ai.registrar_falhas_aceitas(tmp_path, "TASK-001", [f"{_ARQ_UI}::b[chromium]"])
    assert ai.falhas_aceitas_por_arquivo(tmp_path) == {
        _ARQ: set(),
        _ARQ_UI: {f"{_ARQ_UI}::b[chromium]"},
    }


def test_arquivo_de_interface_e_sempre_de_navegador():
    assert jn.usa_navegador("def test_CA_01(page): ...", _ARQ_UI) is True
    assert jn.usa_navegador("def test_CA_01(): ...", _ARQ) is False


# ── Autor de aceite ────────────────────────────────────────────────────────


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    modulo = importlib.import_module("src.agents.workflow_coding_review.acceptance.agent")
    from shared.workspace import get_agent_workspace

    coder = get_agent_workspace("cr_coder")
    (coder / "app").mkdir(parents=True, exist_ok=True)
    (coder / "run.json").write_text(
        json.dumps(
            {
                "surface": "service",
                "run": "venv/bin/python -m uvicorn app.main:app --port 8000",
                "port": 8000,
                "test": ["venv/bin/python -m pytest -v"],
            }
        )
    )
    return SimpleNamespace(modulo=modulo, coder=coder, tasks=get_agent_workspace("cr_context_engineer"))


def _tasks(produto="web_app"):
    return {
        "macro_context": {"product_type": produto, "tech_stack": ["python"]},
        "tasks": [
            {
                "id": "TASK-001",
                "description": "Ensaios",
                "acceptance_criteria": [
                    {"id": "CA-01", "description": "persiste", "automatable": True, "tecnico": True},
                    {"id": "CA-02", "description": "pela tela", "automatable": True},
                ],
            }
        ],
    }


def _ctx(produto="web_app"):
    return SimpleNamespace(state={"task_id": "TASK-001", "tasks": _tasks(produto)})


_UI_OK = '''
import re
from playwright.sync_api import Page, expect

def test_CA_02_cria_pela_tela(page: Page):
    page.goto("/")
    page.get_by_role("link", name=re.compile("novo", re.I)).click()
    expect(page.get_by_text("ok")).to_be_visible()
'''


def test_web_app_divide_criterios_entre_os_dois_arquivos(ws):
    state = _ctx().state
    task = state["tasks"]["tasks"][0]
    assert ws.modulo.dividir_criterios(state, task, ws.coder) == (["CA-01"], ["CA-02"])
    contexto = json.loads(ws.modulo.montar_aceite_task(state, task, ws.coder))
    assert contexto["interface"]["criterios"] == ["CA-02"]
    assert contexto["interface"]["arquivo"] == _ARQ_UI


def test_fora_de_web_app_nao_ha_arquivo_de_interface(ws):
    state = _ctx("api_service").state
    task = state["tasks"]["tasks"][0]
    assert ws.modulo.dividir_criterios(state, task, ws.coder) == (["CA-01", "CA-02"], [])
    assert "interface" not in json.loads(ws.modulo.montar_aceite_task(state, task, ws.coder))


def test_web_app_sem_servico_nao_tem_como_navegar(ws):
    (ws.coder / "run.json").write_text(json.dumps({"surface": "command", "run": "x", "test": ["pytest"]}))
    state = _ctx().state
    assert ws.modulo.dividir_criterios(state, state["tasks"]["tasks"][0], ws.coder)[1] == []


def test_salva_os_dois_arquivos_e_o_conftest(ws):
    principal = "def test_CA_01_persiste():\n    assert 1\n\ndef test_CA_02_tela():\n    assert 1\n"
    r1 = ws.modulo.tool_salvar_teste_aceite(principal, _ctx())
    r2 = ws.modulo.tool_salvar_teste_interface(_UI_OK, _ctx())

    assert r1["criterios_cobertos"] == ["CA-01"]  # CA-02 é homologação pela interface
    assert "tool_salvar_teste_interface" in r1["pendente"]
    assert r2["sucesso"] is True and r2["criterios_cobertos"] == ["CA-02"]
    assert (ws.coder / _ARQ_UI).read_text() == _UI_OK
    assert (ws.coder / ai.PASTA_ACEITE / "conftest.py").read_text() == jn.CONFTEST_JORNADA
    mapa = ai.ler_mapa(ws.tasks, "TASK-001")
    assert mapa["arquivos"] == [_ARQ, _ARQ_UI]
    assert set(mapa["por_criterio"]) == {"CA-01", "CA-02"}
    assert mapa["tecnicos"] == ["CA-01"]


@pytest.mark.parametrize(
    "codigo, trecho",
    [
        ("import httpx\ndef test_CA_02(page):\n    page.goto('/')\n", "httpx"),
        ("def test_CA_02(page):\n    page.goto('/ensaios/1')\n", "página inicial"),
        ("def test_CA_02(page):\n    page.goto('/')\n    page.evaluate('fetch(1)')\n", "evaluate"),
        ("def test_CA_02():\n    assert 1\n", "page"),
    ],
)
def test_interface_recusa_atalhos_que_pulam_a_tela(ws, codigo, trecho):
    resposta = ws.modulo.tool_salvar_teste_interface(codigo, _ctx())
    assert resposta["sucesso"] is False and trecho in resposta["erro"]
    assert not (ws.coder / _ARQ_UI).exists()


def test_task_so_de_interface_recusa_o_arquivo_principal(ws):
    ctx = _ctx()
    ctx.state["tasks"]["tasks"][0]["acceptance_criteria"] = [
        {"id": "CA-01", "description": "pela tela", "automatable": True}
    ]
    resposta = ws.modulo.tool_salvar_teste_aceite("def test_CA_01_x():\n    assert 1\n", ctx)
    assert resposta["sucesso"] is False and "tool_salvar_teste_interface" in resposta["erro"]


def test_gate_reinvoca_o_autor_enquanto_faltar_o_arquivo_de_interface(ws):
    state = _ctx().state
    gate = ws.modulo.gate
    ai.gravar_mapa(ws.tasks, "TASK-001", _ARQ, {"CA-01": [f"{_ARQ}::a"]})
    assert gate._mapa_completo(state, "TASK-001", ai.ler_mapa(ws.tasks, "TASK-001")) is False
    ai.gravar_mapa(ws.tasks, "TASK-001", _ARQ_UI, {"CA-02": [f"{_ARQ_UI}::b"]}, mesclar=True)
    assert gate._mapa_completo(state, "TASK-001", ai.ler_mapa(ws.tasks, "TASK-001")) is True


# ── Harness ────────────────────────────────────────────────────────────────


def _cenario(tmp_path, saida_ui: str, *, healthcheck=200):
    coder, execution, tasks = th._dirs(tmp_path)
    th._write_task(
        tasks,
        criteria=[
            {"id": "CA-01", "description": "persiste", "automatable": True, "tecnico": True},
            {"id": "CA-02", "description": "pela tela", "automatable": True},
        ],
    )
    th._write_macro(tasks, "web_app")
    th._write_manifest(coder, th._manifest_service(test=["venv/bin/python -m pytest -v tests/test_meu.py"]))
    (coder / ai.PASTA_ACEITE).mkdir(parents=True)
    (coder / _ARQ).write_text("def test_CA_01_a():\n    pass\n")
    (coder / _ARQ_UI).write_text(_UI_OK)
    ai.gravar_mapa(tasks, "TASK-001", _ARQ, {"CA-01": [f"{_ARQ}::test_CA_01_a"]})
    ai.gravar_mapa(
        tasks, "TASK-001", _ARQ_UI, {"CA-02": [f"{_ARQ_UI}::test_CA_02_cria_pela_tela"]},
        mesclar=True, tecnicos=["CA-01"],
    )
    sandbox = th.FakeSandbox(
        exec_results={
            _ARQ_UI: CommandResult(exit_code=1, stdout=saida_ui, stderr=""),
            _ARQ: CommandResult(exit_code=0, stdout=f"{_ARQ}::test_CA_01_a PASSED\n1 passed", stderr=""),
            "pytest": CommandResult(exit_code=0, stdout="1 passed", stderr=""),
        }
    )
    relatorio = th._run(
        "TASK-001", coder, execution, tasks, sandbox, response=th._mock_response(healthcheck)
    )
    return relatorio, sandbox


def test_harness_roda_a_interface_contra_o_servico_e_casa_o_nodeid_do_navegador(ligada, tmp_path):
    saida = f"{_ARQ_UI}::test_CA_02_cria_pela_tela[chromium] FAILED\n1 failed"
    relatorio, sandbox = _cenario(tmp_path, saida)

    assert any("playwright install chromium" in c for c in sandbox.exec_calls)
    por_id = {e["criterion_id"]: e for e in relatorio["criteria_evidence"]}
    assert por_id["CA-01"]["outcome"] == "atendido"
    assert por_id["CA-02"]["outcome"] == "nao_atendido"


def test_harness_sem_aplicacao_no_ar_nao_executa_a_interface(ligada, tmp_path):
    relatorio, sandbox = _cenario(tmp_path, "", healthcheck=500)
    assert not any(c.endswith(_ARQ_UI) for c in sandbox.exec_calls)
    por_id = {e["criterion_id"]: e for e in relatorio["criteria_evidence"]}
    assert por_id["CA-02"]["outcome"] == "teste_nao_executado"


def test_linha_de_base_casa_o_nodeid_parametrizado(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import get_agent_workspace
    from src.agents.workflow_coding_review.task_iterator import fechar_linha_de_base

    tasks = get_agent_workspace("cr_context_engineer")
    ai.gravar_mapa(tasks, "TASK-001", _ARQ_UI, {"CA-02": [f"{_ARQ_UI}::t"]})
    relatorio = tmp_path / "r.json"
    relatorio.write_text(json.dumps({"stages": [{"stage": "testes_automatizados", "evidence": {
        "resultados": [{"testes": [{"nodeid": f"{_ARQ_UI}::t[chromium]", "outcome": "falhou"}]}]}}]}))
    fechar_linha_de_base("TASK-001", str(relatorio))
    assert ai.ler_mapa(tasks, "TASK-001")["falhas_aceitas"] == [f"{_ARQ_UI}::t[chromium]"]


# ── conftest ───────────────────────────────────────────────────────────────


def test_conftest_nao_afeta_testes_sem_navegador(tmp_path):
    """Na pasta de aceite convivem os testes do TestClient: sem `page`, nada de
    `base_url` (que pularia o teste sem a URL do produto)."""
    jn.instalar_conftest(tmp_path, ai.PASTA_ACEITE)
    (tmp_path / ai.PASTA_ACEITE / "test_x.py").write_text("def test_ok():\n    assert 1\n")
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", ai.PASTA_ACEITE],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert "1 passed" in res.stdout, res.stdout + res.stderr


# ── Técnico nunca reprova: vira nota ───────────────────────────────────────


def test_falha_so_em_teste_tecnico_nao_reprova_a_suite(ligada, tmp_path):
    coder, execution, tasks = th._dirs(tmp_path)
    th._write_task(tasks, criteria=[
        {"id": "CA-01", "description": "sqlite", "automatable": True, "tecnico": True},
        {"id": "CA-02", "description": "outro", "automatable": True},
    ])
    th._write_manifest(coder, th._manifest_command(test=["venv/bin/python -m pytest -v tests/t.py"]))
    (coder / ai.PASTA_ACEITE).mkdir(parents=True)
    (coder / _ARQ).write_text("def test_CA_01_a():\n    pass\n")
    ai.gravar_mapa(tasks, "TASK-001", _ARQ,
                   {"CA-01": [f"{_ARQ}::test_CA_01_a"], "CA-02": [f"{_ARQ}::test_CA_02_b"]},
                   tecnicos=["CA-01"])

    def _rodar(falha_b: bool):
        saida = f"{_ARQ}::test_CA_01_a FAILED\n{_ARQ}::test_CA_02_b {'FAILED' if falha_b else 'PASSED'}\n"
        sandbox = th.FakeSandbox(exec_results={
            _ARQ: CommandResult(exit_code=1, stdout=saida, stderr=""),
            "pytest": CommandResult(exit_code=0, stdout="1 passed", stderr=""),
        })
        return th._run("TASK-001", coder, execution, tasks, sandbox)

    from src.agents.workflow_coding_review.executor.loop_policy import protegidos_falharam

    so_tecnico = _rodar(False)
    testes = next(s for s in so_tecnico["stages"] if s["stage"] == "testes_automatizados")
    assert testes["status"] == "sucesso"
    assert protegidos_falharam(so_tecnico) is False
    por_id = {e["criterion_id"]: e for e in so_tecnico["criteria_evidence"]}
    assert por_id["CA-01"]["outcome"] == "nao_atendido" and por_id["CA-01"]["tecnico"] is True

    homologacao = _rodar(True)
    testes = next(s for s in homologacao["stages"] if s["stage"] == "testes_automatizados")
    assert testes["status"] == "falha"
    assert protegidos_falharam(homologacao) is True


def _report_tecnico():
    return {
        "work_item_id": "TASK-001",
        "overall_status": "sucesso",
        "stages": [],
        "criteria_evidence": [
            {"criterion": "pela tela", "criterion_id": "CA-01", "outcome": "atendido",
             "observed": "", "check_performed": "", "checkable": True},
            {"criterion": "sqlite", "criterion_id": "CA-02", "outcome": "nao_atendido", "tecnico": True,
             "observed": "id repetido", "check_performed": "", "checkable": True},
        ],
    }


def test_validador_aprova_com_tecnico_nao_atendido_e_registra_nota(ligada):
    from src.agents.implementation_validator.agent import montar_veredito
    from src.agents.implementation_validator.schemas import VerdictStatus

    veredito = montar_veredito(_report_tecnico())
    assert veredito.status == VerdictStatus.APROVADO
    assert "Notas técnicas (não bloqueiam): CA-02: nao_atendido" in veredito.summary


def test_nota_de_aceite_exclui_tecnico_e_lista_a_nota():
    from src.agents.workflow_coding_review.executor.acceptance_score import calcular_nota_aceite

    nota = calcular_nota_aceite(_report_tecnico())
    assert (nota.total, nota.atendidos, nota.nao_atendidos, nota.nota) == (1, 1, 0, 1.0)
    assert nota.como_dict()["notas_tecnicas"] == [
        {"id": "CA-02", "criterio": "sqlite", "resultado": "nao_atendido", "observado": "id repetido"}
    ]


def test_manifesto_publica_as_notas_tecnicas():
    from src.agents.workflow_coding_review.executor.acceptance_score import calcular_nota_aceite
    from src.agents.workflow_coding_review import manifest

    aceite = calcular_nota_aceite(_report_tecnico()).como_dict()
    bloco = manifest.resumo_de_aceite({"task_results": {"TASK-001": {"aceite": aceite, "criterios_esperados": 1}}})
    assert bloco["criterios_nao_atendidos"] == 0
    assert bloco["notas_tecnicas"][0]["task_id"] == "TASK-001"


# ── Context engineer: task web sem homologação é recusada ──────────────────


@pytest.fixture
def ce(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.tools.coding_tools import context_engineer_tools as cet

    return cet


def _task(criterios, **extra):
    return json.dumps({"id": "TASK-002", "acceptance_criteria": criterios, **extra})


_SO_TECNICO = [{"id": "CA-01", "description": "POST /upload retorna 202", "automatable": True, "tecnico": True}]


def test_task_web_sem_criterio_de_homologacao_e_recusada(ce):
    ce.tool_salvar_macro_context_cr(json.dumps({"product_type": "web_app"}))
    resposta = ce.tool_salvar_task_cr("TASK-002", _task(_SO_TECNICO))
    assert resposta["sucesso"] is False and "homologação" in resposta["erro"]

    com_tela = _SO_TECNICO + [{"id": "CA-02", "description": "A partir da página inicial, enviar fotos"}]
    assert ce.tool_salvar_task_cr("TASK-002", _task(com_tela))["sucesso"] is True
    assert ce.tool_salvar_task_cr("TASK-002", _task(_SO_TECNICO, tecnica=True))["sucesso"] is True


@pytest.mark.parametrize("macro", [{"product_type": "api_service"}, None])
def test_fora_de_web_app_ou_sem_macro_nao_ha_trava(ce, macro):
    if macro:
        ce.tool_salvar_macro_context_cr(json.dumps(macro))
    assert ce.tool_salvar_task_cr("TASK-002", _task(_SO_TECNICO))["sucesso"] is True


def test_prompts_exigem_identificador_unico_listas_e_ordem():
    from src.agents.workflow_coding_review.acceptance.prompt import instruction
    from src.agents.workflow_coding_review.coder.prompt import SECAO_PRODUTO_WEB

    assert "get_by_test_id" in instruction and "IDENTIFICADOR ÚNICO" in instruction
    assert "filter(has_text=" in instruction and "`.nth(i)`" in instruction
    assert "só afirme ordem quando o critério pedir" in instruction
    assert 'data-testid="item-ensaio"' in SECAO_PRODUTO_WEB


# ── Robustez dos testes de interface (11ª validação) ───────────────────────

import ast  # noqa: E402


@pytest.mark.parametrize(
    "trecho_codigo, trecho_erro",
    [
        ("expect(fotos).to_have_count(lambda c: c >= 1)", "nunca função"),
        ("expect(item).to_have_text(lambda t: 'x' in t)", "nunca função"),
        ("page.get_by_test_id('item-foto').first.click()", "`.first`"),
        ("page.get_by_test_id('item-foto').nth(2).click()", "`.nth(...)`"),
        ("page.locator('button.btn-upload').click()", "classe CSS"),
        ("try:\n        page.get_by_test_id('a').click()\n    except Exception:\n        pass", "try/except"),
        ("if page.get_by_test_id('a').count() > 0:\n        page.get_by_test_id('a').click()", "não ramifique"),
    ],
)
def test_robustez_recusa_padroes_frageis(trecho_codigo, trecho_erro):
    codigo = f"def test_CA_01(page):\n    page.goto('/')\n    {trecho_codigo}\n"
    assert any(trecho_erro in v for v in jn.violacoes_de_robustez(ast.parse(codigo)))


def test_robustez_aceita_o_exemplo_do_prompt_e_campo_de_arquivo():
    codigo = (
        "def test_CA_01(page):\n"
        "    page.goto('/')\n"
        "    item = page.get_by_test_id('item-ensaio').filter(has_text='x')\n"
        "    item.locator('input[type=file]').set_input_files([])\n"
        "    expect(item.get_by_test_id('item-foto')).to_have_count(3)\n"
        "    expect(item).to_have_text(['a.png', 'b.png'])\n"
    )
    assert jn.violacoes_de_robustez(ast.parse(codigo)) == []


def test_interface_com_lambda_e_recusada_ao_salvar(ws):
    codigo = _UI_OK.replace(
        'expect(page.get_by_text("ok")).to_be_visible()',
        'expect(page.get_by_test_id("item")).to_have_count(lambda c: c > 0)',
    )
    resposta = ws.modulo.tool_salvar_teste_interface(codigo, _ctx())
    assert resposta["sucesso"] is False and "nunca função" in resposta["erro"]


def test_inventario_de_identificadores_das_telas_e_dos_testes(tmp_path):
    (tmp_path / "app" / "templates").mkdir(parents=True)
    (tmp_path / "app" / "templates" / "g.html").write_text(
        '<ul data-testid="galeria-ensaio"><li data-testid="item-foto-{{ f.id }}"></li></ul>'
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "t.py").write_text('page.get_by_test_id("form-novo-ensaio")')
    (tmp_path / "venv").mkdir()
    (tmp_path / "venv" / "x.html").write_text('<a data-testid="nao-conta">')
    assert jn.identificadores_existentes(tmp_path) == ["form-novo-ensaio", "galeria-ensaio"]


@pytest.mark.parametrize(
    "saida, do_teste",
    [
        ("E   playwright._impl._errors.Error: value must be a string or regular expression", True),
        ("E   TypeError: 'Locator' object is not callable", True),
        ("E   fixture 'pagina' not found", True),
        ("E   playwright._impl._errors.TimeoutError: Locator.click: Timeout 30000ms exceeded.", False),
        ("E   AssertionError: Locator expected to be visible", False),
    ],
)
def test_classifica_erro_do_proprio_teste(saida, do_teste):
    assert jn.erro_do_proprio_teste(saida) is do_teste


def test_web_app_manda_homologacao_ao_autor_mesmo_nao_automatizavel(ws):
    state = _ctx().state
    task = state["tasks"]["tasks"][0]
    task["acceptance_criteria"].append({"id": "CA-03", "description": "upload pela tela", "automatable": False})
    assert ws.modulo.dividir_criterios(state, task, ws.coder) == (["CA-01"], ["CA-02", "CA-03"])


def _relatorio_de_reparo(tmp_path, saida, *, iteracao=2, task="TASK-001"):
    caminho = tmp_path / "r.json"
    caminho.write_text(json.dumps({
        "work_item_id": task, "iteration": iteracao,
        "stages": [{"stage": "testes_automatizados", "evidence": {"resultados": [
            {"comando": f"venv/bin/python -m pytest -v {_ARQ_UI}", "exit_code": 1, "saida_tail": saida,
             "aceite_independente": True},
        ]}}],
    }))
    return str(caminho)


def test_gate_devolve_ao_autor_o_teste_com_erro_proprio(ws, tmp_path):
    gate = ws.modulo.gate
    mapa = {"arquivos": [_ARQ, _ARQ_UI]}
    erro = "E   playwright._impl._errors.Error: value must be a string or regular expression"
    state = {"report_path": _relatorio_de_reparo(tmp_path, erro)}

    reparo = gate._reparo_pendente(state, "TASK-001", mapa)
    assert reparo["arquivo"] == _ARQ_UI and reparo["iteracao"] == 2

    # Mesma rodada não é reparada duas vezes; e há teto por task.
    assert gate._reparo_pendente({**state, "aceite_reparos": {"TASK-001": [2]}}, "TASK-001", mapa) is None
    assert gate._reparo_pendente({**state, "aceite_reparos": {"TASK-001": [1, 3]}}, "TASK-001", mapa) is None


def test_gate_nao_repara_falha_do_produto_nem_relatorio_de_outra_task(ws, tmp_path):
    gate = ws.modulo.gate
    mapa = {"arquivos": [_ARQ_UI]}
    produto = {"report_path": _relatorio_de_reparo(tmp_path, "E   AssertionError: expected visible")}
    assert gate._reparo_pendente(produto, "TASK-001", mapa) is None
    outra = {"report_path": _relatorio_de_reparo(tmp_path, "E   TypeError: x", task="TASK-002")}
    assert gate._reparo_pendente(outra, "TASK-001", mapa) is None


@pytest.mark.asyncio
async def test_gate_invoca_o_autor_em_modo_reparo_mesmo_com_mapa_completo(ws, ligada, tmp_path):
    from tests.unit.test_aceite_independente import _rodar_gate

    ai.gravar_mapa(ws.tasks, "TASK-001", _ARQ, {"CA-01": [f"{_ARQ}::a"]})
    ai.gravar_mapa(ws.tasks, "TASK-001", _ARQ_UI, {"CA-02": [f"{_ARQ_UI}::b"]}, mesclar=True)
    erro = "E   playwright._impl._errors.Error: value must be a string or regular expression"
    estado = {**_ctx().state, "report_path": _relatorio_de_reparo(tmp_path, erro)}

    chamadas, final = await _rodar_gate(ws.modulo, estado)
    assert len(chamadas) == 1
    assert json.loads(chamadas[0])["reparo"]["arquivo"] == _ARQ_UI
    assert final["aceite_reparos"] == {"TASK-001": [2]}
    assert "aceite_tentativas" not in final  # reparo não gasta tentativa de autoria

    # A mesma rodada não dispara outro reparo.
    chamadas, _ = await _rodar_gate(ws.modulo, {**estado, "aceite_reparos": {"TASK-001": [2]}})
    assert chamadas == []


# ── Helpers determinísticos, convenção de id, suíte do coder (12ª validação) ─


def test_helpers_do_conftest_geram_dados_unicos_e_imagens_validas(tmp_path):
    jn.instalar_conftest(tmp_path, ai.PASTA_ACEITE)
    (tmp_path / ai.PASTA_ACEITE / "test_h.py").write_text(
        "def test_helpers(nome_unico, imagens):\n"
        "    a, b = nome_unico('Ensaio'), nome_unico('Ensaio')\n"
        "    assert a != b and a.startswith('Ensaio ')\n"
        "    pngs = imagens(3, 'png', (10, 8))\n"
        "    assert len(pngs) == 3 and len({p.read_bytes() for p in pngs}) == 3\n"
        "    assert all(p.read_bytes().startswith(b'\\x89PNG') for p in pngs)\n"
    )
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", ai.PASTA_ACEITE],
        cwd=tmp_path, capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"},
    )
    assert "1 passed" in res.stdout, res.stdout + res.stderr


def test_png_do_helper_abre_no_pillow(tmp_path):
    pil = pytest.importorskip("PIL.Image")
    ns: dict = {}
    codigo = jn.CONFTEST_JORNADA
    exec(compile(codigo, "conftest", "exec"), ns)  # noqa: S102 — texto do próprio pipeline
    (tmp_path / "x.png").write_bytes(ns["_png"](12, 7, (1, 2, 3)))
    with pil.open(tmp_path / "x.png") as img:
        assert img.size == (12, 7) and img.getpixel((0, 0)) == (1, 2, 3)


def test_salvar_o_arquivo_principal_instala_os_helpers(ws):
    ws.modulo.tool_salvar_teste_aceite("def test_CA_01_x():\n    assert 1\n", _ctx("api_service"))
    assert (ws.coder / ai.PASTA_ACEITE / "conftest.py").read_text() == jn.CONFTEST_JORNADA


def test_trilha_web_fixa_o_helper_de_identificador():
    from shared.execution.trilhas import TRILHAS

    web = next(t for t in TRILHAS if t.id == "python-web")
    notas = web.notas.format(python=web.python)
    assert "app/ids.py" in notas and "str(uuid.uuid4())" in notas


def test_prompt_proibe_exigir_formato_nao_pedido():
    from src.agents.workflow_coding_review.acceptance.prompt import instruction

    assert "Não exija FORMATO que o critério não especifica" in instruction
    assert "nome_unico" in instruction and "imagens(" in instruction


def _cenario_suite(tmp_path, *, com_mapa: bool):
    coder, execution, tasks = th._dirs(tmp_path)
    th._write_task(tasks, criteria=[{"id": "CA-01", "description": "pela tela", "automatable": True}])
    th._write_manifest(coder, th._manifest_command(test=["venv/bin/python -m pytest -v tests/t.py"]))
    (coder / ai.PASTA_ACEITE).mkdir(parents=True)
    (coder / _ARQ).write_text("def test_CA_01_a():\n    pass\n")
    if com_mapa:
        ai.gravar_mapa(tasks, "TASK-001", _ARQ, {"CA-01": [f"{_ARQ}::test_CA_01_a"]})
    sandbox = th.FakeSandbox(exec_results={
        _ARQ: CommandResult(exit_code=0, stdout=f"{_ARQ}::test_CA_01_a PASSED\n1 passed", stderr=""),
        "tests/t.py": CommandResult(exit_code=1, stdout="tests/t.py::test_prazo FAILED\n1 failed", stderr=""),
    })
    return th._run("TASK-001", coder, execution, tasks, sandbox)


def test_suite_do_coder_vira_nota_com_homologacao_decidida(ligada, tmp_path):
    from src.agents.implementation_validator.agent import montar_veredito
    from src.agents.implementation_validator.schemas import VerdictStatus

    relatorio = _cenario_suite(tmp_path, com_mapa=True)
    testes = next(s for s in relatorio["stages"] if s["stage"] == "testes_automatizados")
    assert testes["status"] == "sucesso"
    veredito = montar_veredito(relatorio)
    assert veredito.status == VerdictStatus.APROVADO
    assert "suíte do coder com falha (1 falharam" in veredito.summary


def test_sem_mapa_a_suite_do_coder_continua_reprovando(ligada, tmp_path):
    relatorio = _cenario_suite(tmp_path, com_mapa=False)
    testes = next(s for s in relatorio["stages"] if s["stage"] == "testes_automatizados")
    assert testes["status"] == "falha"


# ── Técnico é anotado: não chega ao coder como coisa a corrigir ────────────


def test_error_report_tira_o_tecnico_do_que_o_coder_corrige(monkeypatch):
    from src.agents.workflow_coding_review.executor import agent as executor

    relatorio = {
        "work_item_id": "TASK-002", "iteration": 3,
        "criteria_evidence": [
            {"criterion": "pela tela", "criterion_id": "CA-01", "outcome": "nao_atendido"},
            {"criterion": "sqlite", "criterion_id": "CA-02", "outcome": "nao_atendido", "tecnico": True},
        ],
        "stages": [{"stage": "testes_automatizados", "status": "falha", "evidence": {"resultados": [
            {"comando": "pytest tests/test_upload.py", "exit_code": 1, "nao_bloqueante": True,
             "resumo": {"falharam": 1, "erros": 0}, "saida_tail": "test_upload_50_images FAILED"},
            {"comando": f"pytest {_ARQ_UI}", "exit_code": 1, "resumo": {"falharam": 1, "erros": 0},
             "saida_tail": "test_CA_01 FAILED: botão não encontrado"},
            {"comando": f"pytest {_ARQ}", "exit_code": 0, "saida_tail": "1 passed"},
        ], "saida_tail": "tudo"}}],
    }
    monkeypatch.setattr(executor, "_carregar_execution_report", lambda _c: relatorio)
    estado = {
        "validation": {
            "status": "reprovado", "work_item_id": "TASK-002", "blocking_reason": "x",
            "criteria_verdicts": [
                {"criterion": "pela tela", "status": "nao_atendido"},
                {"criterion": "sqlite", "status": "nao_atendido"},
            ],
        },
    }
    executor.montar_error_report(SimpleNamespace(state=estado))
    relatorio_coder = estado["error_report"]
    assert [c["criterion"] for c in relatorio_coder["failed_criteria"]] == ["pela tela"]
    resultados = relatorio_coder["failed_stages"][0]["evidence"]["resultados"]
    assert [r["comando"] for r in resultados] == [f"pytest {_ARQ_UI}"]
    assert "test_upload_50_images" not in relatorio_coder["failed_stages"][0]["evidence"]["saida_tail"]
    assert any("tests/test_upload.py" in n for n in relatorio_coder["notas_tecnicas"])
    assert any("CA-02" in n for n in relatorio_coder["notas_tecnicas"])


def test_coder_e_instruido_a_nao_corrigir_notas_tecnicas():
    from src.agents.workflow_coding_review.coder.prompt import instruction

    assert "`notas_tecnicas`" in instruction and "NÃO gaste a rodada com elas" in instruction


def test_reparo_ignora_o_arquivo_rodado_pela_suite_do_coder(ws, tmp_path):
    caminho = tmp_path / "r.json"
    caminho.write_text(json.dumps({
        "work_item_id": "TASK-001", "iteration": 1,
        "stages": [{"stage": "testes_automatizados", "evidence": {"resultados": [
            {"comando": f"pytest --ignore=tests/acceptance {_ARQ_UI}", "exit_code": 1, "nao_bloqueante": True,
             "saida_tail": "E       fixture 'page' not found"},
        ]}}],
    }))
    assert ws.modulo.gate._reparo_pendente({"report_path": str(caminho)}, "TASK-001", {"arquivos": [_ARQ_UI]}) is None


def test_rodada_com_erro_do_proprio_teste_nao_conta_para_o_teto(ws, ligada, tmp_path, monkeypatch):
    from src.agents.workflow_coding_review.executor import agent as executor

    ai.gravar_mapa(ws.tasks, "TASK-001", _ARQ_UI, {"CA-02": [f"{_ARQ_UI}::b"]})
    erro = "E   AttributeError: 'PosixPath' object has no attribute 'split'"
    state = {"task_id": "TASK-001", "report_path": _relatorio_de_reparo(tmp_path, erro)}
    assert executor._teste_a_reparar(state) is True

    produto = {"task_id": "TASK-001", "report_path": _relatorio_de_reparo(tmp_path, "E   TimeoutError: x")}
    assert executor._teste_a_reparar(produto) is False
    esgotado = {**state, "aceite_reparos": {"TASK-001": [7, 8]}}
    assert executor._teste_a_reparar(esgotado) is False
