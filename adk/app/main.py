import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import litellm
from dotenv import load_dotenv
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.registry import LLMRegistry

from shared.workspace import init_workspace

LLMRegistry._register(r"github_copilot/.*", LiteLlm)
LLMRegistry._register(r"github/.*", LiteLlm)


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# github_copilot não suporta response_format (usado pelo output_schema do ADK).
# Com drop_params o LiteLLM remove silenciosamente parâmetros não suportados.
litellm.drop_params = True

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_DEFAULT_AGENTS_DIR = "src/agents"

# Por padrão, o workspace_output/ existente é preservado ao subir o servidor
# Defina WORKSPACE_RESET_ON_START=true para forçar uma limpeza da raiz legada
# (workspace_output/) uma única vez, no boot — útil em ambiente de dev.
# Não afeta workspaces por sessão (workspace_output/sessions/<id>/), que são
# geridos individualmente por quem os cria.
_ENV_RESET_ON_START = "WORKSPACE_RESET_ON_START"


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.environ.get(_ENV_RESET_ON_START, "false").lower() in ("true", "1", "yes"):
        root = init_workspace()
        logger.info(
            f"[STARTUP] {_ENV_RESET_ON_START}=true — workspace legado limpo: {root}"
        )
    else:
        logger.info(
            f"[STARTUP] workspace_output/ preservado ({_ENV_RESET_ON_START} != true)."
        )
    yield


app = get_fast_api_app(
    # Diretório padrao: adk/src/agents/ — cada subpasta é um agente runnável
    # cujo __init__.py exporta root_agent. Override via ADK_AGENTS_DIR.
    agents_dir=os.environ.get("ADK_AGENTS_DIR", _DEFAULT_AGENTS_DIR),
    web=True,
    allow_origins=["*"],
    lifespan=lifespan,
)
