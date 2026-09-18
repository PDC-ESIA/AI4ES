"""Observabilidade: liga o logging/tracing NATIVO do ADK.

Este módulo é o ponto central de configuração de observabilidade — que antes
inexistia. Em vez de construir infra própria, ele ativa o que o google-adk já
traz embutido:

- ``setup_adk_logger`` (google.adk.cli.utils.logs): configura ``basicConfig``
  com timestamp + nível + ``file:lineno`` e controla o namespace ``google_adk``.
- Plugins nativos (google.adk.plugins): ``LoggingPlugin`` (loga no console cada
  ponto crítico da invocação: mensagem do usuário, início/fim de agente,
  request/response de LLM, tool calls com args/resultados e erros) e
  ``DebugLoggingPlugin`` (mesma informação, estruturada em arquivo YAML).

Como ``orchestrator/agent.py`` repassa ``plugins=ctx.plugin_manager.plugins``
para os Runners internos, um plugin registrado no nível do app cascateia
automaticamente para os 4 sub-pipelines (requirements → design → coding_review
→ qa) e todos os sub-agentes aninhados.

Knobs (via ambiente):
    LOG_LEVEL          Nível do logger raiz/``google_adk`` (default: INFO).
    ADK_LOG_PLUGIN     off | console | file (default: console).
    ADK_DEBUG_LOG_PATH Caminho do YAML quando ADK_LOG_PLUGIN=file
                       (default: workspace_output/adk_debug.yaml).
"""

import logging
import os

from google.adk.cli.utils.logs import setup_adk_logger
from google.adk.plugins import DebugLoggingPlugin

# Instância pré-configurada do plugin de arquivo. Referenciável por nome
# qualificado em `extra_plugins` — o loader do ADK aceita instâncias de
# BasePlugin diretamente (não só classes), permitindo injetar output_path.
debug_logging_plugin = DebugLoggingPlugin(
    output_path=os.environ.get(
        "ADK_DEBUG_LOG_PATH", "workspace_output/adk_debug.yaml"
    )
)


def _resolve_level(default: int = logging.INFO) -> int:
    """Traduz LOG_LEVEL (nome ou número) para o int do módulo logging."""
    raw = os.environ.get("LOG_LEVEL")
    if not raw:
        return default
    raw = raw.strip()
    if raw.isdigit():
        return int(raw)
    return getattr(logging, raw.upper(), default)


def setup_logging() -> None:
    """Configura o logging nativo do ADK a partir de LOG_LEVEL.

    Substitui o antigo ``logger.setLevel`` local de app/main.py (que não
    instalava handler). Idempotente o suficiente para ser chamado no boot.
    """
    setup_adk_logger(level=_resolve_level())


def resolved_plugins() -> list[str]:
    """Nomes qualificados dos plugins nativos a registrar via extra_plugins.

    Controlado por ADK_LOG_PLUGIN:
        off      → nenhum plugin.
        console  → LoggingPlugin (loga tudo no stdout). [default]
        file     → DebugLoggingPlugin (YAML estruturado por invocação).
    """
    mode = os.environ.get("ADK_LOG_PLUGIN", "console").strip().lower()
    if mode == "off":
        return []
    if mode == "file":
        return ["shared.observability.debug_logging_plugin"]
    # default: console
    return ["google.adk.plugins.LoggingPlugin"]
