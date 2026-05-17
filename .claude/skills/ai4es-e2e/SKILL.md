---
name: ai4es-e2e
description: Subir o servidor ADK do AI4ES (FastAPI/uvicorn) e invocar qualquer agente via REST. Use quando o usuário pedir para "rodar o orquestrador", "testar e2e", "invocar o agente X", "subir o servidor dos agentes". Inclui scripts que encapsulam o ciclo session→run→pretty-print, mais diagnose pré-flight e inspeção pós-run.
---

# AI4ES E2E Agent Runner

Skill para executar agentes do AI4ES via REST com mínimo contexto pós-`/clear`.

## When to use

- "rode o orquestrador com [prompt]" / "testar SDLC end-to-end"
- "invocar o agente [X]"
- "subir o servidor dos agentes" / "start uvicorn dos agentes"
- "qual agentes estão disponíveis"
- O usuário quer iterar com os agentes via HTTP

## Project layout (essencial)

- App ADK: `adk/` (Python 3.12, gerenciado por `uv`, venv em `adk/.venv/`)
- Entrypoint: `app.main:app` (FastAPI auto-discovery de `src/agents/*/`)
- Modelo: `gemini-2.5-flash` via `GOOGLE_API_KEY` em `adk/.env` (override com `ADK_LLM_MODEL`)
- Porta default: 8081 (override com `PORT=8082`)
- Workspace de output: `./workspace_output/` (criado pela `init_workspace()` do `shared.workspace`)

20 agentes:
- **Entrada**: `orchestrator` (recomendado para SDLC completo)
- **Workflows**: `workflow_coding`, `workflow_coding_review`, `workflow_design_pipeline`, `workflow_qa`, `workflow_requirements`
- **Times 1-4**: `requirements`, `design_architect`, `design_orchestrator`, `mermaid_specialist`, `markdown_specialist`, `validator`, `io_agent`, `qa_agent`, `architect`, `context_engineer`, `coder`, `reviewer`, `test_planner`, `finalizer`

## Scripts (em `.claude/skills/ai4es-e2e/scripts/`)

Todos respeitam `PORT` env (default 8081). Use sempre via `bash <caminho>`.

| Script | Função |
|---|---|
| `diagnose.sh [agent]` | **Pré-flight**: schemas Gemini-compat, prompt↔tools, env, hardcoded paths |
| `start-server.sh` | Sobe uvicorn em background, aguarda /list-apps responder (até 30s) |
| `stop-server.sh` | Mata uvicorn na porta indicada |
| `list-apps.sh` | GET /list-apps (formatado) |
| `run-agent.sh <app> [prompt_file]` | Cria sessão + invoca /run (prompt do stdin se não passar arquivo) |
| `pretty-response.py` | Renderiza JSON de /run em formato legível (textos + tool calls + responses) |
| `e2e.sh <prompt_file>` | Lifecycle completo: start → run orchestrator → pretty-print |
| `snapshot.sh [dest]` | Copia workspace_output/ para fora (init_workspace apaga a cada run) |
| `inspect-run.sh [path]` | **Pós-run**: lista subpastas vazias, doubt artifacts, diagnostica gaps do SDLC |

## Fluxo recomendado (default — orchestrator)

```bash
# Pré-flight (~5s) — pega bugs antes de gastar quota Gemini
bash .claude/skills/ai4es-e2e/scripts/diagnose.sh

# Salvar a run anterior se quiser reaproveitar
bash .claude/skills/ai4es-e2e/scripts/snapshot.sh

# Rodar o SDLC completo
bash .claude/skills/ai4es-e2e/scripts/e2e.sh .claude/skills/ai4es-e2e/examples/healthcheck-prompt.md

# Analisar o resultado
bash .claude/skills/ai4es-e2e/scripts/inspect-run.sh
```

`e2e.sh` faz: sobe uvicorn (se preciso), lista agentes, cria sessão para `orchestrator`, envia o prompt, imprime resposta formatada.

Para parar o servidor depois: `bash .claude/skills/ai4es-e2e/scripts/stop-server.sh`.

## Known SDLC gaps (rodar com a expectativa correta)

O `orchestrator` chama 3 pipelines em sessões isoladas: **requirements → coding_review → qa**. Hoje a integração é parcial — leia antes de interpretar resultados.

### O que funciona

- ✓ Os 3 pipelines completam sem erro de schema (após os fixes recentes em `filesystem.py`, `git.py`, `pytest_runner.py`).
- ✓ `cr_coder_agent` escreve em `workspace_output/coder/` (isolado, não toca no repo).
- ✓ `cr_review_agent` escreve em `workspace_output/review/verificacao_revisao.md`.

### O que NÃO funciona ainda

- ❌ `workspace_output/requirements/` fica vazio. `tool_salvar_artefato_requisito` em `shared/tools/filesystem.py:266` hardcoda `docs/Time_1_Requisitos/{HUs,RFs,RNFs,RNs}` — os artefatos vão para lá, fora do workspace.
- ❌ `Doubt_Artifact_*.md` vão para `docs/Time_1_Requisitos/setup-ADK/AgenteAnalista/` (default de `gerar_doubt_artifact.caminho_base`). Procure com `find . -name 'Doubt_Artifact*.md' | grep -v .venv`.
- ❌ `workspace_output/tests/`, `tests/planning/`, `tests/fixes/`, `tests/inputs/` ficam vazios — `workflow_qa` não tem binding ao workspace e suas tools persistem com paths arbitrários decididos pelo LLM.
- ❌ `workspace_output/design/`, `architecture/`, `test_plans/`, `finalizer/` ficam vazios — o orchestrator atual (`src/agents/orchestrator/agent.py`) só roda 3 pipelines; design/architect/test_planner/finalizer não estão na sequência.
- ❌ `workflow_qa.action_planner` frequentemente devolve string vazia → o `generate` (gerador de doubt) é invocado com `trigger_type: planning_failure`. SDLC termina em "bloqueado" mesmo quando o coder gerou código válido.

