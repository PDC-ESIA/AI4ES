"""Testes do plugin de guarda (contagem de rodadas e restauração do ambiente)."""

from __future__ import annotations

import asyncio
import json
import re

import pytest
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


class _ErroRateLimit(Exception):
    pass


_ErroRateLimit.__name__ = "RateLimitError"


class _ModeloFalso:
    """Modelo que falha com os erros dados e depois responde."""

    def __init__(self, erros):
        self._erros = list(erros)
        self.chamadas = 0

    async def generate_content_async(self, llm_request, stream=False):
        self.chamadas += 1
        if self._erros:
            raise self._erros.pop(0)
        yield SimpleNamespace(texto="resposta", partial=False)


def _contexto(modelo):
    agente = SimpleNamespace(canonical_model=modelo)
    return SimpleNamespace(_invocation_context=SimpleNamespace(agent=agente))


def _plugin_com_pausa(tmp_path: Path, esperas: list, maximo: float = 1000.0):
    async def _dormir(segundos):
        esperas.append(segundos)

    plugin = BenchmarkGuardPlugin(tmp_path, rate_limit_initial_wait=60,
                                  rate_limit_max_wait=maximo, sleep=_dormir)
    plugin.start_instance(IMAGEM)
    return plugin


def test_rate_limit_pausa_e_repete_a_mesma_chamada(tmp_path: Path):
    esperas: list = []
    plugin = _plugin_com_pausa(tmp_path, esperas)
    modelo = _ModeloFalso([_ErroRateLimit("429 utility models")])

    resposta = asyncio.run(plugin.on_model_error_callback(
        callback_context=_contexto(modelo), llm_request=object(),
        error=_ErroRateLimit("exceeded your rate limit"),
    ))

    assert resposta.texto == "resposta"
    assert esperas == [60, 120]  # 1ª repetição ainda limitada; a 2ª passa
    assert modelo.chamadas == 2
    assert plugin.summary()["pausas_rate_limit_s"] == [60, 120]


def test_pausa_respeita_o_teto_e_devolve_o_erro_ao_loop(tmp_path: Path):
    esperas: list = []
    plugin = _plugin_com_pausa(tmp_path, esperas, maximo=200)
    modelo = _ModeloFalso([_ErroRateLimit("429")] * 5)
    resposta = asyncio.run(plugin.on_model_error_callback(
        callback_context=_contexto(modelo), llm_request=object(),
        error=_ErroRateLimit("rate limit"),
    ))
    assert resposta is None  # 60 + 120 = 180; a próxima (240) passaria do teto
    assert esperas == [60, 120]


def test_estouro_de_contexto_e_outros_erros_nao_sao_pausados(tmp_path: Path):
    esperas: list = []
    plugin = _plugin_com_pausa(tmp_path, esperas)
    modelo = _ModeloFalso([])
    for erro in (
        ValueError("prompt token count of 142900 exceeds the limit of 128000"),
        ValueError("outra falha"),
    ):
        assert asyncio.run(plugin.on_model_error_callback(
            callback_context=_contexto(modelo), llm_request=object(), error=erro,
        )) is None
    assert esperas == [] and modelo.chamadas == 0


def test_erro_diferente_na_repeticao_e_propagado(tmp_path: Path):
    import pytest

    esperas: list = []
    plugin = _plugin_com_pausa(tmp_path, esperas)
    modelo = _ModeloFalso([ValueError("prompt token count of 200000 exceeds the limit of 128000")])
    with pytest.raises(ValueError, match="exceeds the limit"):
        asyncio.run(plugin.on_model_error_callback(
            callback_context=_contexto(modelo), llm_request=object(),
            error=_ErroRateLimit("429"),
        ))


def test_pausa_funciona_com_um_llmagent_real_do_adk(tmp_path: Path):
    from google.adk.agents import LlmAgent
    from google.adk.apps import App
    from google.adk.models.base_llm import BaseLlm
    from google.adk.models.llm_response import LlmResponse
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types

    class _LlmComRateLimit(BaseLlm):
        chamadas: int = 0

        async def generate_content_async(self, llm_request, stream=False):
            self.chamadas += 1
            if self.chamadas == 1:
                raise _ErroRateLimit("429 you've exceeded your rate limit for utility models")
            yield LlmResponse(content=types.Content(role="model",
                                                    parts=[types.Part(text="ok depois da pausa")]))

    llm = _LlmComRateLimit(model="falso")
    agente = LlmAgent(name=CODER_AGENT_NAME, model=llm, instruction="responda")
    esperas: list = []
    plugin = _plugin_com_pausa(tmp_path, esperas)
    environment.write_benchmark_files(tmp_path, IMAGEM)

    async def _rodar():
        runner = Runner(app=App(name="teste_pausa", root_agent=agente, plugins=[plugin]),
                        session_service=InMemorySessionService())
        sessao = await runner.session_service.create_session(app_name="teste_pausa", user_id="u")
        textos = []
        async for evento in runner.run_async(
            user_id="u", session_id=sessao.id,
            new_message=types.Content(role="user", parts=[types.Part(text="oi")]),
        ):
            if evento.content and evento.content.parts:
                textos += [p.text for p in evento.content.parts if p.text]
        await runner.close()
        return textos

    textos = asyncio.run(_rodar())
    assert textos[-1] == "ok depois da pausa"
    assert llm.chamadas == 2 and esperas == [60]


class _Relogio:
    def __init__(self):
        self.agora = 1000.0

    def __call__(self):
        return self.agora


