#!/usr/bin/env bash
# Copia workspace_output/ para um diretório fora do repo antes de uma nova execução.
# Indispensável porque init_workspace() apaga o conteúdo a cada nova invocação
# do orchestrator (vide workflow_coding_review/agent.py).
#
# Uso:
#   bash snapshot.sh                              # /tmp/ai4es-snapshot-<timestamp>/
#   bash snapshot.sh /path/destino/               # diretório customizado
#   DEST=/tmp/foo bash snapshot.sh                # idem
#
# Saída: imprime o caminho final do snapshot.

set -euo pipefail

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
SRC="${ROOT}/adk/workspace_output"

if [ ! -d "${SRC}" ]; then
  echo "AVISO: ${SRC} não existe — nada para snapshot." >&2
  exit 0
fi

# Argumento posicional > env > default
DEST="${1:-${DEST:-/tmp/ai4es-snapshot-$(date +%Y%m%d-%H%M%S)}}"

if [ -e "${DEST}" ]; then
  echo "ERRO: destino '${DEST}' já existe — escolha outro caminho." >&2
  exit 1
fi

mkdir -p "$(dirname "${DEST}")"
cp -r "${SRC}" "${DEST}"

# Resumo
TOTAL_FILES=$(find "${DEST}" -type f | wc -l | tr -d ' ')
SIZE=$(du -sh "${DEST}" | cut -f1)
echo "Snapshot: ${DEST}"
echo "  ${TOTAL_FILES} arquivos, ${SIZE}"

# Lista subpastas não-vazias (útil pra detectar SDLC incompleto)
echo "  Subpastas com conteúdo:"
find "${DEST}" -maxdepth 2 -mindepth 1 -type d -not -empty | sort | while read -r d; do
  rel="${d#${DEST}/}"
  count=$(find "${d}" -maxdepth 1 -type f | wc -l | tr -d ' ')
  [ "${count}" -gt 0 ] && echo "    ${rel} (${count} arquivos)"
done
