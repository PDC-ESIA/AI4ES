# ADK — agentes e orquestração

## Estrutura

```text
adk/
├── app/
│   └── main.py                 # Entry point FastAPI + ADK (default agents_dir=src/agents)
├── src/
│   └── agents/                 # ← caminho padrão escaneado pelo adk web
│       ├── architect/
│       ├── coder/
│       ├── design_architect/
│       ├── design_orchestrator/
│       ├── finalizer/
│       ├── io_agent/
│       ├── markdown_specialist/
│       ├── mermaid_specialist/
│       ├── orchestrator/
│       ├── qa_agent/
│       ├── requirements/
│       ├── reviewer/
│       ├── test_planner/
│       ├── validator/
│       ├── workflow_coding/             # pipeline SDLC completo
│       ├── workflow_coding_review/      # pipeline enxuto requisitos→coder→review
│       └── workflow_design_pipeline/    # pipeline de design
├── shared/
│   └── tools/                  # tools compartilhadas (git, filesystem, slicer, etc)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── evals/
├── .env
├── .env.example
└── pyproject.toml
```

Cada subpasta de `src/agents/` é um agente runnável pelo ADK Dev UI. O `__init__.py` de cada agente exporta `root_agent`; a implementação principal vive em `agent.py`.

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

Dev UI: `http://127.0.0.1:8081/dev-ui/?app=<nome_do_agente>`

Exemplos:
- `?app=orchestrator` — orquestrador completo
- `?app=workflow_coding` — pipeline SDLC sequencial
- `?app=qa_agent` — agente de QA isolado
- `?app=requirements` — agente de requisitos com glossário

### Override de diretório (avançado)

Por padrão `app/main.py` escaneia `src/agents/`. Para apontar para outro diretório:

```bash
export ADK_AGENTS_DIR=outro/caminho
```

## Execução com Docker

Pré-requisito: **Docker** (e Docker Compose) instalados. Copie `.env.example` para `.env` e preencha.

**Opção A — sem build** (monta o código como volume, instala deps a cada start):

```bash
docker compose up
```

**Opção B — com build** (dependências embutidas na imagem, starts mais rápidos):

```bash
docker compose -f docker-compose.build.yml up --build
```

Acesse `http://localhost:8081/dev-ui/?app=orchestrator`.

### Primeira execução — autenticação obrigatória

Na **primeira vez** que o container subir, o LiteLLM iniciará o fluxo de autenticação OAuth do GitHub Copilot. Para completá-lo:

1. Abra os logs do container em um terminal:

```bash
docker compose logs -f
```

2. Procure por uma linha contendo um **código** e a URL `https://github.com/login/device`.
3. Abra a URL no navegador, cole o código e autorize.
4. Após a autorização, os tokens são salvos no volume `copilot-tokens` e **não será necessário repetir** este passo em execuções futuras.

> **Sem Docker:** o mesmo fluxo ocorre no terminal onde o `uvicorn` está rodando.

## GitHub Copilot (LiteLLM)

Os agentes usam o provedor **`github_copilot/`** via [LiteLLM](https://docs.litellm.ai/docs/providers/github_copilot).

1. **Requisito** — Conta com **GitHub Copilot** ativo.
2. **Primeira autenticação** — Na primeira chamada, siga o device flow no **terminal do uvicorn** (`https://github.com/login/device`).
3. **Tokens** — Salvos em `~/.config/litellm/github_copilot/` (configurável via `GITHUB_COPILOT_TOKEN_DIR`).
