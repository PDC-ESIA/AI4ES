"""
test_llm_router.py
==================
Testes unitários para o módulo shared/llm (router, client, get_model).

Execute com:
    pytest tests/unit/test_llm_router.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from shared.llm.router import _build_model_list, create_router
from shared.llm.client import RouterLiteLLMClient, MODEL_NAME


# ===========================================================================
# 1. Testes do Router
# ===========================================================================


class TestBuildModelList:
    def test_defaults(self, monkeypatch):
        monkeypatch.delenv("ADK_LLM_MODEL", raising=False)
        monkeypatch.delenv("ADK_LLM_FALLBACK_MODEL_1", raising=False)
        monkeypatch.delenv("ADK_LLM_FALLBACK_MODEL_2", raising=False)

        deployments = _build_model_list()

        assert len(deployments) == 3
        assert deployments[0]["litellm_params"]["model"] == "github_copilot/gpt-4"
        assert deployments[1]["litellm_params"]["model"] == "openrouter/meta-llama/llama-4-scout"
        assert deployments[2]["litellm_params"]["model"] == "openrouter/google/gemini-2.0-flash"

    def test_custom_env(self, monkeypatch):
        monkeypatch.setenv("ADK_LLM_MODEL", "custom/primary")
        monkeypatch.setenv("ADK_LLM_FALLBACK_MODEL_1", "custom/fallback1")
        monkeypatch.setenv("ADK_LLM_FALLBACK_MODEL_2", "custom/fallback2")

        deployments = _build_model_list()

        assert deployments[0]["litellm_params"]["model"] == "custom/primary"
        assert deployments[1]["litellm_params"]["model"] == "custom/fallback1"
        assert deployments[2]["litellm_params"]["model"] == "custom/fallback2"

    def test_deployments_order(self):
        deployments = _build_model_list()

        assert deployments[0]["litellm_params"]["order"] == 1
        assert deployments[1]["litellm_params"]["order"] == 2
        assert deployments[2]["litellm_params"]["order"] == 3


class TestCreateRouter:
    def test_returns_router_instance(self):
        router = create_router()
        assert type(router).__name__ == "Router"

    def test_config(self):
        router = create_router()
        assert router.num_retries == 2
        assert router.cooldown_time == 10


# ===========================================================================
# 2. Testes do Client
# ===========================================================================


class TestRouterLiteLLMClient:
    @pytest.mark.asyncio
    async def test_acompletion_delegates_to_router(self):
        mock_router = MagicMock()
        mock_router.acompletion = AsyncMock(return_value="response")
        client = RouterLiteLLMClient(mock_router)

        result = await client.acompletion(
            model="ignored", messages=[{"role": "user", "content": "hi"}]
        )

        mock_router.acompletion.assert_called_once()
        call_kwargs = mock_router.acompletion.call_args
        assert call_kwargs.kwargs["model"] == MODEL_NAME
        assert result == "response"

    def test_completion_delegates_to_router(self):
        mock_router = MagicMock()
        mock_router.completion = MagicMock(return_value="response")
        client = RouterLiteLLMClient(mock_router)

        result = client.completion(
            model="ignored", messages=[{"role": "user", "content": "hi"}]
        )

        mock_router.completion.assert_called_once()
        call_kwargs = mock_router.completion.call_args
        assert call_kwargs.kwargs["model"] == MODEL_NAME
        assert result == "response"

    @pytest.mark.asyncio
    async def test_acompletion_passes_messages_and_tools(self):
        mock_router = MagicMock()
        mock_router.acompletion = AsyncMock(return_value="ok")
        client = RouterLiteLLMClient(mock_router)

        messages = [{"role": "user", "content": "test"}]
        tools = [{"type": "function", "function": {"name": "foo"}}]

        await client.acompletion(model="x", messages=messages, tools=tools)

        call_kwargs = mock_router.acompletion.call_args.kwargs
        assert call_kwargs["messages"] == messages
        assert call_kwargs["tools"] == tools

    @pytest.mark.asyncio
    async def test_acompletion_passes_kwargs(self):
        mock_router = MagicMock()
        mock_router.acompletion = AsyncMock(return_value="ok")
        client = RouterLiteLLMClient(mock_router)

        await client.acompletion(
            model="x",
            messages=[],
            tools=None,
            temperature=0.5,
            max_tokens=100,
        )

        call_kwargs = mock_router.acompletion.call_args.kwargs
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 100


# ===========================================================================
# 3. Testes do get_model()
# ===========================================================================


class TestGetModel:
    def test_returns_litellm_instance(self):
        from shared.llm import get_model

        model = get_model()
        assert type(model).__name__ == "LiteLlm"

    def test_uses_router_client(self):
        from shared.llm import get_model

        model = get_model()
        assert isinstance(model.llm_client, RouterLiteLLMClient)

    def test_model_name(self):
        from shared.llm import get_model

        model = get_model()
        assert model.model == MODEL_NAME

    def test_singleton_router(self):
        from shared.llm import _client, get_model

        model1 = get_model()
        model2 = get_model()
        # Ambos usam o mesmo client (e portanto o mesmo router)
        assert model1.llm_client is model2.llm_client
        assert model1.llm_client is _client
