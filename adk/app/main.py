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

# ---------------------------------------------------------------------------
# Langfuse – observabilidade de LLM (tokens, latência, custo)
# Ativa callbacks do LiteLLM quando LANGFUSE_ENABLED=true
# ---------------------------------------------------------------------------
if os.environ.get("LANGFUSE_ENABLED", "false").lower() == "true":
    _langfuse_vars = {
        "LANGFUSE_PUBLIC_KEY": os.environ.get("LANGFUSE_PUBLIC_KEY"),
        "LANGFUSE_SECRET_KEY": os.environ.get("LANGFUSE_SECRET_KEY"),
        "LANGFUSE_HOST": os.environ.get("LANGFUSE_HOST"),
    }
    _missing = [k for k, v in _langfuse_vars.items() if not v]
    if _missing:
        raise RuntimeError(
            f"LANGFUSE_ENABLED=true mas variáveis obrigatórias ausentes: "
            f"{', '.join(_missing)}. Configure no .env ou desative com "
            f"LANGFUSE_ENABLED=false."
        )

    # Valida conectividade com o Langfuse
    try:
        from langfuse import Langfuse

        _lf_client = Langfuse(
            public_key=_langfuse_vars["LANGFUSE_PUBLIC_KEY"],
            secret_key=_langfuse_vars["LANGFUSE_SECRET_KEY"],
            host=_langfuse_vars["LANGFUSE_HOST"],
        )
        _lf_client.auth_check()
    except Exception as e:
        raise RuntimeError(
            f"LANGFUSE_ENABLED=true mas não foi possível conectar ao Langfuse "
            f"({_langfuse_vars['LANGFUSE_HOST']}): {e}. "
            f"Verifique se o serviço está acessível e as chaves estão corretas."
        ) from e

    litellm.success_callback = ["langfuse"]
    litellm.failure_callback = ["langfuse"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_DEFAULT_AGENTS_DIR = "runners"

app = get_fast_api_app(
    # Profissional: configura por ambiente, com default seguro (produção).
    # - runners: expõe somente apps em adk/runners/ (ex.: orchestrator)
    # - agents/roles: expõe roles diretamente (útil em desenvolvimento)
    agents_dir=os.environ.get("ADK_AGENTS_DIR", _DEFAULT_AGENTS_DIR),
    web=True,
    allow_origins=["*"],
)
