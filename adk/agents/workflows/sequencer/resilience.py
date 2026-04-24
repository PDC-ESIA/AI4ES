"""Camada de resiliência do sequenciador.

Envolve a execução do sdlc_pipeline com:
- Timeout configurável via asyncio.wait_for
- Interceptação de falhas de API (LiteLLM)
- Interceptação de violações de schema (Pydantic ValidationError)
- Registro estruturado do erro em session.state
- Re-lançamento controlado de SequencerError (sem crash da aplicação)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from typing import AsyncGenerator 

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event

logger = logging.getLogger(__name__)


class SequencerError(Exception):
    """Exceção controlada emitida pelo wrapper de resiliência.

    Attributes:
        error_type: Categoria da falha — ``timeout`` | ``api_error`` | ``schema_violation``.
        detail: Mensagem descritiva da falha.
        failed_at: Nome do agente ou etapa onde a falha ocorreu, quando disponível.
    """

    def __init__(
        self,
        error_type: str,
        detail: str,
        failed_at: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.error_type = error_type
        self.detail = detail
        self.failed_at = failed_at

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"SequencerError(error_type={self.error_type!r}, "
            f"failed_at={self.failed_at!r}, detail={self.detail!r})"
        )


def _record_failure(
    session_state: dict[str, Any],
    error_type: str,
    detail: str,
    failed_at: str | None = None,
) -> None:
    """Registra o estado de falha de forma imutável no session.state."""
    session_state["sequencer_error"] = error_type
    session_state["error_detail"] = detail
    if failed_at:
        session_state["failed_at"] = failed_at
    logger.error(
        "SequencerError | type=%s | failed_at=%s | detail=%s",
        error_type,
        failed_at,
        detail,
    )



async def run_with_resilience(
    agent: BaseAgent,
    ctx: InvocationContext,
    session_state: dict[str, Any],
    timeout_seconds: float = 300.0,
    failed_at: str | None = None,
) -> AsyncGenerator[Event, None]:
    """Executa o agente em tempo real (streaming) com um relógio global de timeout."""
    
    gen = agent.run_async(ctx)
    loop = asyncio.get_running_loop()
    end_time = loop.time() + timeout_seconds

    try:
        while True:
            # Calcula quanto tempo nos resta
            remaining = end_time - loop.time()
            if remaining <= 0:
                raise asyncio.TimeoutError()

            # Espera pelo próximo evento limitando pelo tempo restante
            event = await asyncio.wait_for(gen.__anext__(), timeout=remaining)
            yield event

    except asyncio.TimeoutError:
        detail = f"Timeout de {timeout_seconds}s excedido" + (f" em '{failed_at}'" if failed_at else "")
        _record_failure(session_state, "timeout", detail, failed_at)
        raise SequencerError("timeout", detail, failed_at) from None

    except StopAsyncIteration:
        # O agente terminou o trabalho dele normalmente. Fim do loop.
        return

    except Exception as exc:
        error_class = type(exc).__name__
        detail = f"{error_class}: {exc}"
        _record_failure(session_state, "api_error", detail, failed_at)
        raise SequencerError("api_error", detail, failed_at) from exc