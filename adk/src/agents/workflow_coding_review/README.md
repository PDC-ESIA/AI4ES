# Fluxo Coding Review (workflow_coding_review)

## 1. Visão Geral

- **Identificação:** Fluxo de Codificação com Revisão
- **Propósito:** Automatizar o ciclo completo de codificação → execução → correção → revisão, garantindo que o código produzido seja executável (validado em Docker) antes de passar por revisão com análise estática e LLM.
- **Stacks/Tecnologias:** Google ADK (SequentialAgent, LoopAgent, LlmAgent, AgentTool), Docker, Ruff, Bandit, Python, Pydantic

### Arquitetura do Pipeline

```
cr_context_engineer → LoopAgent[cr_coder ↔ cr_executor] → cr_reviewer
```

O `SequentialAgent` orquestra três etapas:
1. **Contextualização** — decompõe requisitos em tasks atômicas
2. **Loop de codificação/execução** — o coder implementa, o executor valida em Docker; repete até sucesso ou limite de iterações
3. **Revisão** — análise de qualidade em 4 camadas sobre o código aprovado

---

## 2. Funcionalidades

### cr_context_engineer

| Aspecto | Detalhe |
|---|---|
| **Responsabilidade** | Recebe requisitos em linguagem natural e os fragmenta em tasks de codificação contextualizadas (Context Windows), enriquecidas com contexto arquitetural, regras globais e contratos de dependência |
| **Limite** | Não implementa código. Não define requisitos de negócio. Apenas contextualiza e empacota |
| **Saída** | Arquivos JSON individuais (`TASK-XXX.json`) + schema `TasksOutput` em `state["tasks"]` |
| **Tools** | `_tool_salvar_task_cr` (persistência em `workspace_output/cr_context_engineer/`) |

### cr_coder

| Aspecto | Detalhe |
|---|---|
| **Responsabilidade** | Implementa projeto completo (app, testes, Dockerfile, docker-compose.yml) a partir das tasks. Em re-execução, corrige código com base no ErrorReport do executor |
| **Limite** | Não faz Git. Não toma decisões de produto. Opera apenas via tools de filesystem |
| **Saída** | Código-fonte em `workspace_output/cr_coder/` + `state["implementation"]` |
| **Tools** | `tool_criar_arquivo`, `tool_ler_arquivo`, `tool_substituir_trecho`, `tool_ler_workspace`, `tool_listar_workspace` |

### cr_executor

| Aspecto | Detalhe |
|---|---|
| **Responsabilidade** | Builda e roda o código em Docker via harness, invoca o `implementation_validator` (AgentTool), monta ErrorReport determinístico quando reprovado, controla encerramento do loop via `exit_loop` |
| **Limite** | Não corrige código. Não prescreve soluções. Apenas reporta o que falhou com evidência bruta |
| **Saída** | `state["execution_result"]` (ErrorReport JSON ou texto), `state["validation"]` (veredito) |
| **Tools** | `executar_harness_tool`, `AgentTool(implementation_validator)`, `exit_loop` |

### cr_reviewer

| Aspecto | Detalhe |
|---|---|
| **Responsabilidade** | Revisão de código em 4 camadas (completude, arquitetura, corretude, testes). Injeta findings de Ruff e Bandit via `before_agent_callback`. Persiste relatório via `after_agent_callback` (sem LLM no passo de escrita) |
| **Limite** | Não aprova/reprova execução Docker. Não altera código |
| **Saída** | `state["review_analysis"]` + arquivo `verificacao_revisao.md` em `workspace_output/cr_reviewer/` |
| **Tools** | `tool_ler_arquivo` (bound ao workspace do coder) |

### Comportamento do Loop

- Máximo de iterações: 5 (configurável via `AI4ES_MAX_LOOP_ITERATIONS`)
- **Encerramento por aprovação:** executor chama `exit_loop` quando o veredito é "aprovado"
- **Encerramento por estagnação:** executor detecta que o coder não alterou código entre iterações e encerra com status "bloqueado"
- **Fallback:** se o limite for atingido, o código segue para revisão mesmo com falha

---

## 3. Como executar ou testar

### Pré-requisitos

- Python 3.12+
- `uv` instalado
- Docker instalado e rodando
- Arquivo `.env` com provedor LLM configurado

### Instalação

```bash
uv sync
```

### Execução

**Via orquestrador (pipeline completo):**

O `orchestrator` invoca o fluxo automaticamente como terceira etapa do SDLC:
```
requirements_pipeline → design_pipeline → coding_review_pipeline → qa_pipeline
```

**Isoladamente:**

```python
from src.agents.workflow_coding_review.agent import agent
# agent é um SequentialAgent pronto para ser executado via ADK Runner
```

### Variáveis de ambiente

| Variável | Descrição | Default |
|---|---|---|
| `ADK_LLM_MODEL` | Modelo LLM utilizado por todos os sub-agentes | `gemini-2.5-flash` |
| `AI4ES_MAX_LOOP_ITERATIONS` | Máximo de iterações do loop coder↔executor | `5` |
| `WORKSPACE_OUTPUT_DIR` | Diretório raiz de saída dos artefatos | `./workspace_output` |
| `REVIEWER_STATIC_ANALYSIS` | `"0"` desabilita análise estática (Ruff/Bandit) pré-LLM | `"1"` (habilitado) |

### Suíte de testes

```bash
uv run pytest tests/unit/test_context_engineer.py \
             tests/unit/test_cr_executor.py \
             tests/unit/test_review_agent_persistence.py \
             tests/unit/test_harness_execucao.py \
             tests/integration/test_harness_poc.py -v
```

| Arquivo de teste | Cobertura |
|---|---|
| `tests/unit/test_context_engineer.py` | Schemas (TasksOutput, Contract, Task) + tool de persistência |
| `tests/unit/test_cr_executor.py` | Topologia do loop, tools, callbacks, ErrorReport |
| `tests/unit/test_review_agent_persistence.py` | Callback de persistência, descoberta de arquivos, análise estática |
| `tests/unit/test_harness_execucao.py` | Harness Docker (build, run, relatórios) |
| `tests/integration/test_harness_poc.py` | Integração Docker end-to-end |

---

## 4. Entradas e Saídas

### Entrada

Requisitos em linguagem natural, acumulados pelo orquestrador a partir das fases anteriores (requirements + design).

### States intermediários

| State key | Produtor | Consumidor |
|---|---|---|
| `tasks` | cr_context_engineer | cr_coder |
| `implementation` | cr_coder | cr_executor |
| `execution_result` | cr_executor | cr_coder (re-execução) |
| `validation` | cr_executor (via callback do validador) | cr_executor (para montar ErrorReport) |
| `review_analysis` | cr_reviewer | pipeline finalizado |

### Artefatos em disco

| Diretório | Conteúdo |
|---|---|
| `workspace_output/cr_context_engineer/` | `TASK-001.json`, `TASK-002.json`, ... |
| `workspace_output/cr_coder/` | Código-fonte completo (app/, tests/, Dockerfile, docker-compose.yml, PLAN.md) |
| `workspace_output/cr_executor/` | Relatórios de execução Docker (`<task_id>.report.json`) |
| `workspace_output/cr_reviewer/` | `verificacao_revisao.md` |

### Saída final

- `state["review_analysis"]` — markdown com status (APROVADO/BLOQUEADO), issues e resumo
- Arquivo `verificacao_revisao.md` persistido em disco

---

## 5. Cenário de Teste Específico

A ser definido.

---

## 6. Lista de Erros Identificados

A ser definido.
