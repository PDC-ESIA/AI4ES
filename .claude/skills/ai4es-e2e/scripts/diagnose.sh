#!/usr/bin/env bash
# Pré-flight check antes de rodar agentes. Detecta as armadilhas conhecidas:
#   1. Tools com schema Gemini-incompatível (any_of[null,str], additional_properties).
#   2. Tools que prometem persistência no workspace mas hardcodam paths externos.
#   3. Prompts que mencionam tools não registradas (causa de "Tool X not found").
#   4. Ambiente: .env / GOOGLE_API_KEY / .venv.
#
# Uso:
#   bash diagnose.sh                       # checa orchestrator + os 5 workflows
#   bash diagnose.sh <agent_name>          # checa um agente específico
#
# Exit code: 0 = saudável, 1 = problemas encontrados.

set -euo pipefail

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
ADK_DIR="${ROOT}/adk"
PYTHON="${ADK_DIR}/.venv/bin/python"

if [ ! -x "${PYTHON}" ]; then
  echo "ERRO: ${PYTHON} não existe. Rode: cd ${ADK_DIR} && uv sync" >&2
  exit 1
fi

TARGET="${1:-}"
EXIT=0

echo "===================="
echo "AI4ES E2E DIAGNOSE"
echo "===================="

# 1) Env check
echo ""
echo "[1/4] Ambiente"
if [ ! -f "${ADK_DIR}/.env" ]; then
  echo "  ❌ ${ADK_DIR}/.env ausente"
  EXIT=1
elif ! grep -q "^GOOGLE_API_KEY=" "${ADK_DIR}/.env"; then
  echo "  ❌ GOOGLE_API_KEY não definido em ${ADK_DIR}/.env"
  EXIT=1
else
  echo "  ✓ .env + GOOGLE_API_KEY ok"
fi

# 2) Tool schemas — caminho mais comum de falhar
echo ""
echo "[2/4] Schemas de tool (Gemini-compat)"
cd "${ADK_DIR}"
"${PYTHON}" - <<PYEOF
import sys, json
sys.path.insert(0, '.')

TARGETS = ["${TARGET}"] if "${TARGET}" else [
    "orchestrator",
    "workflow_requirements",
    "workflow_coding_review",
    "workflow_design_pipeline",
    "workflow_qa",
    "workflow_coding",
]

problems = []

def walk(agent, depth=0):
    name = getattr(agent, "name", "?")
    if hasattr(agent, "tools"):
        for i, t in enumerate(agent.tools):
            try:
                d = t._get_declaration()
                j = d.model_dump_json(exclude_none=True, by_alias=True)
                if "any_of" in j or "additional_properties" in j.lower() or "additionalproperties" in j.lower():
                    problems.append((name, i, d.name, j[:200]))
            except Exception as e:
                problems.append((name, i, f"<error: {e}>", ""))
    if hasattr(agent, "sub_agents"):
        for sa in agent.sub_agents:
            walk(sa, depth + 1)

for tname in TARGETS:
    try:
        mod = __import__(f"src.agents.{tname}.agent", fromlist=["agent"])
        agent = getattr(mod, "agent", None) or getattr(mod, "root_agent", None)
        walk(agent)
    except Exception as e:
        print(f"  ⚠️  {tname}: erro ao carregar — {e}")

if problems:
    print(f"  ❌ {len(problems)} tool(s) com schema problemático:")
    for agent_name, idx, tool_name, snippet in problems:
        print(f"     - {agent_name}[{idx}] {tool_name}")
    sys.exit(1)
else:
    print("  ✓ Nenhum schema problemático nos targets")
PYEOF
[ $? -ne 0 ] && EXIT=1

# 3) Tools mencionadas no prompt mas não registradas (alucinação garantida)
echo ""
echo "[3/4] Coerência prompt↔tools registradas"
"${PYTHON}" - <<'PYEOF'
import sys, re
sys.path.insert(0, '.')

TARGETS = [
    ("requirements", "src.agents.requirements.agent"),
    ("workflow_requirements", "src.agents.workflow_requirements.agent"),
    ("coder", "src.agents.coder.agent"),
    ("reviewer", "src.agents.reviewer.agent"),
]

TOOL_NAME_RX = re.compile(r"`(tool_[a-z_]+|gerar_doubt_artifact|run_slicer|ler_chunk|run_search|check_glossary|add_to_glossary|extract_text)`")

issues = []
for tname, modpath in TARGETS:
    try:
        mod = __import__(modpath, fromlist=["agent"])
        agent = getattr(mod, "agent", None) or getattr(mod, "root_agent", None)
        instruction = getattr(agent, "instruction", "") or ""
        registered = set()
        for t in getattr(agent, "tools", []):
            try:
                registered.add(t._get_declaration().name)
            except Exception:
                pass
        mentioned = set(TOOL_NAME_RX.findall(instruction))
        missing = mentioned - registered
        if missing:
            issues.append((tname, missing, registered))
    except Exception as e:
        print(f"  ⚠️  {tname}: erro — {e}")

if issues:
    for tname, missing, registered in issues:
        print(f"  ⚠️  {tname}: prompt menciona tools NÃO registradas → {sorted(missing)}")
        print(f"      registered: {sorted(registered)}")
else:
    print("  ✓ Nenhuma tool fantasma detectada")
PYEOF

# 4) Workspace isolation — tools de persistência aceitam base_dir e estão na lista de bind?
echo ""
echo "[4/4] Workspace isolation"
"${PYTHON}" - <<'PYEOF'
import sys
import inspect
sys.path.insert(0, '.')

# Tools que precisam aceitar base_dir E estar em _FILESYSTEM_TOOL_NAMES
# para serem auto-bound pelo agent_factory ao workspace_output/<agente>/.
PERSISTENCE_TOOLS = [
    ("tool_salvar_artefato_requisito", "shared.tools.filesystem"),
    ("gerar_doubt_artifact", "shared.tools.doubt_generator_analista"),
]

from shared.agent_factory import _FILESYSTEM_TOOL_NAMES

problems = []
for tool_name, modpath in PERSISTENCE_TOOLS:
    try:
        mod = __import__(modpath, fromlist=[tool_name])
        fn = getattr(mod, tool_name)
        sig = inspect.signature(fn)
        has_base_dir = "base_dir" in sig.parameters
        in_set = tool_name in _FILESYSTEM_TOOL_NAMES
        if not has_base_dir:
            problems.append(f"{tool_name}: assinatura NÃO tem `base_dir` (não pode ser bound)")
        elif not in_set:
            problems.append(f"{tool_name}: aceita `base_dir` mas NÃO está em _FILESYSTEM_TOOL_NAMES (não será auto-bound)")
    except Exception as e:
        problems.append(f"{tool_name}: erro ao carregar — {e}")

if problems:
    print(f"  ⚠️  {len(problems)} tool(s) de persistência mal-configuradas:")
    for p in problems:
        print(f"     - {p}")
    print("     → workspace_output/{requirements,tests,design}/ pode ficar vazio mesmo com SDLC bem-sucedido.")
    print("     → Fix: aceitar base_dir nessas tools e incluir em _FILESYSTEM_TOOL_NAMES (shared/agent_factory.py).")
else:
    print(f"  ✓ {len(PERSISTENCE_TOOLS)} tool(s) de persistência ok (aceitam base_dir + registradas no factory)")
PYEOF

echo ""
echo "===================="
if [ $EXIT -eq 0 ]; then
  echo "✓ DIAGNOSE OK"
else
  echo "❌ DIAGNOSE: problemas encontrados"
fi
echo "===================="
exit $EXIT
