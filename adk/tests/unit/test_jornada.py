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
    assert resposta == {"sucesso": True, "caminho": ARQUIVO_JORNADA, "jornadas": ["test_jornada_01_x"]}
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
