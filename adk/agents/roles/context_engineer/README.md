# Agente Context Engineer
**Time:** Codificação  
**Modelo:** github_copilot/gpt-4 (padrão) — sobrescreva com `ADK_LLM_MODEL`

---

## O que este agente faz

Recebe requisitos atômicos gerados pelo `requirements_agent` e os transforma em
**tarefas de codificação contextualizadas** (Context Windows), enriquecidas com
contexto arquitetural, regras globais e contratos de dependência.

Persiste cada task como arquivo JSON individual no workspace do projeto.

O agente NÃO implementa código. NÃO define requisitos. Apenas contextualiza e empacota.

---

## Posição no Pipeline SDLC

```
requirements_agent → context_engineer → architecture_agent → test_planner → coder → reviewer → finalizer
```

- **Entrada:** `state["requirements"]` (saída do `requirements_agent`)
- **Saída:** `state["tasks"]` (consumida pelos agentes subsequentes)

---

## Estrutura de arquivos

```
agents/roles/context_engineer/
├── __init__.py
├── agent.py          — definição do LlmAgent
├── prompt.py         — description + instruction
├── schemas.py        — MacroContext, Contract, Task, TasksOutput
├── tools.py          — tool: persistência de tasks no workspace
└── README.md
```

---

## Schema de saída

```json
{
  "macro_context": {
    "epic_slug": "epic-login",
    "epic_summary": "Implementação do fluxo de autenticação de usuários",
    "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
    "global_rules": ["Usar SQLAlchemy", "API RESTful", "JWT para autenticação"]
  },
  "tasks": [
    {
      "id": "TASK-001",
      "type": "backend",
      "complexity": "medium",
      "description": "Criar endpoint POST /auth/login que valida credenciais e retorna JWT",
      "business_rules": ["Token expira em 8 horas", "Bloquear após 5 tentativas falhas"],
      "acceptance_criteria": [
        "Endpoint retorna 200 com token JWT válido para credenciais corretas",
        "Endpoint retorna 401 para credenciais inválidas",
        "Conta é bloqueada após 5 tentativas falhas consecutivas"
      ],
      "contract": {
        "inputs": ["src/models/user.py"],
        "outputs": ["src/routes/auth.py"],
        "interfaces": "def login(email: str, password: str) -> TokenResponse"
      }
    }
  ]
}
```

---

## Persistência no Workspace

As tasks são salvas em disco via `tool_salvar_task`. A estrutura do workspace é:

```
$WORKSPACE_OUTPUT_DIR/
├── _global/                        ← Contratos compartilhados entre épicos
│   ├── architecture.json
│   └── shared_interfaces.json
└── <epic-slug>/
    ├── tasks/                      ← Context Engineer escreve aqui
    │   ├── TASK-001.json
    │   └── TASK-002.json
    ├── coder/                      ← Agente Coder escreve aqui
    ├── review/                     ← Agente Review escreve aqui
    └── pipeline/                   ← CI/CD
```

**Variável de ambiente:** `WORKSPACE_OUTPUT_DIR` (default: `./workspace_output`)

---

## Tools disponíveis

| Tool | Quando é chamada |
|------|-----------------|
| `tool_salvar_task` | Para cada task gerada, persiste o JSON no workspace |

---

## Como testar localmente

### Cenário 1 — PRD simples (deve gerar 1-2 tasks)
```
crie uma página HTML com o conteúdo Hello World
```

### Cenário 2 — PRD com múltiplos requisitos (deve gerar múltiplas tasks com contratos)
```
Módulo: Autenticação de Usuários
O sistema deve suportar dois perfis: Aluno e Professor.
Login via e-mail e senha com token JWT de 8 horas.
Bloqueio após 5 tentativas falhas consecutivas por 15 minutos.
Professores podem criar turmas e visualizar relatórios.
```

### Verificação
1. O JSON de saída contém `macro_context` e `tasks`?
2. Cada task possui `contract` com `inputs` e `outputs`?
3. Os arquivos `TASK-XXX.json` foram criados em `$WORKSPACE_OUTPUT_DIR/<epic>/tasks/`?
