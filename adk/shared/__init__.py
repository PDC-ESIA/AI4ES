"""Shared: módulo comum importado por todos os agentes.

Configura LiteLLM e registra providers adicionais no LLMRegistry do ADK
no momento do import, garantindo que qualquer agente (via factory ou direto)
tenha acesso ao provider github_copilot.
"""

import litellm
from google.adk.models.registry import LLMRegistry

# github_copilot (e outros providers) não suportam response_format.
# drop_params faz o LiteLLM remover silenciosamente params não suportados.
litellm.drop_params = True

# Registra github_copilot como provider LiteLLM no ADK (não incluso por padrão).
LLMRegistry._register_lazy(
    ["github_copilot/.*"],
    "google.adk.models.lite_llm",
    "LiteLlm",
)
