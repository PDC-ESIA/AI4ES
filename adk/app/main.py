import logging
import os
from pathlib import Path

import litellm
from dotenv import load_dotenv
from google.adk.cli.fast_api import get_fast_api_app

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# github_copilot não suporta response_format (usado pelo output_schema do ADK).
# Com drop_params o LiteLLM remove silenciosamente parâmetros não suportados.
litellm.drop_params = True

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Langfuse – observabilidade de LLM (tokens, latência, custo)
# Ativado somente quando as variáveis de ambiente LANGFUSE_PUBLIC_KEY e
# LANGFUSE_SECRET_KEY estão definidas.
# ---------------------------------------------------------------------------
if os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"):
    litellm.success_callback = ["langfuse"]
    litellm.failure_callback = ["langfuse"]
    logger.info("Langfuse ativado como callback de observabilidade do LiteLLM.")
else:
    logger.info("Langfuse desativado (LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY ausentes).")

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
