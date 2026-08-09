"""Configuração por ambiente do loop de codificação (coding_review).

Centraliza a resolução das variáveis que controlam o `LoopAgent` e o
`convergence_checker`, para que o teto e a paciência sejam lidos de UM único
lugar (DRY) e a deprecação da env antiga emita UM único aviso.

Variáveis suportadas:
- ``AI4ES_LOOP_MAX_ITERATIONS`` (int, default 300): teto do LoopAgent (rede de
  segurança). A terminação REAL do loop é do convergence_checker (early-stopping
  por progresso); este teto é apenas a última salvaguarda.
- ``AI4ES_LOOP_PATIENCE`` (int, default 3): janela de iterações sem progresso
  antes de o convergence_checker encerrar.

Deprecada (IGNORADA):
- ``AI4ES_MAX_LOOP_ITERATIONS``: substituída por ``AI4ES_LOOP_MAX_ITERATIONS``.
  Se presente, emite ``DeprecationWarning`` + log e o valor é IGNORADO — migração
  forçada, sem fallback silencioso.

A resolução acontece no import-time (mesmo padrão de ``ADK_LLM_MODEL``): as
constantes ``LOOP_MAX_ITERATIONS`` / ``LOOP_PATIENCE`` são fixadas uma vez.
"""

import logging
import os
import warnings

logger = logging.getLogger(__name__)

DEFAULT_LOOP_MAX_ITERATIONS = 300
DEFAULT_LOOP_PATIENCE = 3

_ENV_LOOP_MAX_ITERATIONS = "AI4ES_LOOP_MAX_ITERATIONS"
_ENV_LOOP_PATIENCE = "AI4ES_LOOP_PATIENCE"
_ENV_DEPRECATED_MAX_ITERATIONS = "AI4ES_MAX_LOOP_ITERATIONS"


def _int_env(nome: str, default: int) -> int:
    """Lê um inteiro de env; ausente/inválido → default (inválido gera aviso)."""
    bruto = os.environ.get(nome)
    if bruto is None:
        return default
    try:
        return int(bruto)
    except ValueError:
        logger.warning(
            "coding_review.config: %s=%r inválido; usando %d.", nome, bruto, default
        )
        return default


def _avisar_env_deprecada() -> None:
    """Se a env antiga estiver setada, avisa e a IGNORA (migração forçada)."""
    if _ENV_DEPRECATED_MAX_ITERATIONS in os.environ:
        msg = (
            f"{_ENV_DEPRECATED_MAX_ITERATIONS} está obsoleta e é IGNORADA; "
            f"use {_ENV_LOOP_MAX_ITERATIONS} "
            f"(default {DEFAULT_LOOP_MAX_ITERATIONS})."
        )
        warnings.warn(msg, DeprecationWarning, stacklevel=2)
        logger.warning("coding_review.config: %s", msg)


_avisar_env_deprecada()

# Constantes resolvidas uma única vez no import-time.
LOOP_MAX_ITERATIONS = _int_env(_ENV_LOOP_MAX_ITERATIONS, DEFAULT_LOOP_MAX_ITERATIONS)
LOOP_PATIENCE = _int_env(_ENV_LOOP_PATIENCE, DEFAULT_LOOP_PATIENCE)
