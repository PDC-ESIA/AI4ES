#!/usr/bin/env bash
# Valida o app gerado pelo coder em workspace_output/coder/:
#   1. snapshot para /tmp (init_workspace apaga workspace_output a cada run)
#   2. uv venv + uv pip install -r requirements.txt
#   3. pytest -q tests/ (verde = bug 4 corrigido)
#   4. uvicorn sobe e responde GET /healthcheck com {"status": "ok"}
#
# Uso: bash verify-coder-output.sh [coder_dir]

set -euo pipefail

CODER_DIR="${1:-adk/workspace_output/coder}"
DEST="/tmp/coder-verify-$(date +%s)"
APP_PORT="${APP_PORT:-8090}"

if [ ! -d "${CODER_DIR}" ]; then
  echo "ERRO: Coder workspace não encontrado: ${CODER_DIR}" >&2
  exit 1
fi

echo "==> Snapshot ${CODER_DIR} → ${DEST}"
cp -r "${CODER_DIR}" "${DEST}"
cd "${DEST}"

echo "==> Criando venv (python 3.12)"
uv venv --python 3.12 --quiet

echo "==> Instalando requirements.txt"
if [ ! -f requirements.txt ]; then
  echo "ERRO: requirements.txt não encontrado em ${DEST}" >&2
  exit 1
fi
VIRTUAL_ENV="${DEST}/.venv" uv pip install -q -r requirements.txt

echo "==> Rodando pytest"
set +e
.venv/bin/pytest -q tests/
PYTEST_EXIT=$?
set -e

echo "==> Subindo uvicorn em :${APP_PORT}"
.venv/bin/uvicorn app.main:app --port "${APP_PORT}" >/tmp/coder-verify-uvicorn.log 2>&1 &
UVICORN_PID=$!
sleep 2

RESPONSE=$(curl -sf "http://127.0.0.1:${APP_PORT}/healthcheck" 2>/dev/null || echo "FAIL")
kill "${UVICORN_PID}" 2>/dev/null || true
wait "${UVICORN_PID}" 2>/dev/null || true

echo ""
echo "===================="
echo "RESULTADO"
echo "===================="
echo "pytest exit: ${PYTEST_EXIT}"
echo "endpoint response: ${RESPONSE}"
echo "snapshot em: ${DEST}"

if [ "${PYTEST_EXIT}" = "0" ] && echo "${RESPONSE}" | grep -q '"status":"ok"'; then
  echo "✓ Coder output verificado (pytest verde + endpoint responde)"
  exit 0
else
  echo "❌ Verification failed" >&2
  exit 1
fi
