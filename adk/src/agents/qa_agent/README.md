# QA Agent

O QA Agent planeja, gera, executa e normaliza testes automatizados a partir do
código persistido e dos artefatos de requisitos disponíveis.

## Níveis e stacks

| Nível | Python/FastAPI | Node/Express JS/TS | Java/Spring | Go |
| --- | --- | --- | --- | --- |
| Unitário | pytest | Jest, Vitest, Mocha ou `node:test` | JUnit/Maven ou Gradle | `go test` |
| Integração | pytest | runner declarado pelo projeto | JUnit/Maven ou Gradle | `go test` |
| E2E | Playwright | Playwright | Playwright | Playwright |

A stack vem primeiro do `tech_stack` entregue ao Coder. Os manifests do projeto
são usados como fallback. A estrutura está descrita em
[`TEST_AGENT_STRUCTURE.md`](./TEST_AGENT_STRUCTURE.md).

## Fluxo

```text
entrada → planejamento → inspeção → perfil → geração → execução → normalização
```

- `action_planner` limita o escopo e seleciona o nível solicitado;
- cada gerador escolhe um perfil compatível com o projeto;
- os executores usam comandos definidos pelo perfil;
- falhas de runtime, dependência ou contrato retornam bloqueios estruturados;
- o agente altera somente arquivos de teste.

O `pytest_runner` existente permanece responsável pelo perfil Python unitário e
não é usado como fallback para outras stacks.

## Executar

Na pasta `adk`:

```powershell
uv sync
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8081
```

Use `ADK_AGENTS_DIR=src/agents` e abra
`http://127.0.0.1:8081/dev-ui/?app=workflow_qa`.

## Validar

```powershell
# Testes automatizados dos perfis e adaptadores
.\.venv\Scripts\python.exe -m pytest `
  tests/unit/test_profile_based_test_agents.py `
  tests/unit/test_multistack_integration_adapters.py `
  tests/unit/test_result_normalization.py -q

# Matriz real de integração e E2E
.\.venv\Scripts\python.exe -m pytest `
  tests/integration/test_multistack_profiles_real.py -q
```

Os comandos completos de reprodução e os caminhos das evidências estão em
[`QA_AUTOMATED_HANDOFF.md`](../../../../docs/Time_3_Testes/evidencias/QA_AUTOMATED_HANDOFF.md).

## Contrato de saída

Os três níveis retornam `status`, `tipo_teste`, `inspecao`, `perfil`, `resumo`,
`arquivos_gerados`, `detalhes` e `bloqueios`. Integração e E2E também preservam
o resultado original do executor em `resultado_bruto`.

Dependências não são instaladas pelos executores. O runtime e as dependências
declaradas devem estar preparados antes da execução.
