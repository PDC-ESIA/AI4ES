"""Fábrica centralizada de modelo LLM com fallback via LiteLLM Router."""

import logging
import os
from pathlib import Path
from typing import Optional

import litellm
import yaml
from google.adk.models.lite_llm import LiteLlm

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "github_copilot/gpt-4"
_CONFIG_PATH = Path(__file__).resolve().parents[1] / "llm_config.yaml"

_router: Optional[litellm.Router] = None


def _load_config() -> dict:
    if not _CONFIG_PATH.exists():
        logger.info("Arquivo %s não encontrado; fallback desabilitado.", _CONFIG_PATH)
        return {}
    with open(_CONFIG_PATH) as fh:
        return yaml.safe_load(fh) or {}


def _build_router(config: dict) -> Optional[litellm.Router]:
    model_list = config.get("model_list")
    if not model_list:
        return None

    router_settings = config.get("router_settings", {})
    fallbacks = router_settings.get("fallbacks")
    num_retries = router_settings.get("num_retries", 2)
    timeout = router_settings.get("timeout", 120)

    return litellm.Router(
        model_list=model_list,
        fallbacks=fallbacks,
        num_retries=num_retries,
        timeout=timeout,
    )


def _init() -> None:
    global _router  # noqa: PLW0603
    config = _load_config()
    _router = _build_router(config)

    if _router is None:
        logger.info("Nenhum fallback configurado; usando modelo direto.")
        return

    litellm.acompletion = _router.acompletion  # type: ignore[assignment]
    litellm.completion = _router.completion  # type: ignore[assignment]
    logger.info(
        "LiteLLM Router ativado com %d deployment(s) e fallbacks configurados.",
        len(_router.model_list),
    )


def get_router() -> Optional[litellm.Router]:
    return _router


def get_model() -> LiteLlm:
    """Retorna instância LiteLlm compatível com ADK usando o modelo primário."""
    model_name = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)
    return LiteLlm(model=model_name)


_init()
