"""Contrato de interface de produto web (`AI4ES_CONTRATO_WEB`): top-down.

web_app em qualquer stack: contrato, prompt, testes presos aos identificadores
do contrato e identificadores ausentes no ErrorReport. Trilha python-web:
esqueleto (`app/ids.py`) e conferência de rotas no quadro.
"""

from __future__ import annotations

import asyncio
import importlib
import json
from types import SimpleNamespace

import pytest

from shared.tools.coding_tools import aceite_independente as ai
from shared.tools.coding_tools import contrato_web as cw

_CONTRATO = {
    "telas": [
        {
            "id": "painel",
            "titulo": "Painel",
            "rota": "/",
            "prototipo": "design/prototypes/painel_fotografo.html",
            "tasks": ["TASK-001"],
            "elementos": [
                {"testid": "tela-painel", "papel": "tela"},
                {"testid": "form-criar-ensaio", "papel": "form", "task": "TASK-001"},
                {"testid": "campo-titulo-ensaio", "papel": "campo", "task": "TASK-001"},
                {"testid": "btn-criar-ensaio", "papel": "botao", "task": "TASK-001"},
                {"testid": "item-ensaio", "papel": "item", "task": "TASK-001"},
                {"testid": "link-galeria-ensaio", "papel": "link", "task": "TASK-002"},
            ],
        },
        {
            "id": "galeria",
            "rota": "/ensaios/{ensaio_id}",
            "tasks": ["TASK-002"],
            "elementos": [
                {"testid": "tela-galeria", "papel": "tela"},
                {"testid": "btn-enviar-fotos", "papel": "botao", "task": "TASK-002"},
                {"testid": "link-voltar-painel", "papel": "link", "task": "TASK-002"},
            ],
        },
    ],
    "rotas": [
        {"metodo": "POST", "caminho": "/ensaios", "formato": "form", "campos": ["titulo"], "task": "TASK-001"},
        {"metodo": "POST", "caminho": "/ensaios/{ensaio_id}/upload", "formato": "multipart", "task": "TASK-002"},
    ],
    "navegacao": [
        {"origem": "painel", "acao": "abrir o ensaio", "elemento": "link-galeria-ensaio",
         "dentro_de": "item-ensaio", "destino": "galeria"},
        {"origem": "galeria", "acao": "voltar", "elemento": "link-voltar-painel", "destino": "painel"},
    ],
    "estilo": {"origem": "design/prototypes/global.css", "url": "/static/global.css"},
    "decisoes": ["ingestão assíncrona"],
    "suposicoes": ["cliente é texto livre"],
    "convencoes": ["UUID com hífens"],
}


# ── Validação ──────────────────────────────────────────────────────────────


def test_contrato_valido():
    contrato, erros = cw.validar(_CONTRATO, ["TASK-001", "TASK-002"])
    assert erros == [] and contrato is not None
    assert cw.testids(contrato) == [
        "tela-painel", "form-criar-ensaio", "campo-titulo-ensaio", "btn-criar-ensaio", "item-ensaio",
        "link-galeria-ensaio", "tela-galeria", "btn-enviar-fotos", "link-voltar-painel",
    ]


@pytest.mark.parametrize(
    "mutacao, trecho",
    [
        (lambda c: c["telas"][1]["elementos"].append({"testid": "btn-criar-ensaio", "papel": "botao"}), "repetido"),
        (lambda c: c["telas"][1]["elementos"].append({"testid": "input-titulo-ensaios", "papel": "campo"}), "equivale a `campo-titulo-ensaio`"),
        (lambda c: c["telas"][1]["elementos"].append({"testid": "BtnX", "papel": "botao"}), "kebab-case"),
        (lambda c: c["rotas"].append({"metodo": "POST", "caminho": "/ensaios", "formato": "form"}), "repetida"),
        (lambda c: c["rotas"].append({"metodo": "POST", "caminho": "/x", "formato": "xml"}), "formato"),
        (lambda c: c["telas"][0].update(rota="/painel"), "tela inicial"),
        (lambda c: c["telas"][0]["tasks"].append("TASK-099"), "task desconhecida"),
        (lambda c: c["telas"][1]["elementos"].pop(0), "falta o elemento `tela-galeria`"),
        (lambda c: c["navegacao"].append({"origem": "painel", "elemento": "btn-x", "destino": "galeria"}), "não é elemento da tela painel"),
        (lambda c: c["navegacao"].append({"origem": "painel", "elemento": "btn-criar-ensaio", "destino": "nada"}), "tela inexistente"),
    ],
)
def test_contrato_invalido(mutacao, trecho):
    dados = json.loads(json.dumps(_CONTRATO))
    mutacao(dados)
    contrato, erros = cw.validar(dados, ["TASK-001", "TASK-002"])
    assert contrato is None and any(trecho in e for e in erros), erros


