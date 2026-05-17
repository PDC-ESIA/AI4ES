#!/usr/bin/env bash
# Sobe o uvicorn do ADK em background. Aguarda /list-apps responder.
# Variáveis:
#   PORT     — porta (default 8081)
#   LOG_FILE — caminho do log (default /tmp/ai4es-uvicorn-<PORT>.log)
#
# Saída: imprime URL + PID. Exit 1 se não subir em 30s.

set -euo pipefail

PORT="${PORT:-8081}"
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
ADK_DIR="${ROOT}/adk"
LOG_FILE="${LOG_FILE:-/tmp/ai4es-uvicorn-${PORT}.log}"

if [ ! -d "${ADK_DIR}/.venv" ]; then
  echo "ERRO: ${ADK_DIR}/.venv não existe. Rode: cd ${ADK_DIR} && uv sync" >&2
  exit 1
fi

if [ ! -f "${ADK_DIR}/.env" ]; then
  echo "AVISO: ${ADK_DIR}/.env não existe — agentes vão falhar sem GOOGLE_API_KEY." >&2
fi

if curl -sf "http://127.0.0.1:${PORT}/list-apps" >/dev/null 2>&1; then
  echo "Servidor já está rodando em http://127.0.0.1:${PORT}"
  echo "Logs: ${LOG_FILE}"
  exit 0
fi

echo "Iniciando uvicorn em ${ADK_DIR} na porta ${PORT}..." >&2
cd "${ADK_DIR}"
nohup .venv/bin/uvicorn app.main:app --port "${PORT}" > "${LOG_FILE}" 2>&1 &
PID=$!
disown 2>/dev/null || true

for i in $(seq 1 30); do
  sleep 1
  if curl -sf "http://127.0.0.1:${PORT}/list-apps" >/dev/null 2>&1; then
    echo "Servidor pronto: http://127.0.0.1:${PORT} (PID ${PID})"
    echo "Logs:   ${LOG_FILE}"
    echo "Docs:   http://127.0.0.1:${PORT}/docs"
    echo "Stop:   PORT=${PORT} bash $(dirname "$0")/stop-server.sh"
    exit 0
  fi
done

echo "ERRO: servidor não respondeu em 30s. Últimas 30 linhas do log:" >&2
tail -30 "${LOG_FILE}" >&2
exit 1
