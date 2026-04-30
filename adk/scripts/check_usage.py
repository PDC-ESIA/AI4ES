"""Verifica consumo diário de tokens via Langfuse e alerta via webhook.

Uso:
    python -m scripts.check_usage

Variáveis de ambiente necessárias:
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
    DAILY_TOKEN_LIMIT (padrão: 1_000_000)
    ALERT_WEBHOOK_URL (Discord/Slack webhook)
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

from langfuse import Langfuse


def get_daily_usage() -> int:
    """Consulta Langfuse e retorna total de tokens consumidos hoje."""
    client = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.environ.get("LANGFUSE_HOST", "http://localhost:3000"),
    )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Busca todas as gerações de hoje
    generations = client.get_generations(
        limit=1000,
        from_timestamp=f"{today}T00:00:00Z",
    )

    total_tokens = 0
    for gen in generations.data:
        usage = gen.usage
        if usage:
            total_tokens += (usage.total_tokens or 0)

    return total_tokens


def send_alert(message: str) -> None:
    """Envia alerta via webhook (compatível com Discord e Slack)."""
    webhook_url = os.environ.get("ALERT_WEBHOOK_URL")
    if not webhook_url:
        print(f"[ALERTA LOCAL] {message}")
        return

    payload = json.dumps({"content": message, "text": message}).encode()
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=10)
    print(f"[ALERTA ENVIADO] {message}")


def main() -> None:
    limit = int(os.environ.get("DAILY_TOKEN_LIMIT", "1000000"))
    threshold = 0.8

    usage = get_daily_usage()
    pct = usage / limit if limit > 0 else 0

    print(f"Consumo diário: {usage:,} / {limit:,} tokens ({pct:.1%})")

    if pct >= threshold:
        send_alert(
            f"⚠️ **Alerta de consumo ADK** — {pct:.0%} do limite diário "
            f"atingido ({usage:,} / {limit:,} tokens). "
            f"Considere reduzir uso ou verificar fallback."
        )
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
