#!/usr/bin/env python3
"""Verifica consumo diário de tokens via Langfuse e alerta ao atingir threshold.

Uso:
    python scripts/check_usage.py                          # threshold padrão 80%
    python scripts/check_usage.py --threshold 0.7          # threshold customizado
    DAILY_TOKEN_LIMIT=500000 python scripts/check_usage.py # limite diário explícito

Variáveis de ambiente necessárias:
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST (opcional)
    DAILY_TOKEN_LIMIT – número máximo de tokens/dia (padrão: 1_000_000)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone

from langfuse import Langfuse

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_DAILY_LIMIT = 1_000_000
_DEFAULT_THRESHOLD = 0.8


def get_daily_usage(client: Langfuse) -> int:
    """Retorna total de tokens (input + output) consumidos hoje via Langfuse."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    page = 1
    total_tokens = 0
    while True:
        generations = client.fetch_generations(
            limit=100,
            page=page,
            from_start_time=f"{today}T00:00:00Z",
        )
        items = generations.data if generations.data else []
        if not items:
            break
        for gen in items:
            usage = gen.usage
            if usage:
                total_tokens += (usage.input or 0) + (usage.output or 0)
        page += 1

    return total_tokens


def check(threshold: float = _DEFAULT_THRESHOLD) -> bool:
    """Verifica consumo e emite alerta. Retorna True se dentro do limite."""
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    if not public_key or not secret_key:
        logger.error("LANGFUSE_PUBLIC_KEY e LANGFUSE_SECRET_KEY são obrigatórias.")
        return False

    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
    client = Langfuse(public_key=public_key, secret_key=secret_key, host=host)

    daily_limit = int(os.environ.get("DAILY_TOKEN_LIMIT", _DEFAULT_DAILY_LIMIT))
    total = get_daily_usage(client)
    ratio = total / daily_limit if daily_limit > 0 else 0.0
    pct = ratio * 100

    logger.info("Tokens consumidos hoje: %s / %s (%.1f%%)", f"{total:,}", f"{daily_limit:,}", pct)

    if ratio >= 1.0:
        logger.critical("LIMITE DIÁRIO ATINGIDO – consumo em %.1f%%.", pct)
        return False
    if ratio >= threshold:
        logger.warning(
            "ALERTA – consumo em %.1f%% (threshold: %.0f%%). Considere reduzir uso ou ativar fallback.",
            pct,
            threshold * 100,
        )
        return False

    logger.info("Consumo dentro do limite (threshold: %.0f%%).", threshold * 100)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Verifica consumo diário de tokens.")
    parser.add_argument(
        "--threshold",
        type=float,
        default=_DEFAULT_THRESHOLD,
        help="Fração do limite que dispara alerta (padrão: 0.8)",
    )
    args = parser.parse_args()

    ok = check(threshold=args.threshold)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
