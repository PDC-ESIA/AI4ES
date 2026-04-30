"""LiteLLM Router com fallback multi-nível.

Cadeia de prioridade:
  1. github_copilot/gpt-4 (primário)
  2. openrouter/meta-llama/llama-4-scout (fallback gratuito)
  3. openrouter/google/gemini-2.0-flash (último recurso)
"""

import os


def _build_model_list() -> list[dict]:
    """Constrói lista de deployments a partir das env vars."""
    primary_model = os.environ.get("ADK_LLM_MODEL", "github_copilot/gpt-4")
    fallback_1 = os.environ.get(
        "ADK_LLM_FALLBACK_MODEL_1", "openrouter/meta-llama/llama-4-scout"
    )
    fallback_2 = os.environ.get(
        "ADK_LLM_FALLBACK_MODEL_2", "openrouter/google/gemini-2.0-flash"
    )

    model_name = "adk-model"

    deployments = [
        {
            "model_name": model_name,
            "litellm_params": {
                "model": primary_model,
                "order": 1,
            },
        },
        {
            "model_name": model_name,
            "litellm_params": {
                "model": fallback_1,
                "api_key": os.environ.get("OPENROUTER_API_KEY"),
                "order": 2,
            },
        },
        {
            "model_name": model_name,
            "litellm_params": {
                "model": fallback_2,
                "api_key": os.environ.get("OPENROUTER_API_KEY"),
                "order": 3,
            },
        },
    ]

    return deployments


def create_router():
    """Cria e retorna o Router LiteLLM configurado."""
    from litellm import Router

    return Router(
        model_list=_build_model_list(),
        num_retries=2,
        retry_after=1,
        allowed_fails=1,
        cooldown_time=10,
        routing_strategy="simple-shuffle",
    )
