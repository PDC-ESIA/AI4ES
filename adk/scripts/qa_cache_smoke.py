from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.cache.cache_key import build_cache_identity
from shared.cache.sql_cache import create_cache_backend


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("DATABASE_URL não definido. Exemplo: postgresql://postgres:postgres@localhost:5432/qa_agent_cache")
        return 1

    ttl_seconds = int(os.environ.get("QA_AGENT_CACHE_TTL_SECONDS", "86400"))
    backend = create_cache_backend(database_url)

    identity = build_cache_identity(
        model_name=os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash"),
        prompt_text="QA cache smoke test prompt",
        request_contents=[
            {
                "role": "user",
                "parts": [{"text": "smoke-test"}],
            }
        ],
    )

    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=ttl_seconds)
    payload = f"smoke-ok:{now.isoformat()}"

    try:
        backend.set(identity.cache_key, payload, expires_at)
        roundtrip = backend.get(identity.cache_key, now)
        if roundtrip != payload:
            print("Falha no roundtrip do cache.")
            return 1

        print("Smoke test OK.")
        print(f"cache_key={identity.cache_key}")
        print(f"database_url={database_url}")
        print(f"expires_at={expires_at.isoformat()}")
        return 0
    except Exception as exc:
        print(f"Smoke test falhou: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())