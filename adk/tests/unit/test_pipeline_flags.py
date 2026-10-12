"""Contagem de tokens opcional do orchestrator, ativada por variáveis de ambiente.

Cada teste liga só a flag que exercita; sem flags o comportamento histórico
deve permanecer idêntico. Os pipelines são substituídos por Runners falsos
que emitem eventos controlados (mesma estratégia de test_orchestrator_hitl).
"""

import json
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.genai import types

from shared.token_usage import record_usage

_FLAGS = [
    "AI4ES_TOKEN_USAGE_PERSIST",
    "AI4ES_TOKEN_REPORT_ON_PAUSE",
    "AI4ES_TOKEN_REPORT_DETAIL",
    "AI4ES_TOKEN_SESSION_TOTAL",
]

_PHASE = {
    "requirements_pipeline": "requirements",
    "design_pipeline": "design",
    "coding_review_pipeline": "coding",
    "qa_pipeline": "qa",
}


@pytest.fixture(autouse=True)
def _ambiente(monkeypatch, tmp_path):
    for f in _FLAGS:
        monkeypatch.delenv(f, raising=False)
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    return tmp_path / "ws"


# ── Fakes ──────────────────────────────────────────────────────────────────


def _manifest(phase, status="ok", artifacts=1, bloqueante=False):
    return {
        "phase": phase,
        "status": status,
        "artifacts": [
            {"tipo": "HU", "id": f"HU-{i:03d}", "path": f"{phase}/HU-{i:03d}.md"}
            for i in range(1, artifacts + 1)
        ],
        "doubts": (
            [{"id": "D-001", "severidade": "alta", "bloqueante": True, "path": f"{phase}/D-001.md"}]
            if bloqueante
            else []
        ),
        "summary": f"resumo {phase}",
    }


def _text(author, text, state_delta=None):
    return Event(
        author=author,
        invocation_id="inv",
        content=types.Content(role="model", parts=[types.Part(text=text)]),
        actions=EventActions(state_delta=state_delta) if state_delta else EventActions(),
    )


def _pause(author, call_id="call-1", name="aguardar_resolucao_bloqueio", args=None):
    fc = types.FunctionCall(id=call_id, name=name, args=args or {"motivo": "requisitos bloqueados"})
    return Event(
        author=author,
        invocation_id="inv",
        content=types.Content(role="model", parts=[types.Part(function_call=fc)]),
        long_running_tool_ids={call_id},
    )


class _FakeSession:
    id = "inner-sid"
    user_id = "u"


class _FakeSessionService:
    async def create_session(self, *, app_name, user_id, state):
        return _FakeSession()


class _Fabrica:
    """Monta um Runner falso por pipeline, na ordem em que o orchestrator cria.

    `roteiro[nome]` é uma lista de "rodadas"; cada chamada a run_async consome
    uma rodada (lista de eventos ou callable que recebe new_message).
    """

    def __init__(self, roteiro):
        self.roteiro = {k: list(v) for k, v in roteiro.items()}
        self.criados: list[str] = []
        self.mensagens: dict[str, list[str]] = {}
        self.runners: dict[str, MagicMock] = {}

    def __call__(self, **kwargs):
        nome = kwargs["app_name"]
        self.criados.append(nome)
        runner = MagicMock()
        runner.session_service = _FakeSessionService()
        runner.close = AsyncMock(return_value=None)

        async def run_async(**kw) -> AsyncGenerator[Event, None]:
            msg = kw.get("new_message")
            textos = [p.text for p in (msg.parts if msg else []) if getattr(p, "text", None)]
            self.mensagens.setdefault(nome, []).append("\n".join(textos))
            rodada = self.roteiro[nome].pop(0) if self.roteiro.get(nome) else None
            eventos = rodada(msg) if callable(rodada) else (rodada or [_text(nome, f"{nome} ok")])
            for e in eventos:
                yield e

        runner.run_async = run_async
        self.runners[nome] = runner
        return runner


def _ok(nome, status="ok", artifacts=1, bloqueante=False, tokens=(100, 10), agente=None):
    def rodada(_msg):
        record_usage(*tokens, agent=agente or f"{nome}_agent")
        return [_text(nome, f"{nome} ok", {"phase_manifests": [_manifest(_PHASE[nome], status, artifacts, bloqueante)]})]
    return rodada


def _todos_ok():
    return {n: [_ok(n)] for n in _PHASE}


