#!/usr/bin/env bash
# Lifecycle completo de teste E2E: start server + run orchestrator + pretty-print.
#
# Uso: bash e2e.sh <prompt_file>
#
# Variáveis:
#   PORT      — porta (default 8081)
#   APP       — agente alvo (default orchestrator)
#   KEEP_UP   — se "1", não mata o servidor no fim (default desligado)

set -euo pipefail

PROMPT_FILE="${1:-}"
if [ -z "${PROMPT_FILE}" ] || [ ! -f "${PROMPT_FILE}" ]; then
  cat >&2 <<EOF
Uso: $0 <prompt_file>
  Exemplo: $0 .claude/skills/ai4es-e2e/examples/healthcheck-prompt.md
EOF
  exit 1
fi

PORT="${PORT:-8081}"
# Sessão persistente entre invocações (resposta ao HITL reusa o ID).
SESSION_FILE="${SESSION_FILE:-/tmp/ai4es-current-session.env}"
export SESSION_FILE
APP="${APP:-orchestrator}"
KEEP_UP="${KEEP_UP:-1}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "===================="
echo "AI4ES E2E TEST"
echo "===================="
echo "Prompt:  ${PROMPT_FILE}"
echo "App:     ${APP}"
echo "Port:    ${PORT}"
echo ""

PORT="${PORT}" bash "${SCRIPT_DIR}/start-server.sh"
echo ""
PORT="${PORT}" bash "${SCRIPT_DIR}/list-apps.sh" >&2
echo ""

RUN_OUTPUT=$(PORT="${PORT}" bash "${SCRIPT_DIR}/run-agent.sh" "${APP}" "${PROMPT_FILE}")
echo "${RUN_OUTPUT}" | "${SCRIPT_DIR}/pretty-response.py"

echo ""
echo "===================="
echo "Output em: ./workspace_output/"
echo "Doubts pendentes: find . -name 'Doubt_Artifact*.md' 2>/dev/null"
echo "===================="

PAUSED_PIPELINE=$(echo "${RUN_OUTPUT}" | python3 -c "
import json, sys
try:
    events = json.load(sys.stdin)
    for ev in events:
        actions = ev.get('actions') or {}
        delta = actions.get('state_delta') or {}
        if delta.get('paused_pipeline'):
            print(delta['paused_pipeline']); break
except Exception:
    pass
" 2>/dev/null)

if [ -n "${PAUSED_PIPELINE}" ]; then
  echo ""
  echo "🔶 [HITL] Pipeline pausado: ${PAUSED_PIPELINE}"
  echo "   Servidor MANTIDO em :${PORT} para você responder."
  echo "   Para retomar:"
  echo "     echo 'aprovar' | bash ${SCRIPT_DIR}/run-agent.sh ${APP}"
  echo "     (ou 'rejeitar' / 'solicitar_ajustes <comentários>')"
  echo "   Quando terminar: bash ${SCRIPT_DIR}/stop-server.sh"
  exit 0
fi

if [ "${KEEP_UP}" != "1" ]; then
  echo ""
  PORT="${PORT}" bash "${SCRIPT_DIR}/stop-server.sh"
else
  echo ""
  echo "✓ Pipeline completou. Servidor permanece em :${PORT} (KEEP_UP=1)."
  echo "  Para parar: bash ${SCRIPT_DIR}/stop-server.sh"
fi
