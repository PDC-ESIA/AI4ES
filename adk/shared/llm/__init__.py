"""Módulo de LLM com fallback multi-nível para o ADK.

Uso nos agents:
    from shared.llm import get_model
    model = get_model(agent_name="coder_agent")
"""

from google.adk.models.lite_llm import LiteLlm

from .client import RouterLiteLLMClient, MODEL_NAME
from .router import create_router

# Singleton do router para reutilizar across agents
_router = create_router()


def get_model(agent_name: str | None = None) -> LiteLlm:
    """Retorna instância LiteLlm com fallback via Router.

    Args:
        agent_name: Nome do agente para rastreamento no Langfuse.
                    Se None, métricas são registradas sem identificação de agente.
    """
    client = RouterLiteLLMClient(_router, agent_name=agent_name)
    return LiteLlm(model=MODEL_NAME, llm_client=client)
