# ADK — agentes e orquestração

## Estrutura

```text
adk/
├── app/
│   └── main.py                  # Entry point FastAPI + ADK
├── runners/                     # Diretório escaneado pelo ADK (agents_dir)
│   └── orchestrator/            # Único app exposto — re-exporta root_agent
│       └── agent.py
├── agents/
│   ├── roles/                   # Agentes especialistas reutilizáveis
│   │   ├── orchestrator/        # root_agent (LlmAgent + AgentTools)
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

### Expor roles diretamente (somente dev)

Por padrão, o servidor expõe apenas os apps em `runners/` (produção). Para expor **roles** diretamente na Dev UI (útil para depurar/agir em um role específico), ajuste:

```bash
export ADK_AGENTS_DIR=agents/roles
```

Para voltar ao padrão:

```bash
export ADK_AGENTS_DIR=runners
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

1. Procure por uma linha contendo um **código** e a URL `https://github.com/login/device`.
1. Abra a URL no navegador, cole o código e autorize.
1. Após a autorização, os tokens são salvos no volume `copilot-tokens` e **não será necessário repetir** este passo em execuções futuras.

> **Sem Docker:** o mesmo fluxo ocorre no terminal onde o `uvicorn` está rodando.

## GitHub Copilot (LiteLLM)

Os agentes usam o provedor **`github_copilot/`** via [LiteLLM](https://docs.litellm.ai/docs/providers/github_copilot).

1. **Requisito** — Conta com **GitHub Copilot** ativo.
2. **Primeira autenticação** — Na primeira chamada, siga o device flow no **terminal do uvicorn** (`https://github.com/login/device`).
3. **Tokens** — Salvos em `~/.config/litellm/github_copilot/` (configurável via `GITHUB_COPILOT_TOKEN_DIR`).

## Dev UI

- **Orquestrador:** `http://127.0.0.1:8081/dev-ui/?app=orchestrator`

O orquestrador decide entre o pipeline SDLC completo ou delegação pontual (coder / reviewer).

## Testes

Na raiz do diretório `adk/`:

```bash
# Rodar todos os testes unitários
.venv/bin/python -m pytest tests/unit/ -v

# Rodar um arquivo específico
.venv/bin/python -m pytest tests/unit/test_llm_router.py -v
```

> **Importante:** Use `.venv/bin/python -m pytest` (não `pytest` direto) para garantir que o interpretador correto com as dependências instaladas seja utilizado.

### Estrutura de testes

| Diretório | Propósito |
|-----------|-----------|
| `tests/unit/` | Testes unitários (mocks, sem chamadas reais) |
| `tests/integration/` | Testes de integração (com serviços reais) |
| `tests/evals/` | Avaliações de qualidade dos agentes |

### Testes disponíveis

- `test_llm_router.py` — Router de fallback, client e `get_model()`
- `test_git_tools.py` — Tools Git do coder agent
- `test_filesystem_tools.py` — Tools de filesystem

## Monitoramento de Consumo

O Langfuse está **ativo por padrão** e registra métricas de tokens, latência e custo por agente.

- **Dashboard:** `http://localhost:3000` (Langfuse self-hosted via Docker Compose)
- **Credenciais padrão:** `admin@ai4es.local` / `admin1234`

### Verificação manual de consumo

Para checar se o consumo diário atingiu 80% do limite e disparar alerta via webhook:

```bash
.venv/bin/python -m scripts.check_usage
```

Variáveis necessárias no `.env`:
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
- `DAILY_TOKEN_LIMIT` (padrão: 1.000.000)
- `ALERT_WEBHOOK_URL` (Discord/Slack webhook — opcional, sem ele o alerta vai para stdout)
