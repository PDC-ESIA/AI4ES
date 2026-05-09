"""
Factory base para criação de agentes LLM.

Centraliza o boilerplate de construção do LlmAgent (model, env var, defaults),
garantindo consistência e manutenibilidade em todos os agentes do sistema.
"""

import os
from types import ModuleType
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

_DEFAULT_MODEL = "github_copilot/gpt-4"
_ENV_MODEL_KEY = "ADK_LLM_MODEL"


def _build_model(model_override: str | None = None) -> LiteLlm:
    """Constrói a instância do modelo LLM a partir da env var ou override."""
    model_id = model_override or os.environ.get(_ENV_MODEL_KEY, _DEFAULT_MODEL)
    return LiteLlm(model_id)


def create_base_agent(
    name: str,
    prompt_module: ModuleType,
    output_key: str | None = None,
    output_schema: Any = None,
    tools: list | None = None,
    model: str | None = None,
) -> LlmAgent:
    """Cria um LlmAgent básico com configuração padronizada.

    Args:
        name: Nome único do agente (ex: 'architecture_agent').
        prompt_module: Módulo Python contendo 'description' e 'instruction'.
        output_key: Chave no session state para a saída do agente.
        output_schema: Schema Pydantic para validação da saída (opcional).
        tools: Lista de tools do agente (opcional).
        model: Override do modelo LLM (opcional, default via env var).

    Returns:
        LlmAgent configurado e pronto para uso.
    """
    kwargs: dict[str, Any] = {
        "model": _build_model(model),
        "name": name,
        "description": prompt_module.description,
        "instruction": prompt_module.instruction,
    }

    if output_key is not None:
        kwargs["output_key"] = output_key

    if output_schema is not None:
        kwargs["output_schema"] = output_schema

    if tools:
        kwargs["tools"] = tools

    return LlmAgent(**kwargs)
