## Estrutura

```
adk/
├── app/
│   └── main.py                  # Entry point FastAPI + ADK
├── agents/
│   ├── orchestrator/            # App ADK (root_agent) — entrada principal
│   │   ├── agent.py
│   │   └── prompt.py
│   ├── roles/                   # Agentes especialistas reutilizáveis
│   │   ├── coder/
│   │   ├── requirements/
│   │   ├── architect/
│   │   ├── test_planner/
│   │   ├── reviewer/
│   │   └── finalizer/
│   └── workflows/               # Composições (SequentialAgent, etc.)
│       ├── coding/              # Pipeline SDLC completo
│       └── pr_review/           # Revisão avulsa de PR
├── shared/
│   └── tools/
│       ├── git.py               # git add, commit, checkout, diff
│       └── filesystem.py        # criar arquivo, salvar relatório
├── tests/
│   ├── unit/
│   ├── integration/
│   └── evals/
├── .env
├── .env.example
└── pyproject.toml
```

## Execução local

Na raiz do diretório `adk/`:

```bash
uv sync
```

Copie `.env.example` para `.env` e preencha. Modelo padrão: **`github_copilot/gpt-4`** (sobrescreva com `ADK_LLM_MODEL`).

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8081
```

## GitHub Copilot (LiteLLM)

Os agentes usam o provedor **`github_copilot/`** via [LiteLLM](https://docs.litellm.ai/docs/providers/github_copilot).

1. **Requisito** — Conta com **GitHub Copilot** ativo.
2. **Primeira autenticação** — Na primeira chamada, siga o device flow no **terminal do uvicorn** (`https://github.com/login/device`).
3. **Tokens** — Salvos em `~/.config/litellm/github_copilot/` (configurável via `GITHUB_COPILOT_TOKEN_DIR`).

## Dev UI

- **Orquestrador:** `http://127.0.0.1:8081/dev-ui/?app=orchestrator`

O orquestrador decide entre o pipeline SDLC completo ou delegação pontual (coder / reviewer).