def test_grava_e_le(tmp_path):
    contrato, _ = cw.validar(_CONTRATO)
    cw.gravar(tmp_path, contrato)
    assert cw.ler(tmp_path) == contrato
    assert cw.ler(tmp_path / "nada") is None


# ── Prompt ─────────────────────────────────────────────────────────────────


def test_secao_detalha_so_as_telas_da_task():
    contrato, _ = cw.validar(_CONTRATO)
    texto = cw.secao_prompt(contrato, "TASK-001")
    assert "CONTRATO DE INTERFACE" in texto
    assert "`campo-titulo-ensaio` (campo)" in texto  # tela da task: detalhada
    assert "`btn-enviar-fotos`" not in texto  # outra tela: só o cabeçalho
    assert "- Tela `painel` em GET /" in texto
    assert "POST /ensaios/{ensaio_id}/upload (multipart) [TASK-002]" in texto
    assert cw.secao_prompt(None, "TASK-001") == ""


# ── Checagens determinísticas ──────────────────────────────────────────────


def test_identificadores_ausentes_qualquer_stack(tmp_path):
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "a.html").write_text('<form data-testid="form-criar-ensaio"><button>Ok</button></form>')
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "App.jsx").write_text('<li data-testid={"item-ensaio"}></li>')
    (tmp_path / ai.PASTA_ACEITE).mkdir(parents=True)
    teste = f"{ai.PASTA_ACEITE}/test_interface_TASK_001.py"
    (tmp_path / teste).write_text(
        'page.get_by_test_id("form-criar-ensaio"); page.get_by_test_id("item-ensaio");'
        ' page.get_by_test_id("btn-criar-ensaio")'
    )
    # Um id que só aparece em teste não conta como presente no produto.
    (tmp_path / "tests" / "outro.py").write_text('x = \'data-testid="btn-criar-ensaio"\'')
    assert cw.identificadores_ausentes(tmp_path, [teste]) == ["btn-criar-ensaio"]


def test_rotas_divergentes():
    contrato, _ = cw.validar(_CONTRATO)
    no_codigo = [("GET", "/"), ("POST", "/ensaios"), ("GET", "/ensaios/{ensaio_uuid}")]
    assert cw.rotas_divergentes(contrato, no_codigo) == ["POST /ensaios/{ensaio_id}/upload [TASK-002]"]


def test_esqueleto_python_web_nao_sobrescreve(tmp_path):
    assert cw.instalar_esqueleto_python_web(tmp_path) == ["app/__init__.py", "app/ids.py"]
    assert "str(uuid.uuid4())" in (tmp_path / "app" / "ids.py").read_text()
    (tmp_path / "app" / "ids.py").write_text("# do coder\n")
    assert cw.instalar_esqueleto_python_web(tmp_path) == []
    assert (tmp_path / "app" / "ids.py").read_text() == "# do coder\n"


# ── Agentes ────────────────────────────────────────────────────────────────


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    monkeypatch.setenv("AI4ES_CONTRATO_WEB", "true")
    from shared.workspace import get_agent_workspace

    return SimpleNamespace(tasks=get_agent_workspace("cr_context_engineer"), coder=get_agent_workspace("cr_coder"))


def _state():
    return {
        "task_id": "TASK-001",
        "tasks": {
            "macro_context": {"product_type": "web_app"},
            "tasks": [
                {"id": "TASK-001", "description": "x", "acceptance_criteria": [{"id": "CA-01", "description": "tela"}]},
                {"id": "TASK-002", "description": "y", "acceptance_criteria": []},
            ],
        },
    }


def test_ferramenta_do_autor_valida_e_grava(ws):
    from src.agents.workflow_coding_review.contract.agent import tool_salvar_contrato_web

    ctx = SimpleNamespace(state=_state())
    ruim = tool_salvar_contrato_web(json.dumps({"telas": []}), ctx)
    assert ruim["sucesso"] is False and any("tela inicial" in e for e in ruim["erros"])
    ok = tool_salvar_contrato_web(json.dumps(_CONTRATO), ctx)
    assert ok == {"sucesso": True, "telas": 2, "elementos": 9, "rotas": 2}
    assert cw.ler(ws.tasks) is not None