### Roadmap de fix (ordem de impacto)

1. **Adicionar `base_dir: Optional[str] = None`** em `tool_salvar_artefato_requisito` e `gerar_doubt_artifact`. Incluir ambas em `_FILESYSTEM_TOOL_NAMES` em `shared/agent_factory.py:36`. Isso desbloqueia o workspace de requirements + doubts no lugar certo.
2. **Bindar tools do `workflow_qa`** (em `src/agents/workflow_qa/agent.py`) ao `get_agent_workspace("qa_agent")` — espelhar o que `workflow_coding_review` faz hoje.
3. **Estender o orchestrator** (`src/agents/orchestrator/agent.py`) para incluir `workflow_design_pipeline` entre requirements e coding_review, se quiser SDLC completo.
4. **Resolver o loop do `action_planner`** — investigar por que retorna string vazia (provavelmente requer ajuste de instruction + tools registradas).

## Fluxos alternativos

### Invocar um agente individual com prompt do stdin

```bash
bash .claude/skills/ai4es-e2e/scripts/start-server.sh
echo "Liste requisitos para um sistema de login" | \
  bash .claude/skills/ai4es-e2e/scripts/run-agent.sh requirements | \
  python3 .claude/skills/ai4es-e2e/scripts/pretty-response.py
```

### Diagnose um workflow específico

```bash
bash .claude/skills/ai4es-e2e/scripts/diagnose.sh workflow_coding_review
```

Útil ao introduzir uma tool nova ou mudar o prompt de um agente.

### Subir o app que o coder gerou

`workspace_output/coder/` é descartado na próxima run. Faça snapshot primeiro:

```bash
bash .claude/skills/ai4es-e2e/scripts/snapshot.sh /tmp/photo-app
cd /tmp/photo-app/coder
uv venv --python 3.12
VIRTUAL_ENV=$PWD/.venv uv pip install -r requirements.txt   # evita reutilizar venv do adk/
.venv/bin/uvicorn app.main:app --port 8090
```

`VIRTUAL_ENV` ou `uv run` é necessário porque `uv pip install` em um subdiretório pode reutilizar o `.venv` do `adk/` pai e nunca instalar localmente (sintoma: `Audited N packages` em vez de `+ pkg==versão`).

## Notas operacionais

- **`/openapi.json` retorna 500** (bug ADK 1.20, campo `httpx.Client` não-serializável). Use `/docs` (Swagger UI) — funciona.
- O `init_workspace()` apaga `workspace_output/` no import do `workflow_coding_review`. Use `snapshot.sh` antes de re-rodar.
- O orchestrator surfaceia doubts ao usuário via mensagens começando com 🚧. Em REST/CLI esses doubts vêm como texto na resposta; responda numa próxima invocação `/run` da mesma sessão.
- O `coder` agent NÃO deve usar git tools — quando tinha, sobrescreveu `adk/app/main.py` e criou branches aleatórias no repo principal. `workflow_coding_review/agent.py` agora remove `tool_git_*` do `cr_coder_agent` e substitui o `instruction`.
- Reset completo: `bash stop-server.sh; rm -rf adk/workspace_output/`.

## Troubleshooting

| Sintoma | Causa provável | Fix |
|---|---|---|
| `start-server.sh` falha com "venv não existe" | `.venv` não foi criado | `cd adk && uv sync` |
| Agente retorna 500 com "API key" | `GOOGLE_API_KEY` ausente | Verificar `adk/.env` |
| `run-agent.sh` retorna "app não encontrado" | Nome digitado errado | Rodar `list-apps.sh` primeiro |
| `400 INVALID_ARGUMENT ... additional_properties` | Tool usa `str \| None` ou `str \| dict` (gera anyOf rejeitado) | Use `Optional[str]`; rode `diagnose.sh` |
| `ValueError: Tool 'X' not found. Available: ...` | Prompt menciona tool não registrada | `diagnose.sh` lista as fantasmas; registre ou edite o prompt |
| Server sobe mas `/run` trava | Modelo em loop ou cota Gemini | `tail /tmp/ai4es-uvicorn-*.log` |
| `409 Conflict` ao criar sessão | Session ID já existe | Use `SESSION_ID=$(date +%s%N)` para gerar único |
| `workspace_output/requirements/` vazio após run | `tool_salvar_artefato_requisito` hardcoda path | Procure em `docs/Time_1_Requisitos/` (vide Known SDLC gaps) |
| `pretty-response.py: stdin não é JSON` | `/run` retornou 500 — schema rejeitado pelo Gemini ou tool ausente | `tail /tmp/ai4es-uvicorn-*.log` para ver o traceback real |
| Coder sobrescreveu repo + criou branches | Coder rodou sem workspace binding | Use `orchestrator` ou `workflow_coding_review` (que tem o binding) — nunca o `coder` solto contra o repo principal |
