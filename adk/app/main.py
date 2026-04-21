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

_DEFAULT_AGENTS_DIR = "agents/roles"

app = get_fast_api_app(
    # Profissional: configura por ambiente, com default seguro (produção).
    # - runners: expõe somente apps em adk/runners/ (ex.: orchestrator)
    # - agents/roles: expõe roles diretamente (útil em desenvolvimento)
    agents_dir=os.environ.get("ADK_AGENTS_DIR", _DEFAULT_AGENTS_DIR),
    web=True,
    allow_origins=["*"],
)