def test_coder_recebe_o_contrato_fora_do_templating(ws, monkeypatch):
    contrato, _ = cw.validar(_CONTRATO)
    cw.gravar(ws.tasks, contrato)
    cr_coder = importlib.import_module("src.agents.workflow_coding_review.coder.agent")

    async def _injecao_estrita(texto, _ctx):
        assert "{ensaio_id}" not in texto, "o contrato passou pelo templating"
        return texto

    monkeypatch.setattr("google.adk.utils.instructions_utils.inject_session_state", _injecao_estrita)
    texto = asyncio.run(cr_coder._INSTRUCTION(SimpleNamespace(state={"task_id": "TASK-002"})))
    assert texto.startswith("# CONTRATO DE INTERFACE DO PRODUTO")
    assert "`btn-enviar-fotos`" in texto


def test_teste_de_interface_fica_preso_aos_ids_do_contrato(ws):
    modulo = importlib.import_module("src.agents.workflow_coding_review.acceptance.agent")
    (ws.coder / "run.json").write_text(json.dumps(
        {"surface": "service", "run": "x", "port": 8000, "test": ["venv/bin/python -m pytest -v"]}
    ))
    contrato, _ = cw.validar(_CONTRATO)
    cw.gravar(ws.tasks, contrato)
    ctx = SimpleNamespace(state=_state())
    fora = "def test_CA_01_x(page):\n    page.goto('/')\n    page.get_by_test_id('btn-salvar').click()\n"
    resposta = modulo.tool_salvar_teste_interface(fora, ctx)
    assert resposta["sucesso"] is False and "fora do contrato" in resposta["erro"]
    dentro = fora.replace("btn-salvar", "btn-criar-ensaio")
    assert modulo.tool_salvar_teste_interface(dentro, ctx)["sucesso"] is True
    contexto = json.loads(modulo.montar_aceite_task(ctx.state, ctx.state["tasks"]["tasks"][0], ws.coder))
    assert "CONTRATO DE INTERFACE" in contexto["contrato_de_interface"]


def test_error_report_lista_identificadores_ausentes(ws, monkeypatch):
    from src.agents.workflow_coding_review.executor import agent as executor

    monkeypatch.setenv("AI4ES_ACEITE_INDEPENDENTE", "true")
    (ws.coder / "templates").mkdir(parents=True)
    (ws.coder / "templates" / "u.html").write_text('<form data-testid="form-upload"><button>Enviar</button></form>')
    (ws.coder / ai.PASTA_ACEITE).mkdir(parents=True)
    (ws.coder / ai.PASTA_ACEITE / "test_interface_TASK_002.py").write_text(
        'f = page.get_by_test_id("form-upload"); f.get_by_test_id("btn-enviar-upload").click()'
    )
    assert executor._identificadores_ausentes(_state()) == ["btn-enviar-upload"]
    nao_web = _state()
    nao_web["tasks"]["macro_context"]["product_type"] = "api_service"
    assert executor._identificadores_ausentes(nao_web) == []


def test_iterator_acha_os_autores_pelo_nome():
    from google.adk.agents import BaseAgent

    from src.agents.workflow_coding_review.task_iterator import NOME_AUTOR_CONTRATO, TaskIterator

    class _A(BaseAgent):
        async def _run_async_impl(self, ctx):
            if False:
                yield None

    loop, jornada, contrato = _A(name="loop"), _A(name="cr_journey_author"), _A(name=NOME_AUTOR_CONTRATO)
    so_contrato = TaskIterator(name="it1", sub_agents=[loop, contrato])
    assert so_contrato._autor_jornada is None and so_contrato._autor_contrato is contrato
    tudo = TaskIterator(name="it2", sub_agents=[_A(name="l2"), _A(name="j2"), _A(name=NOME_AUTOR_CONTRATO)])
    assert tudo._autor_jornada.name == "j2" and tudo._autor_contrato.name == NOME_AUTOR_CONTRATO


def test_fase_do_contrato_so_em_web_app_e_esqueleto_so_em_python_web(ws):
    from google.adk.agents import BaseAgent

    from src.agents.workflow_coding_review.task_iterator import NOME_AUTOR_CONTRATO, TaskIterator

    class _Autor(BaseAgent):
        async def run_async(self, ctx):  # noqa: D401 — stub: grava o contrato
            contrato, _ = cw.validar(_CONTRATO)
            cw.gravar(ws.tasks, contrato)
            if False:
                yield None

    class _Loop(BaseAgent):
        async def _run_async_impl(self, ctx):
            if False:
                yield None

    it = TaskIterator(name="it", sub_agents=[_Loop(name="loop"), _Autor(name=NOME_AUTOR_CONTRATO)])
    ctx = SimpleNamespace(invocation_id="i", branch=None)
    ctx.model_copy = lambda update: ctx

    async def _rodar(state):
        return [e async for e in it._fase_contrato(ctx, state, state["tasks"]["tasks"])]

    api = _state()
    api["tasks"]["macro_context"]["product_type"] = "api_service"
    assert asyncio.run(_rodar(api)) == [] and cw.ler(ws.tasks) is None

    web = {**_state(), "trilha": {"id": "python-web"}}
    eventos = asyncio.run(_rodar(web))
    assert len(eventos) == 1 and cw.ler(ws.tasks) is not None
    assert (ws.coder / "app" / "ids.py").is_file()
    # Contrato já existe: não chama o autor de novo.
    assert asyncio.run(_rodar(web)) == []


