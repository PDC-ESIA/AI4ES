"""Módulo de LLM com fallback multi-nível para o ADK.

Uso nos agents:
    from shared.llm import get_model
    model = get_model()
"""

from google.adk.models.lite_llm import LiteLlm

from .client import RouterLiteLLMClient, MODEL_NAME
from .router import create_router

# Singleton do router para reutilizar across agents
_router = create_router()
_client = RouterLiteLLMClient(_router)


def get_model() -> LiteLlm:
    """Retorna instância LiteLlm com fallback via Router."""
    return LiteLlm(model=MODEL_NAME, llm_client=_client)
