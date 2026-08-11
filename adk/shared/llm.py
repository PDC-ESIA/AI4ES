"""LiteLlm customizado para o provider github_copilot.

O LiteLLM envia o header ``X-Initiator: agent`` sempre que o histórico da
conversa contém mensagens com role ``assistant``/``tool``. Em pipelines
multiagente do ADK isso acontece em praticamente toda chamada, e o GitHub
contabiliza requisições "agent" na cota de *utility models* (muito menor),
causando erros 429 ``user_global_rate_limited``.

Este módulo injeta ``X-Initiator: user`` (sobrescrevível via env var
``GITHUB_COPILOT_X_INITIATOR``) e retries com backoff em RateLimitError.
"""

import os

from google.adk.models.lite_llm import LiteLlm


def copilot_completion_kwargs(model_name: str) -> dict:
    """Kwargs extras para chamadas litellm.completion com github_copilot."""
    if not model_name.startswith("github_copilot/"):
        return {}
    return {
        "extra_headers": {
            "X-Initiator": os.environ.get("GITHUB_COPILOT_X_INITIATOR", "user"),
        },
        "num_retries": int(os.environ.get("ADK_LLM_NUM_RETRIES", "3")),
    }


class GithubCopilotLiteLlm(LiteLlm):
    """LiteLlm com header X-Initiator e retries para github_copilot."""

    def __init__(self, model: str, **kwargs):
        extra = copilot_completion_kwargs(model)
        if extra:
            headers = dict(kwargs.pop("extra_headers", None) or {})
            merged = extra["extra_headers"] | headers
            kwargs["extra_headers"] = merged
            kwargs.setdefault("num_retries", extra["num_retries"])
        super().__init__(model=model, **kwargs)
