import logging
import os
from pathlib import Path

import litellm
from dotenv import load_dotenv
from google.adk.cli.fast_api import get_fast_api_app

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _env_true(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}

# github_copilot não suporta response_format (usado pelo output_schema do ADK).
# Com drop_params o LiteLLM remove silenciosamente parâmetros não suportados.
litellm.drop_params = True

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Verificações de configuração obrigatória / recomendada
# ---------------------------------------------------------------------------
if not os.environ.get("AGENT_WORKSPACE", "").strip():
    logger.warning(
        "AGENT_WORKSPACE não está definida. Ferramentas de arquivo falharão até que "
        "seja configurada (caminho da pasta de entregáveis dos agentes)."
    )

_has_langfuse = bool(
    os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")
)
_langfuse_enabled = _env_true("LANGFUSE_ENABLED", default=True)
if _has_langfuse and _langfuse_enabled:
    litellm.success_callback = ["langfuse"]
    litellm.failure_callback = ["langfuse"]
    logger.info("Langfuse ativado como callback de observabilidade do LiteLLM.")
elif _has_langfuse and not _langfuse_enabled:
    logger.warning(
        "LANGFUSE_ENABLED=false. Callbacks do Langfuse desativados por configuração."
    )
else:
    logger.warning(
        "Monitoramento desativado — LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY ausentes. "
        "Sem ele não há visibilidade sobre tokens, latência ou custo das chamadas LLM."
    )

_has_fallback = bool(
    os.environ.get("GROQ_API_KEY", "").strip()
    or os.environ.get("OPENROUTER_API_KEY", "").strip()
)
if not _has_fallback:
    logger.warning(
        "Fallback de LLM desativado — nenhuma chave GROQ_API_KEY ou OPENROUTER_API_KEY "
        "encontrada. Se o modelo primário falhar, não haverá provedor alternativo."
    )

# ---------------------------------------------------------------------------
# Inicializa o Router de fallback (shared.llm lê llm_config.yaml e faz o
# monkey-patch de litellm.acompletion / litellm.completion se houver config).
# ---------------------------------------------------------------------------
import shared.llm  # noqa: E402, F401

_DEFAULT_AGENTS_DIR = "runners"

app = get_fast_api_app(
    agents_dir=os.environ.get("ADK_AGENTS_DIR", _DEFAULT_AGENTS_DIR),
    web=True,
    allow_origins=["*"],
)
