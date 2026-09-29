"""Testes do plugin de guarda (contagem de rodadas e restauração do ambiente)."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from types import SimpleNamespace

from benchmarks.coding_review.swebench import environment
from benchmarks.coding_review.swebench._testutils import ADK_DIR
from benchmarks.coding_review.swebench.guard_plugin import (
    CODER_AGENT_NAME,
    EXECUTOR_AGENT_NAME,
    BenchmarkGuardPlugin,
)

IMAGEM = "img:latest"


def _turno(plugin: BenchmarkGuardPlugin, nome: str):
    return asyncio.run(
        plugin.before_agent_callback(agent=SimpleNamespace(name=nome), callback_context=None)
    )


def _plugin(tmp_path: Path) -> BenchmarkGuardPlugin:
    environment.write_benchmark_files(tmp_path, IMAGEM)
    plugin = BenchmarkGuardPlugin(tmp_path)
    plugin.start_instance(IMAGEM)
    return plugin


def test_conta_rodadas_do_executor_e_turnos_do_coder(tmp_path: Path):
    plugin = _plugin(tmp_path)
    for _ in range(3):
        assert _turno(plugin, CODER_AGENT_NAME) is None
        assert _turno(plugin, EXECUTOR_AGENT_NAME) is None
    _turno(plugin, "implementation_validator")

    resumo = plugin.summary()
    assert resumo["rodadas_executor"] == 3
    assert resumo["turnos_coder"] == 3
    assert resumo["ocorrencias"] == []
    assert resumo["ambiente_violado"] is False


def test_restaura_o_ambiente_e_registra_a_rodada(tmp_path: Path):
    plugin = _plugin(tmp_path)
    _turno(plugin, EXECUTOR_AGENT_NAME)
    # O coder segue o prompt de sistema e desfaz o ambiente.
    (tmp_path / "Dockerfile").unlink()
    (tmp_path / "run.json").write_text(json.dumps({"surface": "none", "sandbox": "direct",
                                                    "build": ["python -m venv venv"]}))
    _turno(plugin, EXECUTOR_AGENT_NAME)

    resumo = plugin.summary()
    assert (tmp_path / "Dockerfile").is_file()
    assert json.loads((tmp_path / "run.json").read_text())["sandbox"] == "docker"
    assert resumo["ambiente_violado"] is True
    assert resumo["venv_no_manifesto"] is True
    assert {(o["rodada"], o["tipo"]) for o in resumo["ocorrencias"]} == {
        (2, environment.VIOLACAO_DOCKERFILE),
        (2, environment.VIOLACAO_SANDBOX),
        (2, environment.OBSERVACAO_VENV),
    }


def test_nova_instancia_zera_os_contadores(tmp_path: Path):
    plugin = _plugin(tmp_path)
    _turno(plugin, EXECUTOR_AGENT_NAME)
    plugin.start_instance(IMAGEM)
    assert plugin.summary()["rodadas_executor"] == 0


def test_falha_na_guarda_nao_derruba_o_loop(tmp_path: Path, monkeypatch):
    plugin = _plugin(tmp_path)

    def _explode(*_args, **_kwargs):
        raise OSError("disco cheio")

    monkeypatch.setattr(environment, "ensure_benchmark_files", _explode)
    assert _turno(plugin, EXECUTOR_AGENT_NAME) is None
    assert plugin.summary()["erro_na_guarda"] is True


def test_plugin_roda_no_runner_antes_do_callback_do_agente(tmp_path: Path):
    """No ADK real: o plugin conta as rodadas e restaura o ambiente ANTES do
    `before_agent_callback` do executor (é lá que fica o gate da produção)."""
    from google.adk.agents import BaseAgent, LoopAgent
    from google.adk.apps import App
    from google.adk.events.event import Event
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types

    class _Stub(BaseAgent):
        async def _run_async_impl(self, ctx):
            yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                        content=types.Content(role="model", parts=[types.Part(text="ok")]))

    visto_pelo_gate: list[bool] = []

    def _gate(callback_context):
        visto_pelo_gate.append((tmp_path / "Dockerfile").is_file())
        (tmp_path / "Dockerfile").unlink()  # simula o coder apagando entre rodadas
        return None

    executor = _Stub(name=EXECUTOR_AGENT_NAME, before_agent_callback=_gate)
    loop = LoopAgent(name="loop", sub_agents=[_Stub(name=CODER_AGENT_NAME), executor],
                     max_iterations=3)
    plugin = _plugin(tmp_path)

    async def _rodar():
        runner = Runner(app=App(name="teste_guarda", root_agent=loop, plugins=[plugin]),
                        session_service=InMemorySessionService())
        sessao = await runner.session_service.create_session(app_name="teste_guarda",
                                                             user_id="u")
        async for _ in runner.run_async(
            user_id="u", session_id=sessao.id,
            new_message=types.Content(role="user", parts=[types.Part(text="vai")]),
        ):
            pass
        await runner.close()

    asyncio.run(_rodar())

    resumo = plugin.summary()
    assert resumo["rodadas_executor"] == 3 and resumo["turnos_coder"] == 3
    assert visto_pelo_gate == [True, True, True]
    assert [o["rodada"] for o in resumo["ocorrencias"]] == [2, 3]


def test_nomes_dos_agentes_batem_com_a_producao():
    coder = (ADK_DIR / "src/agents/workflow_coding_review/coder/agent.py").read_text()
    executor = (ADK_DIR / "src/agents/workflow_coding_review/executor/agent.py").read_text()
    assert re.search(rf'name="{CODER_AGENT_NAME}"', coder)
    assert re.search(rf'name="{EXECUTOR_AGENT_NAME}"', executor)


def _resposta(prompt: int, completion: int, *, partial: bool = False):
    uso = SimpleNamespace(prompt_token_count=prompt, candidates_token_count=completion)
    return SimpleNamespace(usage_metadata=uso, partial=partial)


def test_contabiliza_uso_de_llm_por_agente_inclusive_o_validador(tmp_path: Path):
    plugin = _plugin(tmp_path)

    def _modelo(agente, resposta):
        return asyncio.run(plugin.after_model_callback(
            callback_context=SimpleNamespace(agent_name=agente), llm_response=resposta
        ))

    assert _modelo(CODER_AGENT_NAME, _resposta(100, 10)) is None
    _modelo(CODER_AGENT_NAME, _resposta(50, 5))
    _modelo("implementation_validator", _resposta(30, 3))
    _modelo(EXECUTOR_AGENT_NAME, _resposta(9, 9, partial=True))  # parcial não conta
    _modelo(EXECUTOR_AGENT_NAME, SimpleNamespace(usage_metadata=None))

    totais = plugin.usage_totals()
    assert (totais["llm_interactions"], totais["prompt_tokens"], totais["completion_tokens"]) == (
        3, 180, 18
    )
    assert totais["por_agente"]["implementation_validator"]["prompt_tokens"] == 30
    plugin.start_instance(IMAGEM)
    assert plugin.usage_totals()["llm_interactions"] == 0
