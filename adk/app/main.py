import logging
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

app = get_fast_api_app(
    agents_dir="agents/roles",
    web=True,
    allow_origins=["*"],
)
