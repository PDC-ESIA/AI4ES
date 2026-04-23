"""Resiliência do sequenciador — wrapper de tolerância a falhas.

Fornece um wrapper assíncrono que envolve a execução do pipeline SDLC,
capturando falhas comuns (timeout, erro de API, violação de schema) e
registrando o estado do erro em ``session.state`` de forma estruturada
antes de re-lançar uma exceção controlada.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pydantic import ValidationError

logger = logging.getLogger(__name__)


class SequencerError(Exception):
    """Exceção controlada lançada pelo wrapper de resiliência.

    Atributos
    ---------
    error_type : str
        Categoria da falha: ``'timeout'``, ``'api_error'`` ou
        ``'schema_violation'``.
    detail : str
        Mensagem descritiva do erro original.
    """

    def __init__(self, error_type: str, detail: str) -> None:
        self.error_type = error_type
        self.detail = detail
        super().__init__(f"[{error_type}] {detail}")


def _record_failure(
    session_state: dict[str, Any],
    *,
    error_type: str,
    detail: str,
    failed_at: str | None = None,
) -> None:
    """Registra informações de falha no ``session.state``."""
    session_state["sequencer_error"] = error_type
    session_state["error_detail"] = detail
    if failed_at is not None:
        session_state["failed_at"] = failed_at


async def run_with_resilience(
    coro,
    session_state: dict[str, Any],
    *,
    timeout_seconds: float = 300,
    current_agent_name: str | None = None,
) -> Any:
    """Executa uma coroutine com tratamento de falhas padronizado.

    Parameters
    ----------
    coro:
        Coroutine a ser executada (ex.: ``runner.run_async(session)``).
    session_state:
        Referência ao ``session.state`` do ADK onde as informações de
        falha serão registradas.
    timeout_seconds:
        Limite de tempo em segundos antes de abortar (padrão: 300s).
    current_agent_name:
        Nome do agente em execução no momento da falha (para registro).

    Returns
    -------
    Any
        O resultado da coroutine, se bem-sucedida.

    Raises
    ------
    SequencerError
        Sempre re-lançada em caso de falha, após registrar o estado.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)

    except asyncio.TimeoutError:
        detail = (
            f"Pipeline excedeu o limite de {timeout_seconds}s"
            f"{f' no agente {current_agent_name}' if current_agent_name else ''}"
        )
        logger.error(detail)
        _record_failure(
            session_state,
            error_type="timeout",
            detail=detail,
            failed_at=current_agent_name,
        )
        raise SequencerError("timeout", detail) from None

    except ValidationError as exc:
        detail = f"Schema inválido: {exc.error_count()} erro(s) — {exc}"
        logger.error(detail)
        _record_failure(
            session_state,
            error_type="schema_violation",
            detail=detail,
            failed_at=current_agent_name,
        )
        raise SequencerError("schema_violation", detail) from exc

    except SequencerError:
        # Não re-envolver SequencerError — propagar como está.
        raise

    except Exception as exc:  # noqa: BLE001
        detail = f"{type(exc).__name__}: {exc}"
        logger.error("Erro de API/runtime no pipeline: %s", detail)
        _record_failure(
            session_state,
            error_type="api_error",
            detail=detail,
            failed_at=current_agent_name,
        )
        raise SequencerError("api_error", detail) from exc