class _Ctx:
    def __init__(self, texto, state=None):
        self.user_content = types.Content(role="user", parts=[types.Part(text=texto)])
        self.user_id = "u"
        self.session = MagicMock()
        self.session.id = "outer-sid"
        self.session.state = state if state is not None else {}
        self.artifact_service = MagicMock()
        self.credential_service = MagicMock()
        self.plugin_manager = MagicMock()
        self.plugin_manager.plugins = []


async def _rodar(fabrica, monkeypatch, texto="Prompt completo do sistema de fotos", state=None):
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    monkeypatch.setattr("src.agents.orchestrator.agent.Runner", fabrica)
    orch = _PipelineOrchestrator(name="orchestrator", description="t")
    ctx = _Ctx(texto, state)
    eventos = [e async for e in orch._run_async_impl(ctx)]
    return orch, ctx, eventos


def _textos(eventos, autor="orchestrator"):
    return [
        p.text
        for e in eventos
        if e.author == autor and e.content
        for p in e.content.parts
        if p.text
    ]


# ── Comportamento padrão ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sem_flags_relatorio_e_state_inalterados(monkeypatch):
    roteiro = _todos_ok()
    roteiro["requirements_pipeline"] = [_ok("requirements_pipeline", "blocked", bloqueante=True)]
    fab = _Fabrica(roteiro)
    _, ctx, eventos = await _rodar(fab, monkeypatch)

    assert fab.criados == list(_PHASE)  # segue mesmo bloqueado (histórico)
    for chave in ("token_usage_agents", "token_usage_runs"):
        assert chave not in ctx.session.state
    final = _textos(eventos)[-1]
    assert final.startswith("**Consumo de tokens da execução**")
    assert "Consumo por agente" not in final



# ── Helpers de pausa ────────────────────────────────────────────────────────


def _roteiro_pausa_no_coder():
    roteiro = _todos_ok()
    roteiro["coding_review_pipeline"] = [
        lambda _m: [_pause("coding_review_pipeline")],
        lambda _m: [_text("coding_review_pipeline", "coder retomado")],
    ]
    return roteiro


# ── Contagem de tokens ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_persist_grava_json_e_state_a_cada_workflow(monkeypatch, _ambiente):
    monkeypatch.setenv("AI4ES_TOKEN_USAGE_PERSIST", "true")
    fab = _Fabrica(_todos_ok())
    _, ctx, eventos = await _rodar(fab, monkeypatch)

    checkpoints = [
        e for e in eventos
        if e.author == "orchestrator" and not e.content and "token_usage" in (e.actions.state_delta or {})
    ]
    assert len(checkpoints) == 4  # um por workflow concluído
    snap = json.loads((_ambiente / "token_usage.json").read_text(encoding="utf-8"))
    assert snap["status"] == "concluída"
    assert snap["current_run"]["total"] == {"input": 400, "output": 40}
    assert snap["current_run"]["agents"]["design"]["design_pipeline_agent"]["calls"] == 1
    assert "token_usage_agents" in ctx.session.state


@pytest.mark.asyncio
async def test_detail_mostra_consumo_por_agente(monkeypatch):
    monkeypatch.setenv("AI4ES_TOKEN_REPORT_DETAIL", "true")
    fab = _Fabrica(_todos_ok())
    _, _, eventos = await _rodar(fab, monkeypatch)
    final = _textos(eventos)[-1]
    assert "**Consumo por agente**" in final
    assert "| requisitos | requirements_pipeline_agent | 1 | 100 | 10 | 110 |" in final


@pytest.mark.asyncio
async def test_report_on_pause_emite_tabela_parcial(monkeypatch):
    monkeypatch.setenv("AI4ES_TOKEN_REPORT_ON_PAUSE", "true")
    fab = _Fabrica(_roteiro_pausa_no_coder())
    _, _, eventos = await _rodar(fab, monkeypatch)
    msg = _textos(eventos)[-1]
    assert "Execução pausada em **coder_reviewer**" in msg
    assert "| design | 100 | 10 | 110 |" in msg


@pytest.mark.asyncio
async def test_session_total_acumula_execucoes_da_sessao(monkeypatch):
    monkeypatch.setenv("AI4ES_TOKEN_SESSION_TOTAL", "true")
    state: dict = {}
    _, _, _ = await _rodar(_Fabrica(_todos_ok()), monkeypatch, state=state)
    _, _, eventos = await _rodar(_Fabrica(_todos_ok()), monkeypatch, state=state)

    assert [r["run"] for r in state["token_usage_runs"]] == [1, 2]
    final = _textos(eventos)[-1]
    assert "**Total da sessão** (2 execução(ões))" in final
    assert "| Total | 800 | 80 | 880 |" in final  # 2 execuções × 4 workflows
