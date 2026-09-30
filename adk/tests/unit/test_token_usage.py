"""Testes da contabilização de tokens por workflow."""

import asyncio
from types import SimpleNamespace

from shared.token_usage import TokenUsage, TokenUsagePlugin, bind_stage


def _resp(prompt, cand, thoughts=None, partial=False):
    meta = SimpleNamespace(
        prompt_token_count=prompt,
        candidates_token_count=cand,
        thoughts_token_count=thoughts,
    )
    return SimpleNamespace(usage_metadata=meta, partial=partial)


def _call(plugin, resp):
    asyncio.run(plugin.after_model_callback(callback_context=None, llm_response=resp))


def test_plugin_atribui_tokens_ao_workflow_corrente():
    usage, plugin = TokenUsage(), TokenUsagePlugin()
    bind_stage(usage, "requirements_pipeline")
    _call(plugin, _resp(100, 10))
    bind_stage(usage, "qa_pipeline")
    _call(plugin, _resp(50, 5, thoughts=5))
    assert usage.stages["requisitos"] == {"input": 100, "output": 10}
    assert usage.stages["qa"] == {"input": 50, "output": 10}
    assert (usage.total_input, usage.total_output) == (150, 20)


def test_plugin_ignora_parciais_e_sem_metadata():
    usage, plugin = TokenUsage(), TokenUsagePlugin()
    bind_stage(usage, "design_pipeline")
    _call(plugin, _resp(10, 1, partial=True))
    _call(plugin, SimpleNamespace(usage_metadata=None, partial=False))
    assert usage.stages == {}


def test_roundtrip_e_relatorio():
    usage = TokenUsage()
    usage.add("coder_reviewer", 1000, 200)
    restored = TokenUsage.from_dict(usage.to_dict())
    report = restored.format_report()
    assert "| Total | 1,000 | 200 | 1,200 |" in report
    assert "| coder_reviewer | 1,000 | 200 | 1,200 |" in report
    assert "| requisitos | 0 | 0 | 0 |" in report


def test_record_litellm_response_objeto_e_dict():
    from shared.token_usage import record_litellm_response

    usage = TokenUsage()
    bind_stage(usage, "qa_pipeline")
    record_litellm_response(
        SimpleNamespace(usage=SimpleNamespace(prompt_tokens=30, completion_tokens=7))
    )
    record_litellm_response({"usage": {"prompt_tokens": 3, "completion_tokens": 1}})
    record_litellm_response(SimpleNamespace(usage=None))
    assert usage.stages["qa"] == {"input": 33, "output": 8}


def test_instrument_genai_client_contabiliza_e_nao_duplica_wrapper():
    from shared.token_usage import instrument_genai_client

    resposta = SimpleNamespace(
        usage_metadata=SimpleNamespace(
            prompt_token_count=40, candidates_token_count=4, thoughts_token_count=None
        )
    )
    models = SimpleNamespace(generate_content=lambda **kw: resposta)
    client = SimpleNamespace(models=models)
    instrument_genai_client(client)
    instrument_genai_client(client)  # idempotente

    usage = TokenUsage()
    bind_stage(usage, "coding_review_pipeline")
    assert client.models.generate_content(model="x", contents="y") is resposta
    assert usage.stages["coder_reviewer"] == {"input": 40, "output": 4}


def test_contexto_propagado_para_thread_com_copy_context():
    import concurrent.futures
    import contextvars

    from shared.token_usage import record_usage

    usage = TokenUsage()
    bind_stage(usage, "qa_pipeline")
    with concurrent.futures.ThreadPoolExecutor() as pool:
        pool.submit(contextvars.copy_context().run, record_usage, 5, 1).result()
    assert usage.stages["qa"] == {"input": 5, "output": 1}


# --- Guarda de regressão: chamadas LLM fora do alcance da contagem ---

from pathlib import Path
import re

_ADK_ROOT = Path(__file__).resolve().parents[2]
_SCAN_DIRS = ("src", "shared")
# Fora do escopo do orchestrator ou contagem desprezível/intencionalmente omitida.
_COMPLETION_ALLOWLIST = {"shared/preflight.py"}
_RUNNER_ALLOWLIST = {"src/agents/workflow_taco/agent.py"}


