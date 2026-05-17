#!/usr/bin/env bash
# Análise pós-run de uma execução do orchestrator. Diferente do pretty-response,
# este foca em SAÚDE do SDLC — quem rodou, quem ficou vazio, quais Doubt_Artifacts
# vieram, qual subdomínio do workspace foi populado.
#
# Uso:
#   bash inspect-run.sh                          # inspeciona workspace_output/ atual
#   bash inspect-run.sh /path/snapshot           # inspeciona um snapshot
#
# Saída: relatório em texto.

set -euo pipefail

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
WS="${1:-${ROOT}/adk/workspace_output}"

if [ ! -d "${WS}" ]; then
  echo "ERRO: '${WS}' não existe." >&2
  exit 1
fi

echo "===================="
echo "AI4ES RUN INSPECTOR"
echo "Workspace: ${WS}"
echo "===================="

# Subpastas esperadas (vide shared/workspace.py AGENT_DIRS)
EXPECTED=(
  "requirements"
  "requirements/glossario"
  "design"
  "design/diagrams"
  "design/reports"
  "design/validation"
  "design/staging"
  "tests"
  "tests/planning"
  "tests/fixes"
  "tests/inputs"
  "tasks"
  "architecture"
  "test_plans"
  "coder"
  "review"
  "finalizer"
  "orchestrator"
  "pipeline"
)

POPULATED=()
EMPTY=()
for d in "${EXPECTED[@]}"; do
  full="${WS}/${d}"
  if [ -d "${full}" ]; then
    count=$(find "${full}" -maxdepth 1 -type f 2>/dev/null | wc -l | tr -d ' ')
    if [ "${count}" -gt 0 ]; then
      POPULATED+=("${d} (${count})")
    else
      EMPTY+=("${d}")
    fi
  fi
done

echo ""
echo "## Subpastas com conteúdo (${#POPULATED[@]}/${#EXPECTED[@]}):"
for x in "${POPULATED[@]}"; do echo "  ✓ ${x}"; done

echo ""
echo "## Subpastas vazias — pipeline NÃO produziu artefatos lá:"
for x in "${EMPTY[@]}"; do echo "  ❌ ${x}"; done

# Doubt artifacts (em qualquer lugar do repo, não só workspace)
echo ""
echo "## Doubt_Artifacts encontrados:"
DOUBTS=$(find "${ROOT}" -name 'Doubt_Artifact*.md' 2>/dev/null | grep -v ".venv/" || true)
if [ -z "${DOUBTS}" ]; then
  echo "  (nenhum)"
else
  echo "${DOUBTS}" | while read -r f; do
    echo "  - ${f#${ROOT}/}"
  done
fi

# Total
echo ""
TOTAL=$(find "${WS}" -type f 2>/dev/null | wc -l | tr -d ' ')
SIZE=$(du -sh "${WS}" 2>/dev/null | cut -f1)
echo "## Total: ${TOTAL} arquivos, ${SIZE}"

# Diagnóstico
echo ""
echo "## Diagnóstico do SDLC:"
if [[ " ${EMPTY[*]} " =~ " requirements " ]]; then
  echo "  ⚠️  workflow_requirements rodou mas não persistiu HUs/RFs em workspace_output/requirements/."
  echo "     Causa conhecida: tool_salvar_artefato_requisito hardcoda 'docs/Time_1_Requisitos/' (ignora workspace)."
  echo "     Verifique: ls ${ROOT}/docs/Time_1_Requisitos/HUs/ — os artefatos podem ter ido pra lá."
fi
if [[ " ${EMPTY[*]} " =~ " tests " ]] || [[ " ${EMPTY[*]} " =~ " tests/planning " ]]; then
  echo "  ⚠️  workflow_qa não persistiu artefatos em workspace_output/tests/."
  echo "     Causa conhecida: workflow_qa não foi bindado em _bind_tool_to_workspace."
fi
if [[ " ${EMPTY[*]} " =~ " design " ]]; then
  echo "  ℹ️  workflow_design_pipeline não está no orchestrator atual (orchestrator/agent.py: requirements → coding_review → qa)."
fi
