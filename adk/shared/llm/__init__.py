"""Módulo de LLM com fallback multi-nível para o ADK.

Uso nos agents:
    from shared.llm import get_model
    model = get_model(agent_name="coder_agent")
"""

from __future__ import annotations

from .router import _build_model_list, create_router

MODEL_NAME = "adk-model"

# Singleton lazy do router
_router = None


def _get_router():
    global _router
    if _router is None:
        _router = create_router()
    return _router


def get_model(agent_name: str | None = None):
    """Retorna instância LiteLlm com fallback via Router.

    Args:
        agent_name: Nome do agente para rastreamento no Langfuse.
                    Se None, métricas são registradas sem identificação de agente.
    """
    from google.adk.models.lite_llm import LiteLlm
    from .client import RouterLiteLLMClient

    router = _get_router()
    client = RouterLiteLLMClient(router, agent_name=agent_name)
    return LiteLlm(model=MODEL_NAME, llm_client=client)
