"""Preflight/health-check rápido do provedor de LLM (GitHub Copilot).

Rodado uma vez por prompt (no topo do orchestrator). Objetivo: detectar em
segundos — em vez de esperar o timeout de 120s por chamada — que a credencial
do Copilot expirou ou que o endpoint está fora do ar, tentar recuperar
automaticamente (renovação de token) e, se não der, abortar cedo com uma
mensagem acionável para o usuário.

Fluxo:
    1. Valida a credencial (Authenticator.get_api_key — auto-renova se expirada).
    2. Se válida, faz um ping real e mínimo ao endpoint (completion 1 token).
    3. Em qualquer falha/timeout, força a renovação do token e refaz o check,
       até AI4ES_PREFLIGHT_RENEW_ATTEMPTS vezes (default 2).
    4. Se ainda assim falhar, retorna ok=False com mensagem — o chamador deve
       abortar o prompt e informar o usuário.

Providers não-Copilot são no-op (ok=True): o health-check só se aplica ao
fluxo de autenticação do GitHub Copilot.

Timeout de cada etapa: AI4ES_PREFLIGHT_TIMEOUT (segundos, default 10).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_COPILOT_PREFIXES = ("github_copilot/", "github/")
_DEFAULT_TIMEOUT = 10.0
_DEFAULT_RENEW_ATTEMPTS = 2

_ABORT_MESSAGE = (
    "[preflight] Não foi possível conectar ao provedor de LLM (GitHub Copilot). "
    "A credencial parece inválida/expirada e a renovação automática falhou após "
    "{attempts} tentativa(s). O prompt foi abortado para não travar por vários "
    "minutos.\n\n"
    "Para reautenticar, rode:\n"
    "    python adk/scripts/copilot_auth.py\n\n"
    "Último erro: {error}"
)


@dataclass(frozen=True)
class PreflightResult:
    """Resultado do health-check. `message` só é relevante quando ok=False."""

    ok: bool
    message: str = ""


def _preflight_timeout() -> float:
    try:
        return float(os.environ.get("AI4ES_PREFLIGHT_TIMEOUT", _DEFAULT_TIMEOUT))
    except (TypeError, ValueError):
        return _DEFAULT_TIMEOUT


def _renew_attempts() -> int:
    try:
        return int(os.environ.get("AI4ES_PREFLIGHT_RENEW_ATTEMPTS", _DEFAULT_RENEW_ATTEMPTS))
    except (TypeError, ValueError):
        return _DEFAULT_RENEW_ATTEMPTS


def _validate_credential() -> None:
    """Lê/renova a api-key do Copilot (auto-refresh se expirada).

    Levanta a exceção do Authenticator se não conseguir obter um token.
    """
    from litellm.llms.github_copilot.authenticator import Authenticator

    token = Authenticator().get_api_key()
    if not token:
        raise RuntimeError("Authenticator retornou token vazio.")


def _ping(model: str, timeout: float) -> None:
    """Chamada mínima ao endpoint do LLM para confirmar conectividade real."""
    import litellm

    litellm.completion(
        model=model,
        messages=[{"role": "user", "content": "ping"}],
        # 16 é o mínimo aceito pelos modelos de raciocínio do Copilot (gpt-5.x,
        # codex): com max_tokens=1 eles respondem 400 "Invalid 'max_output_tokens':
        # integer below minimum value. Expected a value >= 16". O preflight então
        # falhava sempre e culpava a credencial, que estava válida.
        max_tokens=16,
        timeout=timeout,
    )


def _force_renew() -> None:
    """Força o refresh da api-key via access-token e persiste no disco."""
    from litellm.llms.github_copilot.authenticator import Authenticator

    auth = Authenticator()
    info = auth._refresh_api_key()
    with open(auth.api_key_file, "w", encoding="utf-8") as f:
        json.dump(info, f)


async def _health_check(model: str, timeout: float) -> None:
    """Valida credencial e, se ok, faz o ping. Propaga a 1ª exceção/timeout."""
    await asyncio.wait_for(asyncio.to_thread(_validate_credential), timeout)
    await asyncio.wait_for(asyncio.to_thread(_ping, model, timeout), timeout)


async def ensure_llm_ready(model: str | None = None) -> PreflightResult:
    """Health-check rápido do LLM, com renovação de token e retries.

    Para providers não-Copilot é no-op (ok=True). Ver docstring do módulo.
    Nunca levanta: encapsula todas as falhas no PreflightResult.
    """
    model = model or os.environ.get("ADK_LLM_MODEL", "")
    if not model.startswith(_COPILOT_PREFIXES):
        return PreflightResult(ok=True)

    timeout = _preflight_timeout()
    attempts = _renew_attempts()
    last_error: BaseException | None = None

    # Tentativa inicial (sem renovação forçada — get_api_key já auto-renova).
    try:
        await _health_check(model, timeout)
        logger.info("[PREFLIGHT] LLM pronto (credencial válida + ping ok).")
        return PreflightResult(ok=True)
    except (Exception, asyncio.TimeoutError) as exc:  # noqa: BLE001
        last_error = exc
        logger.warning("[PREFLIGHT] Health-check falhou: %s", exc)

    # Recuperação: força renovação do token e refaz o check, até `attempts` vezes.
    for tentativa in range(1, attempts + 1):
        logger.warning(
            "[PREFLIGHT] Renovando token e revalidando (tentativa %d/%d)...",
            tentativa,
            attempts,
        )
        try:
            await asyncio.wait_for(asyncio.to_thread(_force_renew), timeout)
            await _health_check(model, timeout)
            logger.info(
                "[PREFLIGHT] LLM pronto após renovação (tentativa %d/%d).",
                tentativa,
                attempts,
            )
            return PreflightResult(ok=True)
        except (Exception, asyncio.TimeoutError) as exc:  # noqa: BLE001
            last_error = exc
            logger.warning(
                "[PREFLIGHT] Tentativa %d/%d falhou: %s", tentativa, attempts, exc
            )

    message = _ABORT_MESSAGE.format(attempts=attempts, error=last_error)
    logger.error("[PREFLIGHT] Abortando prompt: LLM indisponível após %d tentativa(s).", attempts)
    return PreflightResult(ok=False, message=message)
