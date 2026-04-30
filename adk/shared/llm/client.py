"""Client LiteLLM que delega chamadas para o Router (fallback multi-nível)."""

from __future__ import annotations

from typing import Any

from google.adk.models.lite_llm import LiteLLMClient
from litellm import Router


MODEL_NAME = "adk-model"


class RouterLiteLLMClient(LiteLLMClient):
    """Substitui chamadas diretas ao litellm por chamadas ao Router.

    Opcionalmente injeta metadata do Langfuse para rastreamento por agente.
    """

    def __init__(self, router: Router, agent_name: str | None = None):
        super().__init__()
        self._router = router
        self._agent_name = agent_name

    def _langfuse_metadata(self) -> dict:
        """Retorna metadata para o Langfuse identificar o agente."""
        if not self._agent_name:
            return {}
        return {
            "metadata": {
                "generation_name": self._agent_name,
                "trace_name": self._agent_name,
            }
        }

    async def acompletion(self, model: str, messages: list, tools: list | None = None, **kwargs: Any):
        kwargs.update(self._langfuse_metadata())
        return await self._router.acompletion(
            model=MODEL_NAME,
            messages=messages,
            tools=tools,
            **kwargs,
        )

    def completion(self, model: str, messages: list, tools: list | None = None, stream: bool = False, **kwargs: Any):
        kwargs.update(self._langfuse_metadata())
        return self._router.completion(
            model=MODEL_NAME,
            messages=messages,
            tools=tools,
            stream=stream,
            **kwargs,
        )
