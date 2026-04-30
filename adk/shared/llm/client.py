"""Client LiteLLM que delega chamadas para o Router (fallback multi-nível)."""

from __future__ import annotations

from typing import Any

from google.adk.models.lite_llm import LiteLLMClient
from litellm import Router


MODEL_NAME = "adk-model"


class RouterLiteLLMClient(LiteLLMClient):
    """Substitui chamadas diretas ao litellm por chamadas ao Router."""

    def __init__(self, router: Router):
        super().__init__()
        self._router = router

    async def acompletion(self, model: str, messages: list, tools: list | None = None, **kwargs: Any):
        return await self._router.acompletion(
            model=MODEL_NAME,
            messages=messages,
            tools=tools,
            **kwargs,
        )

    def completion(self, model: str, messages: list, tools: list | None = None, stream: bool = False, **kwargs: Any):
        return self._router.completion(
            model=MODEL_NAME,
            messages=messages,
            tools=tools,
            stream=stream,
            **kwargs,
        )
