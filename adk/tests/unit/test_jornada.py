"""Jornada do produto integrado (`AI4ES_JORNADA`).

`executar_jornada` roda de verdade (DirectSandbox, com o pytest do próprio
ambiente de testes); a fase no TaskIterator usa um loop e um autor falsos, e a
execução da jornada é substituída por uma sequência controlada.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from google.adk.agents import BaseAgent
from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import PrivateAttr

from shared.tools.coding_tools import jornada as jornada_mod
from shared.tools.coding_tools.aceite_independente import ler_mapa
from shared.tools.coding_tools.jornada import (
    ARQUIVO_JORNADA,
    FALHOU,
    NAO_EXECUTADA,
    PASSOU,
    ResultadoJornada,
    executar_jornada,
    montar_task_integracao,
)

_FLAG = "AI4ES_JORNADA"


# ── executar_jornada (execução real) ───────────────────────────────────────


def _produto(raiz: Path, jornada: str | None, *, test_cmd: str | None = None) -> Path:
    (raiz / "app").mkdir(parents=True)
    (raiz / "app" / "__init__.py").write_text("")
    (raiz / "app" / "loja.py").write_text("def total(itens):\n    return sum(itens)\n")
    (raiz / "conftest.py").write_text("")
    if jornada is not None:
        (raiz / "tests" / "journey").mkdir(parents=True)
        (raiz / ARQUIVO_JORNADA).write_text(jornada)
    (raiz / "run.json").write_text(
        json.dumps(
            {
                "surface": "none",
                "build": [],
                "test": [test_cmd or f"{sys.executable} -m pytest -v"],
            }
        )
    )
    return raiz


def test_jornada_que_passa(tmp_path):
    produto = _produto(
        tmp_path / "ok",
        "from app.loja import total\n\ndef test_jornada_01_compra():\n    assert total([1, 2]) == 3\n",
    )
    resultado = executar_jornada(produto)
    assert resultado.status == PASSOU, resultado.saida
    assert [t["nodeid"] for t in resultado.testes] == [f"{ARQUIVO_JORNADA}::test_jornada_01_compra"]


def test_jornada_que_falha_lista_as_falhas(tmp_path):
    produto = _produto(
        tmp_path / "falha",
        "from app.loja import total\n\n"
        "def test_jornada_01_ok():\n    assert total([1]) == 1\n\n"
        "def test_jornada_02_desconto():\n    assert total([10]) == 9, 'sem desconto'\n",
    )
    resultado = executar_jornada(produto)
    assert resultado.status == FALHOU
    assert resultado.falhas == [f"{ARQUIVO_JORNADA}::test_jornada_02_desconto"]
    assert "sem desconto" in resultado.saida


@pytest.mark.parametrize(
    "jornada, comando, motivo",
    [
        (None, None, "não foi escrito"),
        ("def test_jornada_01():\n    pass\n", "npm test", "não usa pytest"),
    ],
)
def test_jornada_nao_executada(tmp_path, jornada, comando, motivo):
    resultado = executar_jornada(_produto(tmp_path / "x", jornada, test_cmd=comando))
    assert resultado.status == NAO_EXECUTADA and motivo in resultado.motivo


def test_task_de_integracao_carrega_as_falhas():
    resultado = ResultadoJornada(FALHOU, motivo="m", falhas=["t::a"], saida="Traceback ... 404")
    task = montar_task_integracao(resultado, "TASK-901", 1)
    assert task["id"] == "TASK-901" and task["type"] == "integration"
    assert "t::a" in task["description"] and "404" in task["description"]
    assert [c["id"] for c in task["acceptance_criteria"]] == ["CA-01"]


# ── Ferramenta do autor ────────────────────────────────────────────────────


def test_ferramenta_grava_a_jornada(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import get_agent_workspace
    from src.agents.workflow_coding_review.journey.agent import tool_salvar_teste_jornada

    ctx = SimpleNamespace(state={})
    assert tool_salvar_teste_jornada("def f(:\n", ctx)["sucesso"] is False
    assert tool_salvar_teste_jornada("def helper():\n    pass\n", ctx)["sucesso"] is False
    resposta = tool_salvar_teste_jornada("def test_jornada_01_x():\n    assert 1\n", ctx)
    assert resposta == {
        "sucesso": True, "caminho": ARQUIVO_JORNADA, "modo": "http", "jornadas": ["test_jornada_01_x"]
    }
    assert (get_agent_workspace("cr_coder") / ARQUIVO_JORNADA).is_file()


# ── Fase da jornada no TaskIterator ────────────────────────────────────────


class _Loop(BaseAgent):
    _tasks: list = PrivateAttr(default_factory=list)

    async def _run_async_impl(self, ctx):
        task_id = ctx.session.state["task_id"]
        self._tasks.append(task_id)
        ctx.session.state["validation"] = {"work_item_id": task_id, "status": "aprovado"}
        yield Event(
            invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=task_id)]),
        )


class _Autor(BaseAgent):
    _contextos: list = PrivateAttr(default_factory=list)

    async def _run_async_impl(self, ctx):
        self._contextos.append(ctx.session.state.get("jornada_contexto"))
        yield Event(
            invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text="jornada escrita")]),
        )


async def _rodar(monkeypatch, tmp_path, sequencia, *, com_autor=True):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from src.agents.workflow_coding_review import task_iterator as ti

    monkeypatch.setattr(ti, "verificar_executabilidade", lambda _d: SimpleNamespace(executavel=True))
    resultados = iter(sequencia)
    monkeypatch.setattr(ti, "executar_jornada", lambda *_a, **_k: next(resultados))

    loop, autor = _Loop(name="loop"), _Autor(name="autor")
    iterator = ti.TaskIterator(name="it", sub_agents=[loop, autor] if com_autor else [loop])
    servico = InMemorySessionService()
    runner = Runner(agent=iterator, app_name="t", session_service=servico)
    tasks = {"macro_context": {"tech_stack": ["python"]}, "tasks": [{"id": "TASK-001", "description": "d"}]}
    sessao = await servico.create_session(app_name="t", user_id="u", state={"tasks": tasks})
    async for _ in runner.run_async(
        user_id="u", session_id=sessao.id,
        new_message=types.Content(role="user", parts=[types.Part(text="x")]),
    ):
        pass
    final = await servico.get_session(app_name="t", user_id="u", session_id=sessao.id)
    return loop._tasks, autor._contextos, final.state


_FALHA = ResultadoJornada(
    FALHOU, motivo="testes da jornada falharam",
    testes=[{"nodeid": f"{ARQUIVO_JORNADA}::test_jornada_01", "outcome": "falhou"}],
    falhas=[f"{ARQUIVO_JORNADA}::test_jornada_01"], saida="404",
)


@pytest.mark.asyncio
async def test_jornada_falha_vira_task_de_integracao(monkeypatch, tmp_path):
    monkeypatch.setenv(_FLAG, "true")
    tasks, contextos, state = await _rodar(
        monkeypatch, tmp_path, [_FALHA, ResultadoJornada(PASSOU, testes=_FALHA.testes)]
    )

    assert tasks == ["TASK-001", "TASK-901"]
    assert json.loads(contextos[0])["arquivo_de_teste"] == ARQUIVO_JORNADA
    summary = state["task_iteration_summary"]
    assert summary["jornada"]["status"] == PASSOU and summary["jornada"]["rodadas"] == 1
    assert summary["task_results"]["TASK-901"]["status"] == "aprovado"
    assert summary["processed_task_ids"] == ["TASK-001"]
    # O critério da integração é decidido pelos testes da jornada.
    from shared.workspace import get_agent_workspace

    tasks_dir = get_agent_workspace("cr_context_engineer")
    assert ler_mapa(tasks_dir, "TASK-901")["por_criterio"] == {
        "CA-01": [f"{ARQUIVO_JORNADA}::test_jornada_01"]
    }
    assert (tasks_dir / "TASK-901.json").is_file()
    # A cobertura das tasks originais não muda por causa da integração.
    assert summary["expected_task_ids"] == ["TASK-001"]


@pytest.mark.asyncio
async def test_sem_rodadas_a_jornada_so_e_medida(monkeypatch, tmp_path):
    monkeypatch.setenv(_FLAG, "true")
    monkeypatch.setenv("AI4ES_JORNADA_MAX_RODADAS", "0")
    tasks, _, state = await _rodar(monkeypatch, tmp_path, [_FALHA])
    assert tasks == ["TASK-001"]
    assert state["task_iteration_summary"]["jornada"]["status"] == FALHOU


@pytest.mark.asyncio
async def test_sem_flag_ou_sem_autor_nao_ha_jornada(monkeypatch, tmp_path):
    monkeypatch.delenv(_FLAG, raising=False)
    tasks, contextos, state = await _rodar(monkeypatch, tmp_path, [])
    assert tasks == ["TASK-001"] and contextos == []
    assert "jornada" not in state["task_iteration_summary"]

    monkeypatch.setenv(_FLAG, "true")
    _, _, state = await _rodar(monkeypatch, tmp_path / "b", [], com_autor=False)
    assert "jornada" not in state["task_iteration_summary"]


# ── Revisor, manifesto e proteção ──────────────────────────────────────────


def test_revisor_mostra_a_jornada_so_quando_existe():
    from src.agents.workflow_coding_review.reviewer.agent import _render_task_outcomes

    base = {"expected_task_ids": [], "task_results": {}, "accepted_task_ids": []}
    sem = _render_task_outcomes({"task_iteration_summary": base})
    assert "Jornada" not in sem
    com = _render_task_outcomes(
        {"task_iteration_summary": {**base, "jornada": {"status": "falhou", "motivo": "m", "falhas": ["t::a"], "rodadas": 1}}}
    )
    assert "Jornada do produto (teste de ponta a ponta): falhou — m; falhas: t::a; rodadas de integração: 1" in com


@pytest.mark.parametrize("status, esperado", [("passou", "ok"), ("falhou", "partial")])
def test_manifesto_considera_a_jornada(tmp_path, monkeypatch, status, esperado):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import get_agent_workspace
    from src.agents.workflow_coding_review import manifest

    coder = get_agent_workspace("cr_coder")
    (coder / "app.py").write_text("x = 1\n")
    (coder.parent / "review").mkdir(parents=True, exist_ok=True)
    (coder.parent / "review" / "review.md").write_text("## Status: APROVADO\n")
    state = {"task_iteration_summary": {"accepted_task_ids": [], "task_results": {}, "jornada": {"status": status}}}
    manifest.emit_coding_manifest(SimpleNamespace(state=state))
    assert state["coding_manifest"]["status"] == esperado
    assert state["coding_manifest"]["jornada"]["status"] == status


def test_coder_nao_edita_a_jornada(monkeypatch):
    from src.agents.workflow_coding_review.coder.workspace_guard import proteger_testes_de_aceite

    criar = SimpleNamespace(name="tool_criar_arquivo")
    ctx = SimpleNamespace(state={})
    monkeypatch.delenv("AI4ES_ACEITE_INDEPENDENTE", raising=False)
    monkeypatch.setenv(_FLAG, "true")
    assert proteger_testes_de_aceite(criar, {"caminho": ARQUIVO_JORNADA}, ctx)["sucesso"] is False
    assert proteger_testes_de_aceite(criar, {"caminho": "tests/acceptance/x.py"}, ctx) is None
    monkeypatch.delenv(_FLAG)
    assert proteger_testes_de_aceite(criar, {"caminho": ARQUIVO_JORNADA}, ctx) is None


def test_instrucao_dos_autores_nao_interpreta_chaves_do_prompt():
    """O prompt da jornada traz dicionários de exemplo (`{"name": ...}`); só o marcador é trocado."""
    from src.agents.workflow_coding_review.acceptance.agent import _instrucao as aceite
    from src.agents.workflow_coding_review.journey.agent import _instrucao as jornada

    texto = jornada(SimpleNamespace(state={"jornada_contexto": "CONTEXTO"}))
    assert "CONTEXTO" in texto and '{"name":' in texto and "{jornada_contexto?}" not in texto
    assert "{jornada_contexto?}" not in jornada(SimpleNamespace(state={}))
    assert "TASK-X" in aceite(SimpleNamespace(state={"aceite_task": "TASK-X"}))


def test_revisor_sem_historico_no_modo_enxuto(tmp_path):
    import os
    import subprocess
    import sys

    codigo = (
        "from src.agents.workflow_coding_review.reviewer.agent import _analyzer as a;"
        "print(a.include_contents)"
    )

    def _modo(valor):
        env = {**os.environ, "AI4ES_CODER_CONTEXTO_ENXUTO": valor, "WORKSPACE_OUTPUT_DIR": str(tmp_path)}
        saida = subprocess.run(
            [sys.executable, "-c", codigo], env=env, capture_output=True, text=True,
            cwd=str(Path(__file__).resolve().parents[2]), timeout=120,
        )
        return saida.stdout.strip().splitlines()[-1]

    assert _modo("true") == "none"
    assert _modo("") == "default"


def _porta_livre() -> int:
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _servico(raiz: Path, jornada_codigo: str, *, main: str) -> Path:
    (raiz / "app").mkdir(parents=True)
    (raiz / "app" / "__init__.py").write_text("")
    (raiz / "app" / "main.py").write_text(main)
    (raiz / "tests" / "journey").mkdir(parents=True)
    (raiz / ARQUIVO_JORNADA).write_text(jornada_codigo)
    porta = _porta_livre()
    (raiz / "run.json").write_text(json.dumps({
        "surface": "service", "build": [],
        "run": f"{sys.executable} -m uvicorn app.main:app --port {porta}",
        "port": porta, "healthcheck": "/",
        "test": [f"{sys.executable} -m pytest -v"],
    }))
    return raiz


_APP = (
    "import os\n"
    "from fastapi import FastAPI\n"
    "app = FastAPI()\n"
    "@app.get('/')\n"
    "def raiz():\n"
    "    return {'ok': True}\n"
    "@app.post('/upload')\n"
    "def upload():\n"
    "    destino = os.environ.get('MEDIA_DIR', '/storage')  # padrão quebrado\n"
    "    os.makedirs(os.path.join(destino, 'x'), exist_ok=True)\n"
    "    return {'ok': True}\n"
)

_JORNADA_HTTP = (
    "import os, httpx\n"
    "def test_jornada_01_upload():\n"
    "    c = httpx.Client(base_url=os.environ['AI4ES_JORNADA_URL'])\n"
    "    assert c.get('/').status_code == 200\n"
    "    r = c.post('/upload')\n"
    "    assert r.status_code < 400, f'upload -> {r.status_code}'\n"
)


def test_jornada_usa_o_servidor_do_run_json_sem_configuracao_extra(tmp_path, monkeypatch):
    """O defeito que os aceites isolados esconderam: padrão gravando em /storage."""
    monkeypatch.setattr(jornada_mod, "preparar_cliente_http", lambda *a, **k: None)
    monkeypatch.delenv("MEDIA_DIR", raising=False)
    resultado = executar_jornada(_servico(tmp_path / "svc", _JORNADA_HTTP, main=_APP))
    assert resultado.status == FALHOU, resultado.saida
    assert resultado.falhas == [f"{ARQUIVO_JORNADA}::test_jornada_01_upload"]
    assert "upload -> 500" in resultado.saida
    assert "log do servidor" in resultado.saida  # o traceback do 500 vai junto


def test_jornada_passa_quando_o_padrao_funciona(tmp_path, monkeypatch):
    monkeypatch.setattr(jornada_mod, "preparar_cliente_http", lambda *a, **k: None)
    app_ok = _APP.replace("'/storage'", "'media'")
    resultado = executar_jornada(_servico(tmp_path / "ok", _JORNADA_HTTP, main=app_ok))
    assert resultado.status == PASSOU, resultado.saida


def test_aplicacao_que_nao_sobe_reprova_a_jornada(tmp_path, monkeypatch):
    monkeypatch.setattr(jornada_mod, "preparar_cliente_http", lambda *a, **k: None)
    monkeypatch.setattr(jornada_mod, "_TIMEOUT_SUBIDA", 3)
    monkeypatch.setattr(jornada_mod, "esperar_servico", lambda url, timeout=3: "sem resposta")
    resultado = executar_jornada(_servico(tmp_path / "quebra", _JORNADA_HTTP, main="raise SystemExit(1)\n"))
    assert resultado.status == FALHOU and "não subiu" in resultado.motivo


def test_instrucao_do_coder_com_trilha_renderiza_no_template_do_adk(tmp_path, monkeypatch):
    """As notas da trilha passam pelo templating do ADK: nada de `{var}` nelas."""
    import asyncio
    import importlib

    from google.adk.agents.invocation_context import InvocationContext
    from google.adk.agents.readonly_context import ReadonlyContext
    from google.adk.sessions.in_memory_session_service import InMemorySessionService

    from shared.execution import trilhas

    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(trilhas, "resolver_interpretador", lambda _v: sys.executable)
    coder = importlib.import_module("src.agents.workflow_coding_review.coder.agent")

    async def _render():
        svc = InMemorySessionService()
        sess = await svc.create_session(
            app_name="a", user_id="u",
            state={"trilha": trilhas.selecionar_trilha(["python", "fastapi"])},
        )
        ic = InvocationContext(session_service=svc, invocation_id="i", agent=coder.agent, session=sess)
        return await coder._INSTRUCTION(ReadonlyContext(ic))

    texto = asyncio.run(_render())
    assert "TRILHA DE EXECUÇÃO: python-web" in texto


def test_autor_da_jornada_roda_o_proprio_teste(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from src.agents.workflow_coding_review.journey import agent as journey

    vistos = {}

    def _executar(coder_dir, trilha):
        vistos["trilha"] = trilha
        return ResultadoJornada(FALHOU, motivo="m", saida="E   TypeError: Cannot mix str")

    monkeypatch.setattr(jornada_mod, "executar_jornada", _executar)
    resposta = journey.tool_executar_teste_jornada(SimpleNamespace(state={"trilha": {"id": "t"}}))
    assert resposta == {"status": FALHOU, "motivo": "m", "saida": "E   TypeError: Cannot mix str"}
    assert vistos == {"trilha": {"id": "t"}}
    assert "tool_executar_teste_jornada" in [t.name for t in journey.author.tools]


@pytest.mark.asyncio
async def test_task_de_integracao_nao_quebra_a_cobertura(monkeypatch, tmp_path):
    monkeypatch.setenv(_FLAG, "true")
    _, _, state = await _rodar(
        monkeypatch, tmp_path, [_FALHA, ResultadoJornada(PASSOU, testes=_FALHA.testes)]
    )
    summary = state["task_iteration_summary"]
    assert summary["processed_task_ids"] == ["TASK-001"]
    assert summary["cobertura_completa"] is True
    assert "TASK-901" in summary["task_results"]


def test_revisor_recebe_o_ambiente_da_trilha_so_quando_ha_trilha(monkeypatch):
    from shared.execution import trilhas
    from src.agents.workflow_coding_review.reviewer.agent import _secao_ambiente

    monkeypatch.setattr(trilhas, "resolver_interpretador", lambda _v: sys.executable)
    assert _secao_ambiente({}) == ""
    secao = _secao_ambiente({"trilha": trilhas.selecionar_trilha(["python", "fastapi"])})
    assert "AMBIENTE DE EXECUÇÃO" in secao and "TemplateResponse(request" in secao
    assert "critical" in secao


# ── Modo navegador (Playwright) para produtos web ──────────────────────────


_JORNADA_WEB_OK = '''
from playwright.sync_api import Page, expect

def test_jornada_01_cria(page: Page):
    page.goto("/")
    page.get_by_role("button", name="Criar").click()
    expect(page.get_by_text("ok")).to_be_visible()
'''


@pytest.mark.parametrize(
    "codigo, trecho",
    [
        ("import httpx\ndef test_j(page):\n    page.goto('/')\n", "import de `httpx`"),
        ("from app.main import app\ndef test_j(page):\n    page.goto('/')\n", "import de `app.main`"),
        ("def test_j(page):\n    page.request.post('/ensaios/1/upload')\n", "`page.request`"),
        ("def test_j(page):\n    page.goto('/ensaios/1/upload')\n", "só pode abrir a página inicial"),
        ("def test_j(page, base_url):\n    page.goto(base_url + '/x')\n", "só pode abrir a página inicial"),
        ("import httpx\ndef test_j():\n    httpx.get('x')\n", "fixture `page`"),
        (
            "def test_j(page):\n    page.goto('/')\n"
            "    page.evaluate(\"() => document.body.appendChild(document.createElement('input'))\")\n",
            "`.evaluate(...)`",
        ),
        (
            "def test_j(page):\n    page.goto('/')\n"
            "    page.locator('#x').evaluate('e => e.click()')\n",
            "`.evaluate(...)`",
        ),
        ("def test_j(page):\n    page.goto('/')\n    page.route('**/x', lambda r: r.abort())\n", "`.route(...)`"),
        ("def test_j(page):\n    page.goto('/')\n    page.wait_for_function('1')\n", "`.wait_for_function(...)`"),
    ],
)
def test_modo_navegador_recusa_atalhos_que_pulam_a_interface(codigo, trecho):
    import ast

    from src.agents.workflow_coding_review.journey.agent import violacoes_do_modo_navegador

    assert any(trecho in v for v in violacoes_do_modo_navegador(ast.parse(codigo)))


def test_modo_navegador_aceita_jornada_pela_interface():
    import ast

    from src.agents.workflow_coding_review.journey.agent import violacoes_do_modo_navegador

    assert violacoes_do_modo_navegador(ast.parse(_JORNADA_WEB_OK)) == []


def test_modo_vem_do_tipo_de_produto():
    from src.agents.workflow_coding_review.journey.agent import modo_da_jornada

    assert modo_da_jornada("web_app") == "navegador"
    assert modo_da_jornada("api_service") == "http"
    assert modo_da_jornada(None) == "http"


def test_salvar_jornada_web_valida_e_grava_o_conftest(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import get_agent_workspace
    from src.agents.workflow_coding_review.journey.agent import tool_salvar_teste_jornada

    ctx = SimpleNamespace(state={"jornada_contexto": json.dumps({"modo": "navegador"})})
    recusada = tool_salvar_teste_jornada("import httpx\ndef test_jornada_01(page):\n    page.goto('/')\n", ctx)
    assert recusada["sucesso"] is False and "INTERFACE" in recusada["erro"]

    aceita = tool_salvar_teste_jornada(_JORNADA_WEB_OK, ctx)
    assert aceita["sucesso"] is True and aceita["modo"] == "navegador"
    conftest = get_agent_workspace("cr_coder") / jornada_mod.ARQUIVO_CONFTEST
    assert conftest.read_text() == jornada_mod.CONFTEST_JORNADA


def test_salvar_jornada_http_nao_exige_navegador(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from src.agents.workflow_coding_review.journey.agent import tool_salvar_teste_jornada

    ctx = SimpleNamespace(state={"jornada_contexto": json.dumps({"modo": "http"})})
    assert tool_salvar_teste_jornada(_JORNADA_HTTP, ctx)["sucesso"] is True


def test_conftest_da_jornada_compila_e_reprova_recurso_quebrado():
    import ast

    arvore = ast.parse(jornada_mod.CONFTEST_JORNADA)
    nomes = {n.name for n in ast.walk(arvore) if isinstance(n, ast.FunctionDef)}
    assert {"base_url", "_recursos_do_produto", "pytest_configure"} <= nomes
    assert "permite_status" in jornada_mod.CONFTEST_JORNADA
    assert jornada_mod.usa_navegador(_JORNADA_WEB_OK) and not jornada_mod.usa_navegador(_JORNADA_HTTP)


def test_coder_nao_edita_o_conftest_da_jornada(monkeypatch):
    from src.agents.workflow_coding_review.coder.workspace_guard import proteger_testes_de_aceite

    monkeypatch.setenv(_FLAG, "true")
    criar = SimpleNamespace(name="tool_criar_arquivo")
    resposta = proteger_testes_de_aceite(criar, {"caminho": jornada_mod.ARQUIVO_CONFTEST}, SimpleNamespace(state={}))
    assert resposta["sucesso"] is False