def _plugin_com_ritmo(tmp_path: Path, tpm: int):
    relogio, esperas = _Relogio(), []

    async def _dormir(segundos):
        esperas.append(segundos)
        relogio.agora += segundos

    plugin = BenchmarkGuardPlugin(tmp_path, max_tokens_per_minute=tpm,
                                  sleep=_dormir, clock=relogio)
    plugin.start_instance(IMAGEM)
    return plugin, relogio, esperas


def _consumir(plugin, prompt: int, saida: int = 0, agente: str = CODER_AGENT_NAME):
    uso = SimpleNamespace(prompt_token_count=prompt, candidates_token_count=saida)
    asyncio.run(plugin.after_model_callback(
        callback_context=SimpleNamespace(agent_name=agente),
        llm_response=SimpleNamespace(usage_metadata=uso, partial=False),
    ))


def _antes_da_chamada(plugin):
    return asyncio.run(plugin.before_model_callback(
        callback_context=SimpleNamespace(agent_name=CODER_AGENT_NAME), llm_request=object()
    ))


def test_ritmo_faz_a_chamada_esperar_para_caber_no_teto(tmp_path: Path):
    plugin, relogio, esperas = _plugin_com_ritmo(tmp_path, tpm=50_000)
    assert _antes_da_chamada(plugin) is None and esperas == []  # sem consumo, sem espera
    _consumir(plugin, prompt=100_000)  # 2 min do teto; 1 min de folga
    _antes_da_chamada(plugin)
    assert esperas == [60.0]
    assert plugin.summary()["pausa_ritmo_s"] == 60.0


def test_ritmo_permite_rajada_curta_e_acumula_divida(tmp_path: Path):
    plugin, relogio, esperas = _plugin_com_ritmo(tmp_path, tpm=60_000)
    _consumir(plugin, prompt=30_000)  # 30 s de teto: dentro da folga de 60 s
    _antes_da_chamada(plugin)
    assert esperas == []
    _consumir(plugin, prompt=60_000)  # dívida total: 90 s
    _antes_da_chamada(plugin)
    assert esperas == [pytest.approx(30.0)]
    relogio.agora += 600  # muito tempo depois, a dívida já foi paga
    _antes_da_chamada(plugin)
    assert len(esperas) == 1


def test_ritmo_desligado_e_divida_sobrevive_a_troca_de_instancia(tmp_path: Path):
    desligado, _, esperas = _plugin_com_ritmo(tmp_path, tpm=0)
    _consumir(desligado, prompt=10_000_000)
    _antes_da_chamada(desligado)
    assert esperas == []

    plugin, _, esperas = _plugin_com_ritmo(tmp_path, tpm=50_000)
    _consumir(plugin, prompt=100_000)
    plugin.start_instance(IMAGEM)  # o provedor não zera o limite entre instâncias
    _antes_da_chamada(plugin)
    assert esperas == [60.0]


def test_ritmo_funciona_com_um_llmagent_real_do_adk(tmp_path: Path):
    from google.adk.agents import LlmAgent
    from google.adk.apps import App
    from google.adk.models.base_llm import BaseLlm
    from google.adk.models.llm_response import LlmResponse
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types

    class _LlmGrande(BaseLlm):
        async def generate_content_async(self, llm_request, stream=False):
            yield LlmResponse(
                content=types.Content(role="model", parts=[types.Part(text="ok")]),
                usage_metadata=types.GenerateContentResponseUsageMetadata(
                    prompt_token_count=100_000, candidates_token_count=0
                ),
            )

    plugin, _, esperas = _plugin_com_ritmo(tmp_path, tpm=50_000)
    agente = LlmAgent(name=CODER_AGENT_NAME, model=_LlmGrande(model="falso"), instruction="r")

    async def _rodar():
        runner = Runner(app=App(name="teste_ritmo", root_agent=agente, plugins=[plugin]),
                        session_service=InMemorySessionService())
        sessao = await runner.session_service.create_session(app_name="teste_ritmo", user_id="u")
        for texto in ("primeira", "segunda"):
            async for _ in runner.run_async(
                user_id="u", session_id=sessao.id,
                new_message=types.Content(role="user", parts=[types.Part(text=texto)]),
            ):
                pass
        await runner.close()

    asyncio.run(_rodar())
    assert esperas == [60.0]  # a 2ª chamada esperou o consumo da 1ª caber no teto
    assert plugin.usage_totals()["prompt_tokens"] == 200_000


def test_tempo_pausado_soma_ritmo_e_rate_limit_e_zera_na_nova_instancia(tmp_path: Path):
    plugin, relogio, _ = _plugin_com_ritmo(tmp_path, tpm=50_000)
    assert plugin.tempo_pausado_s() == 0.0
    _consumir(plugin, prompt=100_000)
    _antes_da_chamada(plugin)  # dorme 60 s de ritmo
    assert plugin.tempo_pausado_s() == 60.0
    plugin.start_instance(IMAGEM)
    assert plugin.tempo_pausado_s() == 0.0


def test_tempo_pausado_inclui_a_pausa_em_curso(tmp_path: Path):
    relogio = _Relogio()
    medidas = []

    async def _dormir(segundos):
        relogio.agora += 30.0
        medidas.append(plugin.tempo_pausado_s())  # no meio da pausa
        relogio.agora += segundos - 30.0

    plugin = BenchmarkGuardPlugin(tmp_path, max_tokens_per_minute=50_000,
                                  sleep=_dormir, clock=relogio)
    plugin.start_instance(IMAGEM)
    _consumir(plugin, prompt=100_000)
    _antes_da_chamada(plugin)
    assert medidas == [30.0]
    assert plugin.tempo_pausado_s() == 60.0
