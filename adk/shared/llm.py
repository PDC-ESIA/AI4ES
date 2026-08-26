"""LiteLlm customizado para o provider github_copilot.

O LiteLLM envia o header ``X-Initiator: agent`` sempre que o histórico da
conversa contém mensagens com role ``assistant``/``tool``. Em pipelines
multiagente do ADK isso acontece em praticamente toda chamada, e o GitHub
contabiliza requisições "agent" na cota de *utility models* (muito menor),
causando erros 429 ``user_global_rate_limited``.

Este módulo injeta ``X-Initiator: user`` (sobrescrevível via env var
``GITHUB_COPILOT_X_INITIATOR``) e retries com backoff em RateLimitError.

IMPORTANTE: o litellm monta os headers da API do Copilot fazendo
``copilot_headers.update(extra_headers)`` — ou seja, as chaves que
passarmos aqui SOBRESCREVEM as dele, inclusive se ele por algum motivo
(versão instalada, ordem de execução) não reinjetar os headers padrão de
"IDE" (``editor-version``, ``copilot-integration-id`` etc.). Se
mandarmos só ``X-Initiator``, tudo bem quando o merge do litellm roda;
mas se ele não rodar, a requisição sai sem esses headers e a API do
Copilot responde 400 "missing Editor-Version header for IDE auth".
Por isso montamos aqui, explicitamente, o conjunto completo de headers
de IDE — assim eles vão sempre, independente do comportamento do
litellm nessa versão. Não incluímos ``Authorization``: esse token é
gerenciado pelo litellm/ADK via ``Authenticator`` a cada chamada, e se
o cachearmos aqui ele fica velho (o Copilot token expira em ~25-30min).
"""

import os
import uuid

from google.adk.models.lite_llm import LiteLlm

_COPILOT_VERSION = "0.26.7"

# Headers de "IDE" exigidos pela API do Copilot, além de Authorization.
# Mesmos valores usados pelo litellm em
# litellm.llms.github_copilot.common_utils.get_copilot_default_headers,
# mas fixados aqui para não depender do merge interno dele.
_COPILOT_IDE_HEADERS = {
    "copilot-integration-id": "vscode-chat",
    "editor-version": "vscode/1.95.0",
    "editor-plugin-version": f"copilot-chat/{_COPILOT_VERSION}",
    "user-agent": f"GitHubCopilotChat/{_COPILOT_VERSION}",
    "openai-intent": "conversation-panel",
    "x-github-api-version": "2025-04-01",
    "x-vscode-user-agent-library-version": "electron-fetch",
}


def copilot_completion_kwargs(model_name: str) -> dict:
    """Kwargs extras para chamadas litellm.completion com github_copilot."""
    if not model_name.startswith("github_copilot/"):
        return {}
    headers = {
        **_COPILOT_IDE_HEADERS,
        "x-request-id": str(uuid.uuid4()),
        "X-Initiator": os.environ.get("GITHUB_COPILOT_X_INITIATOR", "user"),
    }
    return {
        "extra_headers": headers,
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


def openrouter_completion_kwargs(model_name: str) -> dict:
    """Kwargs extras para chamadas litellm.completion com openrouter.

    O OpenRouter recomenda os headers ``HTTP-Referer`` e ``X-Title`` para
    identificar a aplicação no painel/ranking da plataforma. Ambos são
    opcionais e sobrescrevíveis via env var; se vazios, não são enviados.
    """
    if not model_name.startswith("openrouter/"):
        return {}
    headers = {}
    x_title = os.environ.get("OPENROUTER_X_TITLE", "AI4ES")
    if x_title:
        headers["X-Title"] = x_title
    http_referer = os.environ.get(
        "OPENROUTER_HTTP_REFERER", "https://github.com/ceia-pdc/AI4ES"
    )
    if http_referer:
        headers["HTTP-Referer"] = http_referer
    return {
        "extra_headers": headers,
        "num_retries": int(os.environ.get("ADK_LLM_NUM_RETRIES", "1")),
    }


class OpenRouterLiteLlm(LiteLlm):
    """LiteLlm com headers recomendados (HTTP-Referer/X-Title) para openrouter."""

    def __init__(self, model: str, **kwargs):
        extra = openrouter_completion_kwargs(model)
        if extra:
            headers = dict(kwargs.pop("extra_headers", None) or {})
            merged = extra["extra_headers"] | headers
            kwargs["extra_headers"] = merged
            kwargs.setdefault("num_retries", extra["num_retries"])
        super().__init__(model=model, **kwargs)