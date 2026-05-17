---
name: ai4es-e2e
description: Subir o servidor ADK do AI4ES (FastAPI/uvicorn) e invocar qualquer agente via REST. Use quando o usuário pedir para "rodar o orquestrador", "testar e2e", "invocar o agente X", "subir o servidor dos agentes". Inclui scripts que encapsulam o ciclo session→run→pretty-print.
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

Todos respeitam `PORT` env (default 8081). Use sempre via `bash <caminho>` para garantir execução.

| Script | Função |
|---|---|
| `start-server.sh` | Sobe uvicorn em background, aguarda /list-apps responder (até 30s) |
| `stop-server.sh` | Mata uvicorn na porta indicada |
| `list-apps.sh` | GET /list-apps (formatado) |
| `run-agent.sh <app> [prompt_file]` | Cria sessão + invoca /run (prompt do stdin se não passar arquivo) |
| `pretty-response.py` | Renderiza JSON de /run em formato legível (textos + tool calls + responses) |
| `e2e.sh <prompt_file>` | Lifecycle completo: start → run orchestrator → pretty-print |

## Fluxo recomendado (default — orchestrator)

```bash
bash .claude/skills/ai4es-e2e/scripts/e2e.sh .claude/skills/ai4es-e2e/examples/healthcheck-prompt.md
```

Esse comando:
1. Sobe uvicorn (se já não estiver rodando)
2. Lista agentes (sanity check)
3. Cria sessão para `orchestrator`
4. Envia o prompt do arquivo
5. Imprime resposta formatada (eventos, tool calls, output final)

Para parar o servidor depois: `bash .claude/skills/ai4es-e2e/scripts/stop-server.sh`

## Fluxos alternativos

### Invocar um agente individual com prompt do stdin

```bash
bash .claude/skills/ai4es-e2e/scripts/start-server.sh
echo "Liste requisitos para um sistema de login" | \
  bash .claude/skills/ai4es-e2e/scripts/run-agent.sh requirements | \
  python3 .claude/skills/ai4es-e2e/scripts/pretty-response.py
```

### Inspecionar resultado depois

- `ls workspace_output/` — outputs por agente
- `find . -name 'Doubt_Artifact*.md'` — dúvidas pendentes
- `tail /tmp/ai4es-uvicorn-8081.log` — log do servidor

## Notas operacionais

- **`/openapi.json` retorna 500** (bug ADK 1.20, campo `httpx.Client` não-serializável). Use `/docs` (Swagger UI) — funciona.
- O `init_workspace()` apaga `workspace_output/` a cada session. Salve outputs importantes antes de re-rodar.
- O orchestrator surfaceia doubts ao usuário via mensagens começando com 🚧. Em modo REST/CLI, esses doubts aparecem como texto na resposta — você precisa responder em uma próxima invocação `/run` na mesma sessão.
- Para reset completo: `bash stop-server.sh && rm -rf workspace_output/`.

## Troubleshooting

| Sintoma | Causa provável | Fix |
|---|---|---|
| `start-server.sh` falha com "venv não existe" | `.venv` não foi criado | `cd adk && uv sync` |
| Agente retorna 500 com "API key" | `GOOGLE_API_KEY` ausente | Verificar `adk/.env` |
| `run-agent.sh` retorna "app não encontrado" | Nome digitado errado | Rodar `list-apps.sh` primeiro |
| Server sobe mas `/run` trava | Modelo em loop ou cota Gemini | `tail /tmp/ai4es-uvicorn-*.log` |
| `409 Conflict` ao criar sessão | Session ID já existe | Use `SESSION_ID=$(date +%s%N)` para gerar único |
