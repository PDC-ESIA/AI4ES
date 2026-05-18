#!/usr/bin/env bash
# Mata uvicorn na porta indicada. Idempotente.
set -euo pipefail
PORT="${PORT:-8081}"
SESSION_FILE="${SESSION_FILE:-/tmp/ai4es-current-session.env}"
rm -f "${SESSION_FILE}"
if pkill -f "uvicorn.*--port ${PORT}" 2>/dev/null; then
  echo "Uvicorn na porta ${PORT} foi finalizado."
else
  echo "Nenhum uvicorn na porta ${PORT}."
fi
