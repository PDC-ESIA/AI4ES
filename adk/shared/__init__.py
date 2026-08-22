"""Shared: módulo comum importado por todos os agentes.

Configura LiteLLM e registra providers adicionais no LLMRegistry do ADK
no momento do import, garantindo que qualquer agente (via factory ou direto)
tenha acesso ao provider github_copilot.
"""

import os

import litellm
from google.adk.models.registry import LLMRegistry

# github_copilot (e outros providers) não suportam response_format.
# drop_params faz o LiteLLM remover silenciosamente params não suportados.
litellm.drop_params = True

# Fail-fast: o read-timeout default do LiteLLM é 600s (COMPLETION_HTTP_FALLBACK_SECONDS).
# Com chamadas de LLM aninhadas (orchestrator → pipelines → sub-agentes), um
# endpoint travado (ex.: credencial Copilot expirada) empilha timeouts de 10min
# e pode pendurar o pipeline por dezenas de minutos. Limitamos globalmente o
# timeout e o nº de retries (com backoff nativo do litellm) para falhar rápido
# com erro claro. Ambos são sobrescrevíveis por variável de ambiente.
litellm.request_timeout = float(os.environ.get("AI4ES_LLM_TIMEOUT", "120"))
litellm.num_retries = int(os.environ.get("AI4ES_LLM_NUM_RETRIES", "1"))

# Registra github_copilot como provider LiteLLM no ADK (não incluso por padrão).
# Usa subclasse que injeta X-Initiator: user e retries — evita cair na cota
# reduzida de "utility models" do GitHub Copilot (429 user_global_rate_limited).
# Registro tolerante a versão do ADK: 1.33+ expõe `_register_lazy` (import
# preguiçoso do provider, só quando o modelo é resolvido). Em versões antigas,
# o método não existe; caímos no registro clássico (import imediato da classe).
if hasattr(LLMRegistry, "_register_lazy"):
    LLMRegistry._register_lazy(
        ["github_copilot/.*"],
        "shared.llm",
        "GithubCopilotLiteLlm",
    )
else:
    from shared.llm import GithubCopilotLiteLlm

    LLMRegistry._register(r"github_copilot/.*", GithubCopilotLiteLlm)
