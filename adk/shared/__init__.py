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
# Usa subclasse que injeta X-Initiator: user e retries — evita cair na cota
# reduzida de "utility models" do GitHub Copilot (429 user_global_rate_limited).
LLMRegistry._register_lazy(
    ["github_copilot/.*"],
    "shared.llm",
    "GithubCopilotLiteLlm",
)
