import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import sys
import types as py_types

import pytest
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

sys.modules.setdefault("litellm", py_types.SimpleNamespace(drop_params=False))

from shared.cache.qa_agent_cache import QaAgentResponseCache


class FakeClock:
    def __init__(self, start: datetime | None = None):
        self.current = start or datetime(2026, 7, 22, 12, 0, 0)

    def __call__(self) -> datetime:
        return self.current

    def advance(self, **kwargs) -> None:
        self.current += timedelta(**kwargs)


@dataclass
class FakeContext:
    # ADK cria uma instância de contexto por hook; "actions" é o objeto
    # compartilhado entre before/after/on_error de uma mesma chamada real.
    actions: object = field(default_factory=object)


def make_request(text: str, model: str = "gemini-2.5-flash") -> LlmRequest:
    return LlmRequest(
        model=model,
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=text)])],
    )


def make_response(text: str) -> LlmResponse:
    return LlmResponse(
        content=types.Content(role="model", parts=[types.Part.from_text(text=text)])
    )


@pytest.mark.asyncio
async def test_cache_hit_mesma_pergunta_chama_modelo_uma_vez():
    clock = FakeClock()
    cache = QaAgentResponseCache(
        prompt_text="PROMPT-QA",
        database_url="sqlite:///:memory:",
        ttl_seconds=60,
        clock=clock,
    )

    model_calls = 0

    async def execute_once(question: str) -> str:
        nonlocal model_calls
        request = make_request(question)
        context = FakeContext()
        cached = await cache.before_model_callback(context, request)
        if cached is not None:
            return cached.content.parts[0].text
        model_calls += 1
        response = make_response("resposta-final")
        await cache.after_model_callback(context, response)
        return response.content.parts[0].text

    first = await execute_once("mesma pergunta")
    second = await execute_once("mesma pergunta")

    assert first == "resposta-final"
    assert second == "resposta-final"
    assert model_calls == 1


@pytest.mark.asyncio
async def test_cache_miss_grava_resposta():
    clock = FakeClock()
    cache = QaAgentResponseCache(
        prompt_text="PROMPT-QA",
        database_url="sqlite:///:memory:",
        ttl_seconds=60,
        clock=clock,
    )

    request = make_request("pergunta inédita")
    context = FakeContext()

    cached = await cache.before_model_callback(context, request)
    assert cached is None
    assert cache._pending_key(context) in cache._pending

    response = make_response("resultado salvo")
    await cache.after_model_callback(context, response)

    replay_context = FakeContext()
    replay = await cache.before_model_callback(replay_context, request)
    assert replay is not None
    assert replay.content.parts[0].text == "resultado salvo"


@pytest.mark.asyncio
async def test_ttl_expirado_reprocessa():
    clock = FakeClock()
    cache = QaAgentResponseCache(
        prompt_text="PROMPT-QA",
        database_url="sqlite:///:memory:",
        ttl_seconds=10,
        clock=clock,
    )

    model_calls = 0

    async def execute(question: str, answer: str) -> str:
        nonlocal model_calls
        request = make_request(question)
        context = FakeContext()
        cached = await cache.before_model_callback(context, request)
        if cached is not None:
            return cached.content.parts[0].text
        model_calls += 1
        response = make_response(answer)
        await cache.after_model_callback(context, response)
        return answer

    first = await execute("pergunta ttl", "versao-1")
    clock.advance(seconds=11)
    second = await execute("pergunta ttl", "versao-2")

    assert first == "versao-1"
    assert second == "versao-2"
    assert model_calls == 2


@pytest.mark.asyncio
async def test_concorrencia_mesma_chave_chama_modelo_uma_vez():
    clock = FakeClock()
    cache = QaAgentResponseCache(
        prompt_text="PROMPT-QA",
        database_url="sqlite:///:memory:",
        ttl_seconds=60,
        wait_timeout_seconds=2,
        clock=clock,
    )

    model_calls = 0
    gate = asyncio.Event()

    async def invoke(question: str) -> str:
        nonlocal model_calls
        request = make_request(question)
        context = FakeContext()
        cached = await cache.before_model_callback(context, request)
        if cached is not None:
            return cached.content.parts[0].text

        model_calls += 1
        await gate.wait()
        response = make_response("resposta concorrente")
        await cache.after_model_callback(context, response)
        return response.content.parts[0].text

    tasks = [asyncio.create_task(invoke("pergunta concorrente")) for _ in range(5)]
    await asyncio.sleep(0)
    gate.set()
    results = await asyncio.gather(*tasks)

    assert results == ["resposta concorrente"] * 5
    assert model_calls == 1


@pytest.mark.asyncio
async def test_erro_do_modelo_libera_fluxo_da_mesma_chave():
    clock = FakeClock()
    cache = QaAgentResponseCache(
        prompt_text="PROMPT-QA",
        database_url="sqlite:///:memory:",
        ttl_seconds=60,
        wait_timeout_seconds=2,
        clock=clock,
    )

    release_called = asyncio.Event()
    original_release_lock = cache._backend.release_lock
    lock_handle = object()

    def release_lock_spy(lock_handle):
        release_called.set()
        return original_release_lock(lock_handle)

    cache._backend.release_lock = release_lock_spy  # type: ignore[method-assign]

    async def fake_safe_acquire_lock(cache_key: str):
        return lock_handle

    cache._safe_acquire_lock = fake_safe_acquire_lock  # type: ignore[method-assign]

    request = make_request("pergunta com falha")
    leader_context = FakeContext()
    follower_context = FakeContext()

    cached = await cache.before_model_callback(leader_context, request)
    assert cached is None
    assert cache._pending_key(leader_context) in cache._pending

    follower_task = asyncio.create_task(cache.before_model_callback(follower_context, request))
    await asyncio.sleep(0)
    assert not follower_task.done()

    await cache.on_model_error_callback(
        leader_context,
        request,
        RuntimeError("falha simulada"),
    )

    follower_result = await asyncio.wait_for(follower_task, timeout=2)

    assert release_called.is_set()
    assert follower_result is None
    assert cache._pending_key(leader_context) not in cache._pending