"""Factory para criação padronizada de agentes."""

from google.adk.agents import LlmAgent

from shared.capabilities import resolve_tools
from shared.llm import get_model


def create_agent(
    name: str,
    model_key: str,
    instruction: str,
    description: str,
    capabilities: list[str] | None = None,
    tools: list | None = None,
    output_schema=None,
    output_key: str | None = None,
    **kwargs,
) -> LlmAgent:
    """Cria um LlmAgent com capabilities resolvidas e configuração padronizada.

    Args:
        name: Nome identificador do agente.
        model_key: Chave para resolução do modelo via get_model().
        instruction: Prompt de instrução do agente.
        description: Descrição curta do agente.
        capabilities: Lista de nomes de capabilities do registry.
        tools: Tools adicionais específicas (não cobertas por capabilities).
        output_schema: Schema Pydantic de saída (opcional).
        output_key: Chave para armazenar output no estado compartilhado.
        **kwargs: Parâmetros extras repassados ao LlmAgent.

    Returns:
        Instância configurada de LlmAgent.
    """
    resolved_tools = resolve_tools(capabilities or [], extra_tools=tools)

    agent_kwargs = {
        "name": name,
        "model": get_model(agent_name=model_key),
        "instruction": instruction,
        "description": description,
        **kwargs,
    }

    if resolved_tools:
        agent_kwargs["tools"] = resolved_tools
    if output_schema is not None:
        agent_kwargs["output_schema"] = output_schema
    if output_key is not None:
        agent_kwargs["output_key"] = output_key

    return LlmAgent(**agent_kwargs)
