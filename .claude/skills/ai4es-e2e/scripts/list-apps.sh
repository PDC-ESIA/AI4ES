#!/usr/bin/env bash
# GET /list-apps formatado.
set -euo pipefail
PORT="${PORT:-8081}"
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
PYTHON="${ROOT}/adk/.venv/bin/python"

curl -sf "http://127.0.0.1:${PORT}/list-apps" | "${PYTHON}" -c "
import json, sys
apps = json.load(sys.stdin)
print(f'Total: {len(apps)} agentes')
print()
for app in sorted(apps):
    print(f'  - {app}')
"