def _py_files():
    for d in _SCAN_DIRS:
        for p in (_ADK_ROOT / d).rglob("*.py"):
            yield p.relative_to(_ADK_ROOT).as_posix(), p.read_text(encoding="utf-8")


def test_toda_chamada_litellm_direta_registra_tokens():
    padrao = re.compile(r"\ba?completion\(")
    faltando = [
        rel for rel, src in _py_files()
        if rel not in _COMPLETION_ALLOWLIST
        and padrao.search(re.sub(r"def \w*completion\w*\(", "", src))
        and "record_litellm_response" not in src
    ]
    assert not faltando, f"litellm.completion sem record_litellm_response: {faltando}"


def test_todo_runner_isolado_recebe_plugins():
    faltando = []
    for rel, src in _py_files():
        if rel in _RUNNER_ALLOWLIST:
            continue
        for m in re.finditer(r"\bRunner\(", src):
            trecho = src[m.end():m.end() + 600].split("\n        )", 1)[0]
            if "plugins=" not in trecho:
                faltando.append(rel)
    assert not faltando, f"Runner sem plugins= (tokens não contados): {faltando}"


# --- Relatório parcial quando a execução falha ---


def test_orchestrator_emite_relatorio_parcial_e_propaga_erro(monkeypatch):
    import pytest
    from google.genai import types

    import src.agents.orchestrator.agent as orch
    from shared.preflight import PreflightResult
    from shared.token_usage import record_usage

    async def _preflight_ok():
        return PreflightResult(ok=True)

    async def _fresh_que_falha(self, ctx, outer_sid, user_text, usage):
        bind_stage(usage, "requirements_pipeline")
        record_usage(1200, 300)
        yield orch._PipelineOrchestrator._make_text_event("x", "evento normal")
        raise RuntimeError("Rate limit reached for gpt-4.1")

    monkeypatch.setattr(orch, "ensure_llm_ready", _preflight_ok)
    monkeypatch.setattr(
        orch._PipelineOrchestrator, "_handle_fresh_run", _fresh_que_falha
    )

    ctx = SimpleNamespace(
        session=SimpleNamespace(state={}, id="s1"),
        user_content=types.Content(role="user", parts=[types.Part(text="oi")]),
    )

    async def _coletar():
        eventos = []
        with pytest.raises(RuntimeError, match="Rate limit"):
            async for ev in orch.root_agent._run_async_impl(ctx):
                eventos.append(ev)
        return eventos

    eventos = asyncio.run(_coletar())
    texto = eventos[-1].content.parts[0].text
    assert "(parcial)" in texto
    assert "no workflow **requisitos**" in texto
    assert "RuntimeError: Rate limit reached" in texto
    assert "| requisitos | 1,200 | 300 | 1,500 |" in texto
    assert ctx.session.state["token_usage"] == {
        "requisitos": {"input": 1200, "output": 300}
    }
    assert eventos[-1].actions.state_delta["token_usage"] == {
        "requisitos": {"input": 1200, "output": 300}
    }


def test_orchestrator_relatorio_parcial_desembrulha_exception_group(monkeypatch):
    import pytest
    from google.genai import types

    import src.agents.orchestrator.agent as orch
    from shared.preflight import PreflightResult

    async def _preflight_ok():
        return PreflightResult(ok=True)

    async def _fresh_que_falha(self, ctx, outer_sid, user_text, usage):
        bind_stage(usage, "design_pipeline")
        if False:
            yield
        raise ExceptionGroup("unhandled errors in a TaskGroup", [ValueError("429 TPM")])

    monkeypatch.setattr(orch, "ensure_llm_ready", _preflight_ok)
    monkeypatch.setattr(orch._PipelineOrchestrator, "_handle_fresh_run", _fresh_que_falha)
    ctx = SimpleNamespace(
        session=SimpleNamespace(state={}, id="s2"),
        user_content=types.Content(role="user", parts=[types.Part(text="oi")]),
    )

    async def _coletar():
        eventos = []
        with pytest.raises(ExceptionGroup):
            async for ev in orch.root_agent._run_async_impl(ctx):
                eventos.append(ev)
        return eventos

    texto = asyncio.run(_coletar())[-1].content.parts[0].text
    assert "no workflow **design**" in texto
    assert "`ValueError: 429 TPM`" in texto
