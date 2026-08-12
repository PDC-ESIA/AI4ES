import logging
import os
from pathlib import Path

import litellm
from dotenv import load_dotenv
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.registry import LLMRegistry

LLMRegistry._register(r"github_copilot/.*", LiteLlm)
LLMRegistry._register(r"github/.*", LiteLlm)


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# github_copilot não suporta response_format (usado pelo output_schema do ADK).
# Com drop_params o LiteLLM remove silenciosamente parâmetros não suportados.
litellm.drop_params = True

# Fail-fast: limita timeout/retries globais do LiteLLM (default de read-timeout
# é 600s). Evita que uma credencial expirada ou endpoint travado pendure o
# pipeline por dezenas de minutos. Espelha shared/__init__.py — repetido aqui
# porque o entrypoint web pode não importar `shared` antes da 1ª chamada.
litellm.request_timeout = float(os.environ.get("AI4ES_LLM_TIMEOUT", "120"))
litellm.num_retries = int(os.environ.get("AI4ES_LLM_NUM_RETRIES", "1"))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _preflight_copilot_credential() -> None:
    """Valida (e renova, se possível) a credencial do GitHub Copilot no boot.

    Só roda quando o modelo configurado usa o provider github_copilot. Falhas
    NÃO derrubam o servidor: apenas logam um aviso acionável, evitando que o
    usuário descubra uma credencial expirada apenas dezenas de minutos adentro
    de um run aninhado.
    """
    model = os.environ.get("ADK_LLM_MODEL", "")
    if not model.startswith("github_copilot/") and not model.startswith("github/"):
        return
    try:
        from litellm.llms.github_copilot.authenticator import Authenticator

        Authenticator().get_api_key()
        logger.info("[PREFLIGHT] Credencial GitHub Copilot válida.")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[PREFLIGHT] Credencial GitHub Copilot inválida/expirada (%s). "
            "Reautentique com: python adk/scripts/copilot_auth.py",
            exc,
        )


_preflight_copilot_credential()

_DEFAULT_AGENTS_DIR = "src/agents"

app = get_fast_api_app(
    # Diretório padrao: adk/src/agents/ — cada subpasta é um agente runnável
    # cujo __init__.py exporta root_agent. Override via ADK_AGENTS_DIR.
    agents_dir=os.environ.get("ADK_AGENTS_DIR", _DEFAULT_AGENTS_DIR),
    web=True,
    allow_origins=["*"],
)