# ── Navegação gerada e conformidade (design ↔ implementação) ───────────────


def test_teste_de_navegacao_gerado_do_mapa():
    import ast

    contrato, _ = cw.validar(_CONTRATO)
    codigo, inalcancaveis = cw.gerar_teste_navegacao(contrato)
    ast.parse(codigo)
    assert inalcancaveis == []
    assert "def test_navegacao_00_tela_inicial" in codigo
    assert "def test_navegacao_01_painel_galeria" in codigo
    assert '_dentro(page, "item-ensaio").get_by_test_id("link-galeria-ensaio").click()' in codigo
    # Volta da galeria: chega à galeria pelo caminho mais curto e clica em voltar.
    trecho = codigo[codigo.index("def test_navegacao_02_galeria_painel"):]
    assert trecho.index("link-galeria-ensaio") < trecho.index("link-voltar-painel")
    assert 'expect(page.get_by_test_id("tela-painel")).to_be_visible()' in trecho


def test_tela_inalcancavel_no_mapa():
    dados = json.loads(json.dumps(_CONTRATO))
    dados["navegacao"] = dados["navegacao"][1:]  # só galeria → painel
    contrato, erros = cw.validar(dados)
    assert erros == []
    assert cw.gerar_teste_navegacao(contrato)[1] == ["galeria"]


def test_conformidade_so_anota(tmp_path):
    contrato, _ = cw.validar(_CONTRATO)
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "base.html").write_text(
        '<link href="/static/global.css"><main data-testid="tela-painel">'
        '<form data-testid="form-criar-ensaio"></form></main>'
    )
    rel = cw.conformidade(contrato, tmp_path, rotas_do_codigo=[("GET", "/")], navegacao={"arestas": 2})
    assert rel["estilo_referenciado"] is True
    assert rel["telas_sem_marcador"] == ["galeria"]
    assert "btn-enviar-fotos" in rel["elementos_ausentes"]
    assert rel["aderencia_elementos"] == round(2 / 9, 3)
    assert "POST /ensaios [TASK-001]" in rel["rotas_ausentes"]
    assert rel["navegacao"] == {"arestas": 2}


def test_estilo_do_design_copiado_na_trilha_python_web(tmp_path):
    contrato, _ = cw.validar(_CONTRATO)
    raiz, workdir = tmp_path / "sessao", tmp_path / "src"
    (raiz / "design" / "prototypes").mkdir(parents=True)
    (raiz / "design" / "prototypes" / "global.css").write_text(":root{--accent:#0ea5a4}")
    assert cw.instalar_estilo_python_web(raiz, workdir, contrato.estilo) == "static/global.css"
    assert "--accent" in (workdir / "static" / "global.css").read_text()
    assert cw.instalar_estilo_python_web(raiz, workdir, contrato.estilo) is None  # não sobrescreve


def test_secao_traz_navegacao_estilo_marcadores_decisoes():
    contrato, _ = cw.validar(_CONTRATO)
    texto = cw.secao_prompt(contrato, "TASK-001")
    for trecho in (
        "## Navegação", "painel → galeria: clicar `link-galeria-ensaio` dentro de `item-ensaio`",
        "## Design system", "`/static/global.css`", "`tela-painel`", "## Decisões de arquitetura do design",
        "ingestão assíncrona", "## Suposições do design", "cliente é texto livre",
    ):
        assert trecho in texto, trecho


def test_navegacao_gerada_so_percorre_links_e_rota_sem_query():
    dados = json.loads(json.dumps(_CONTRATO))
    dados["navegacao"].append(
        {"origem": "painel", "acao": "criar ensaio", "elemento": "btn-criar-ensaio", "destino": "painel"}
    )
    contrato, erros = cw.validar(dados)
    assert erros == []
    codigo, _ = cw.gerar_teste_navegacao(contrato)
    assert "btn-criar-ensaio" not in codigo  # envio de formulário: fica com os testes das tasks
    dados["rotas"].append({"metodo": "GET", "caminho": "/ensaios/{ensaio_id}/photos?selected=true", "formato": "json"})
    contrato, erros = cw.validar(dados)
    assert contrato is None and any("sem query string" in e for e in erros)
