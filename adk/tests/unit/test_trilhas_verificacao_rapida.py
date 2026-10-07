"""Trilhas de execução (`AI4ES_TRILHAS`) e verificação rápida (`AI4ES_VERIFICACAO_RAPIDA`).

A verificação com trilha roda de verdade (DirectSandbox + venv real, com o
próprio interpretador dos testes e um projeto só de stdlib, para não depender
de rede); a revisão por LLM tem a chamada substituída.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from shared.execution import trilhas as trilhas_mod
from shared.execution import verificacao_rapida as vr
from shared.execution.manifest import RunManifest
from shared.execution.trilhas import (
    PASTA_ATALHOS,
    ambiente_da_trilha,
    secao_prompt,
    selecionar_trilha,
)

_PY = str(Path(sys.executable).resolve())


@pytest.fixture
def interpretador_fixo(monkeypatch):
    monkeypatch.setattr(trilhas_mod, "resolver_interpretador", lambda _v: _PY)


# ── Seleção ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "stack, esperado",
    [
        (["Python", "FastAPI", "Jinja2", "SQLite"], "python-web"),
        (["python", "flask"], "python-web"),
        (["python", "click"], "python-generic"),
        ("python 3 (somente stdlib)", "python-generic"),
        (["node", "express"], None),
        ([], None),
        (None, None),
    ],
)
def test_selecao_de_trilha_pela_stack(interpretador_fixo, stack, esperado):
    trilha = selecionar_trilha(stack)
    assert (trilha or {}).get("id") == esperado


def test_trilha_web_traz_constraints_versionado(interpretador_fixo):
    trilha = selecionar_trilha(["python", "fastapi"])
    assert Path(trilha["constraints"]).is_file()
    assert "fastapi==" in Path(trilha["constraints"]).read_text()
    json.dumps(trilha)  # vai para o state: precisa ser serializável


def test_sem_interpretador_a_stack_fica_livre(monkeypatch):
    monkeypatch.setattr(trilhas_mod, "resolver_interpretador", lambda _v: None)
    assert selecionar_trilha(["python", "fastapi"]) is None


def test_interpretador_explicito_por_variavel(monkeypatch, tmp_path):
    monkeypatch.setenv("AI4ES_TRILHA_PYTHON_312", _PY)
    assert trilhas_mod.resolver_interpretador("3.12") == _PY
    monkeypatch.setenv("AI4ES_TRILHA_PYTHON_312", str(tmp_path / "nao-existe"))
    assert trilhas_mod.resolver_interpretador("3.12") is None


def test_ambiente_da_trilha_cria_atalhos_e_aplica_restricoes(interpretador_fixo, tmp_path):
    trilha = selecionar_trilha(["python", "fastapi"])
    env = ambiente_da_trilha(trilha, tmp_path)
    pasta = tmp_path / PASTA_ATALHOS / "bin"
    assert env["PATH"].startswith(str(pasta))
    assert (pasta / "python3").resolve() == Path(_PY)
    assert env["PIP_CONSTRAINT"] == trilha["constraints"]
    # Idempotente: rodar de novo não falha com o atalho já existente.
    assert ambiente_da_trilha(trilha, tmp_path) == env


def test_ambiente_sem_trilha_valida_e_vazio(tmp_path):
    assert ambiente_da_trilha(None, tmp_path) == {}
    assert ambiente_da_trilha({"interpretador": "/nao/existe"}, tmp_path) == {}


def test_secao_do_prompt(interpretador_fixo):
    assert secao_prompt(None) == ""
    secao = secao_prompt(selecionar_trilha(["python", "fastapi"]))
    assert secao.startswith("# TRILHA DE EXECUÇÃO: python-web (Python 3.12)")
    assert "imghdr" in secao and "httpx" in secao


# ── Verificação rápida com trilha (execução real) ──────────────────────────


@pytest.mark.parametrize(
    "run, esperado",
    [
        ("venv/bin/uvicorn app.main:app --port 8000", "app.main"),
        ("venv/bin/python -m uvicorn app.main:app", "app.main"),
        ("venv/bin/gunicorn web.wsgi:application", "web.wsgi"),
        ("venv/bin/python -m meupacote --input x", "meupacote"),
        ("venv/bin/python pipeline.py", None),
    ],
)
def test_modulo_de_entrada(run, esperado):
    manifest = RunManifest(surface="command", run=run)
    assert vr.modulo_de_entrada(manifest) == esperado


def _projeto(raiz: Path, main: str, *, extra: dict | None = None) -> Path:
    (raiz / "app").mkdir(parents=True)
    (raiz / "app" / "__init__.py").write_text("")
    (raiz / "app" / "main.py").write_text(main)
    for caminho, texto in (extra or {}).items():
        (raiz / caminho).write_text(texto)
    (raiz / "run.json").write_text(
        json.dumps(
            {
                "surface": "command",
                "build": ["python3 -m venv venv"],
                "run": "venv/bin/python -m app.main",
                "test": ["venv/bin/python -m pytest -v"],
            }
        )
    )
    return raiz


@pytest.fixture
def trilha_local(monkeypatch, tmp_path):
    monkeypatch.setenv("AI4ES_VERIFICACAO_RAPIDA_CACHE", str(tmp_path / "cache"))
    return {"id": "python-generic", "python": "x", "interpretador": _PY, "constraints": None}


def test_projeto_saudavel_passa(trilha_local, tmp_path):
    projeto = _projeto(tmp_path / "ok", "import json\nVALOR = json.dumps({})\n")
    resultado = vr.verificar_rapido(projeto, trilha_local)
    assert resultado.modo == "trilha"
    assert resultado.ok, [f.como_texto() for f in resultado.falhas]


def test_erro_de_import_e_barrado_com_o_traceback(trilha_local, tmp_path):
    projeto = _projeto(tmp_path / "imp", "from json import NaoExiste\n")
    resultado = vr.verificar_rapido(projeto, trilha_local)
    assert [f.etapa for f in resultado.falhas] == ["import"]
    assert "NaoExiste" in resultado.falhas[0].detalhe


def test_import_circular_e_barrado(trilha_local, tmp_path):
    projeto = _projeto(
        tmp_path / "circ",
        "from app.rotas import ROTA\nTEMPLATES = 1\n",
        extra={"app/rotas.py": "from app.main import TEMPLATES\nROTA = 2\n"},
    )
    resultado = vr.verificar_rapido(projeto, trilha_local)
    assert resultado.falhas and "circular" in resultado.falhas[0].detalhe


def test_erro_de_sintaxe_e_barrado_antes_do_import(trilha_local, tmp_path):
    projeto = _projeto(tmp_path / "sint", "def f(:\n    pass\n")
    resultado = vr.verificar_rapido(projeto, trilha_local)
    assert [f.etapa for f in resultado.falhas] == ["sintaxe"]


def test_venv_e_reaproveitado_pelo_cache(trilha_local, tmp_path):
    projeto = _projeto(tmp_path / "cache_ok", "X = 1\n")
    vr.verificar_rapido(projeto, trilha_local)
    vr.verificar_rapido(projeto, trilha_local)
    venvs = [p for p in (tmp_path / "cache").iterdir() if not p.name.startswith(".")]
    assert len(venvs) == 1


def test_manifesto_invalido_nao_e_problema_da_verificacao(trilha_local, tmp_path):
    (tmp_path / "vazio").mkdir()
    assert vr.verificar_rapido(tmp_path / "vazio", trilha_local).modo == "nenhum"


# ── Revisão por LLM (sem trilha) ───────────────────────────────────────────


def test_revisao_so_bloqueia_com_confianca_alta():
    texto = json.dumps(
        {
            "erros": [
                {"arquivo": "a.js", "descricao": "require de pacote não declarado", "confianca": "alta"},
                {"arquivo": "b.js", "descricao": "talvez", "confianca": "media"},
            ]
        }
    )
    falhas = vr._interpretar_revisao("```json\n" + texto + "\n```")
    assert [f.detalhe for f in falhas] == ["a.js: require de pacote não declarado"]
    assert vr._interpretar_revisao("sem json") == []


def test_revisao_indisponivel_nao_trava(monkeypatch, tmp_path):
    projeto = _projeto(tmp_path / "llm", "X = 1\n")

    def _quebra(_prompt):
        raise RuntimeError("rate limit")

    monkeypatch.setattr(vr, "_chamar_llm", _quebra)
    resultado = vr.verificar_rapido(projeto, None, stack="node")
    assert resultado.modo == "genai" and resultado.ok


def test_revisao_envia_arquivos_e_devolve_falhas(monkeypatch, tmp_path):
    projeto = _projeto(tmp_path / "llm2", "import requests\n")
    vistos = {}

    def _llm(prompt):
        vistos["prompt"] = prompt
        return '{"erros": [{"arquivo": "app/main.py", "descricao": "requests não declarado", "confianca": "alta"}]}'

    monkeypatch.setattr(vr, "_chamar_llm", _llm)
    resultado = vr.verificar_rapido(projeto, None, stack="python")
    assert "--- run.json ---" in vistos["prompt"] and "import requests" in vistos["prompt"]
    assert not resultado.ok and resultado.falhas[0].etapa == "revisao_llm"


# ── Gate do executor ───────────────────────────────────────────────────────


@pytest.fixture
def executor_module(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    modulo = importlib.import_module("src.agents.workflow_coding_review.executor.agent")
    monkeypatch.setattr(modulo, "fingerprint_mudou", lambda _: True)
    monkeypatch.setattr(
        modulo,
        "verificar_executabilidade",
        lambda _d: SimpleNamespace(executavel=True, bloqueios=[], arquivos=[]),
    )
    return modulo


class _Ctx:
    def __init__(self, state):
        self.state = state
        self.actions = SimpleNamespace(escalate=None)


def test_gate_sem_flag_nao_verifica(executor_module, monkeypatch):
    monkeypatch.delenv("AI4ES_VERIFICACAO_RAPIDA", raising=False)

    def _nao_chamar(*_a, **_k):
        raise AssertionError("não deveria verificar")

    monkeypatch.setattr(executor_module, "verificar_rapido", _nao_chamar)
    assert executor_module.recusar_execucao_incompleta(_Ctx({"task_id": "TASK-001"})) is None


def test_gate_com_flag_barra_e_devolve_os_erros_ao_coder(executor_module, monkeypatch):
    monkeypatch.setenv("AI4ES_VERIFICACAO_RAPIDA", "true")
    falha = vr.ResultadoVerificacao(
        modo="trilha", falhas=[vr.Falha("import", "ImportError: X", comando="python -c ...")]
    )
    recebidos = {}

    def _verificar(coder_dir, trilha, *, stack):
        recebidos.update(trilha=trilha, stack=stack)
        return falha

    monkeypatch.setattr(executor_module, "verificar_rapido", _verificar)
    state = {
        "task_id": "TASK-001",
        "trilha": {"id": "python-web"},
        "tasks": {"macro_context": {"tech_stack": ["python", "fastapi"]}},
    }
    ctx = _Ctx(state)
    conteudo = executor_module.recusar_execucao_incompleta(ctx)

    assert conteudo.parts[0].text.startswith("VERIFICAÇÃO RÁPIDA FALHOU")
    assert "ImportError: X" in state["execution_result"]
    assert state["progress_score_history"] == [0.05]
    assert recebidos == {"trilha": {"id": "python-web"}, "stack": "python, fastapi"}


def test_gate_com_flag_e_verificacao_ok_deixa_o_executor_rodar(executor_module, monkeypatch):
    monkeypatch.setenv("AI4ES_VERIFICACAO_RAPIDA", "true")
    monkeypatch.setattr(
        executor_module, "verificar_rapido", lambda *_a, **_k: vr.ResultadoVerificacao(modo="trilha")
    )
    assert executor_module.recusar_execucao_incompleta(_Ctx({"task_id": "TASK-001"})) is None


def test_gate_sobrevive_a_excecao_da_verificacao(executor_module, monkeypatch):
    monkeypatch.setenv("AI4ES_VERIFICACAO_RAPIDA", "true")

    def _explode(*_a, **_k):
        raise OSError("disco cheio")

    monkeypatch.setattr(executor_module, "verificar_rapido", _explode)
    assert executor_module.recusar_execucao_incompleta(_Ctx({"task_id": "TASK-001"})) is None


# ── TaskIterator, prompt do coder e harness ────────────────────────────────


@pytest.mark.asyncio
async def test_iterator_publica_a_trilha_com_a_flag(monkeypatch):
    from src.agents.workflow_coding_review import task_iterator
    from tests.unit.test_task_iterator import _executar_iterator

    monkeypatch.setenv("AI4ES_TRILHAS", "true")
    monkeypatch.setattr(
        task_iterator, "selecionar_trilha", lambda stack: {"id": "python-web", "python": "3.12", "interpretador": _PY, "stack": stack}
    )
    tasks = {"macro_context": {"tech_stack": ["python", "fastapi"]}, "tasks": [{"id": "TASK-001"}]}
    _, _, state = await _executar_iterator(tasks, {})
    assert state["trilha"]["id"] == "python-web"
    assert state["trilha"]["stack"] == ["python", "fastapi"]


@pytest.mark.asyncio
async def test_iterator_sem_flag_nao_escolhe_trilha(monkeypatch):
    from tests.unit.test_task_iterator import _executar_iterator

    monkeypatch.delenv("AI4ES_TRILHAS", raising=False)
    _, _, state = await _executar_iterator({"tasks": [{"id": "TASK-001"}]}, {})
    assert "trilha" not in state


def test_prompt_do_coder_ganha_a_secao_da_trilha(monkeypatch, tmp_path, interpretador_fixo):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    coder = importlib.import_module("src.agents.workflow_coding_review.coder.agent")

    async def _sem_injecao(texto, _ctx):
        return texto

    monkeypatch.setattr("google.adk.utils.instructions_utils.inject_session_state", _sem_injecao)
    trilha = selecionar_trilha(["python", "fastapi"])
    com = asyncio.run(coder._INSTRUCTION(SimpleNamespace(state={"trilha": trilha})))
    sem = asyncio.run(coder._INSTRUCTION(SimpleNamespace(state={})))
    assert com == secao_prompt(trilha) + sem


def test_harness_aplica_o_ambiente_da_trilha_nos_comandos(tmp_path, monkeypatch):
    from shared.tools.coding_tools import harness_execucao as harness
    from tests.unit import test_harness_execucao as th

    envs = []

    class _Sandbox(th.FakeSandbox):
        def exec(self, command, *, timeout, env=None):
            envs.append(env)
            return super().exec(command, timeout=timeout, env=env)

    monkeypatch.setattr(harness, "ambiente_da_trilha", lambda trilha, raiz: {"PATH": "/trilha/bin"})
    coder, execution, tasks = th._dirs(tmp_path)
    th._write_task(tasks)
    th._write_manifest(coder, th._manifest_command(env={"FOO": "1"}))
    with monkeypatch.context() as m:
        m.setattr(harness, "create_sandbox", lambda *a, **k: _Sandbox())
        relatorio = harness.executar_harness_validacao(
            "TASK-001", 1, coder_base_dir=coder, execution_base_dir=execution,
            tasks_base_dir=tasks, trilha={"id": "python-web"},
        )
    assert envs and all(e == {"PATH": "/trilha/bin", "FOO": "1"} for e in envs)
    prep = relatorio["stages"][0]
    assert prep["evidence"]["trilha"] == "python-web"


def test_harness_sem_trilha_mantem_o_env_do_manifesto(tmp_path, monkeypatch):
    from shared.tools.coding_tools import harness_execucao as harness
    from tests.unit import test_harness_execucao as th

    envs = []

    class _Sandbox(th.FakeSandbox):
        def exec(self, command, *, timeout, env=None):
            envs.append(env)
            return super().exec(command, timeout=timeout, env=env)

    coder, execution, tasks = th._dirs(tmp_path)
    th._write_task(tasks)
    th._write_manifest(coder, th._manifest_command())
    monkeypatch.setattr(harness, "create_sandbox", lambda *a, **k: _Sandbox())
    relatorio = harness.executar_harness_validacao(
        "TASK-001", 1, coder_base_dir=coder, execution_base_dir=execution, tasks_base_dir=tasks,
    )
    assert envs and all(e is None for e in envs)
    assert relatorio["stages"][0]["evidence"]["trilha"] is None
