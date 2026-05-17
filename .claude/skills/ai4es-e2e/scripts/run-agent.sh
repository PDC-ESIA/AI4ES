#!/usr/bin/env bash
# Cria sessão + invoca /run para um agente. Prompt do stdin OU arquivo.
#
# Uso:
#   echo "construa X" | bash run-agent.sh orchestrator
#   bash run-agent.sh orchestrator prompts/foo.md
#
# Variáveis:
#   PORT       — porta (default 8081)
#   USER_ID    — id do usuário (default u_<timestamp>)
#   SESSION_ID — id da sessão (default s_<timestamp_ns>)
#
# Saída: JSON cru de /run (array de eventos). Use pretty-response.py para formatar.

set -euo pipefail

PORT="${PORT:-8081}"
APP="${1:-}"

if [ -z "${APP}" ]; then
  cat >&2 <<EOF
Uso: $0 <app_name> [prompt_file]
  Se prompt_file não for passado, lê o prompt do stdin.

Exemplos:
  echo "Construa um endpoint /healthcheck" | $0 orchestrator
  $0 orchestrator examples/healthcheck-prompt.md
EOF
  exit 1
fi

if [ -n "${2:-}" ]; then
  if [ ! -f "$2" ]; then
    echo "ERRO: prompt_file '$2' não existe." >&2
    exit 1
  fi
  PROMPT=$(cat "$2")
else
  PROMPT=$(cat)
fi

if [ -z "${PROMPT}" ]; then
  echo "ERRO: prompt vazio (stdin ou arquivo sem conteúdo)." >&2
  exit 1
fi

USER_ID="${USER_ID:-u_$(date +%s)}"
SESSION_ID="${SESSION_ID:-s_$(date +%s%N)}"
BASE="http://127.0.0.1:${PORT}"
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
PYTHON="${ROOT}/adk/.venv/bin/python"

if ! curl -sf "${BASE}/list-apps" >/dev/null 2>&1; then
  echo "ERRO: servidor não responde em ${BASE}/list-apps." >&2
  echo "       Rode: bash $(dirname "$0")/start-server.sh" >&2
  exit 1
fi

# Validate app exists
if ! curl -s "${BASE}/list-apps" | APP="${APP}" "${PYTHON}" -c "
import json, sys, os
apps = json.load(sys.stdin)
target = os.environ['APP']
if target not in apps:
    print(f'ERRO: app {target!r} não encontrado.', file=sys.stderr)
    print(f'Disponíveis: {sorted(apps)}', file=sys.stderr)
    sys.exit(1)
" ; then
  exit 1
fi

echo "==> Sessão: ${APP}/${USER_ID}/${SESSION_ID}" >&2
SESSION_HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
  "${BASE}/apps/${APP}/users/${USER_ID}/sessions/${SESSION_ID}" \
  -H "Content-Type: application/json" -d '{}')
if [ "${SESSION_HTTP}" != "200" ] && [ "${SESSION_HTTP}" != "201" ] && [ "${SESSION_HTTP}" != "409" ]; then
  echo "ERRO: criação de sessão retornou HTTP ${SESSION_HTTP}." >&2
  exit 1
fi
if [ "${SESSION_HTTP}" = "409" ]; then
  echo "    (sessão já existia, reutilizando)" >&2
fi

echo "==> Invocando ${APP} (pode levar segundos a minutos)..." >&2

PAYLOAD=$(APP="${APP}" USERID="${USER_ID}" SID="${SESSION_ID}" PROMPT="${PROMPT}" \
  "${PYTHON}" -c "
import json, os
print(json.dumps({
    'app_name': os.environ['APP'],
    'user_id': os.environ['USERID'],
    'session_id': os.environ['SID'],
    'new_message': {'role': 'user', 'parts': [{'text': os.environ['PROMPT']}]}
}))
")

curl -sf -X POST "${BASE}/run" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}"
