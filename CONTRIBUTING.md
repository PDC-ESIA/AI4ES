# Contribuindo com o Projeto (Gitflow)

Este projeto utiliza o fluxo de trabalho **Gitflow** para gerenciar o versionamento de código. Suas contribuições devem seguir este padrão.

## Branches Principais

- **`main`** (ou `master`): Reflete o estado exato da produção. Restrita a merges vindos de `release` ou `hotfix`.
- **`develop`**: Branch principal de desenvolvimento. O código atual da próxima versão fica centralizado aqui.

## Como Contribuir

### 1. Novas Funcionalidades (`feature/`)
Crie sempre a partir da `develop`. **Obrigatório incluir o número da issue no nome**:
```bash
git checkout develop
git checkout -b feature/123-nome-da-sua-feature
```
*Ao finalizar, abra um Pull Request (PR) para a `develop`.*

### 2. Correções Emergenciais (`hotfix/`)
Para bugs críticos em produção, crie a partir da `main`. **Inclua o número da issue do bug**:
```bash
git checkout main
git checkout -b hotfix/124-nome-do-bug
```
*Após corrigir, faça o merge tanto na `main` (gerando nova tag) quanto na `develop`.*

### 3. Lançamentos (`release/`)
Para compilar uma nova versão, crie a partir da `develop`:
```bash
git checkout develop
git checkout -b release/vX.Y.Z
```
*Faça os últimos ajustes e, ao concluir, submeta o merge para a `main` (com tag) e para a `develop`.*

## Pull Requests (PR)

1. **Branch de destino**
   - `feature/*` → `develop`
   - `hotfix/*` → `main` (e depois garantir o merge de volta em `develop`, conforme o fluxo de hotfix)
   - `release/*` → `main` e `develop`, conforme o processo de release

2. **Título e descrição**
   - O título deve ser claro e, quando houver issue, **incluir o número** (ex.: `#123 — Descrição curta`).
   - Na descrição, **referencie a issue** (`Closes #123`, `Refs #123` ou link) e resuma o que mudou e por quê.
   - Se o PR for grande ou depender de contexto, liste pontos de atenção para quem revisa.

3. **Antes de abrir ou marcar como pronto**
   - Sincronize com a branch de destino e resolva conflitos localmente.
   - Garanta que commits e mensagens sigam as [Regras Gerais](#regras-gerais) (issue no nome da branch e nas mensagens, quando aplicável).

4. **Revisão e merge**
   - Aguarde aprovação conforme as políticas do repositório; não faça merge direto em `main` ou `develop`.
   - Prefira PRs **pequenos e focados** em uma mudança ou tarefa; facilita revisão e rollback.

## Criando Agentes (ADK)

O projeto utiliza o [Google ADK](https://google.github.io/adk-docs/) com a seguinte convenção de diretórios dentro de `adk/`:

| Camada       | Caminho                  | Finalidade                                                                 |
| ------------ | ------------------------ | -------------------------------------------------------------------------- |
| **Role**     | `agents/roles/<nome>/`   | Agente especialista individual (`LlmAgent`)                                |
| **Workflow** | `agents/workflows/<nome>/` | Composição de roles (`SequentialAgent`, `ParallelAgent`, …)              |
| **Runner**   | `runners/<nome>/`        | Entry point ADK — re-exporta um `root_agent` para ser exposto via FastAPI  |

### 1. Criar um novo Role

Crie a pasta `agents/roles/<nome>/` com no mínimo:

```text
agents/roles/meu_agente/
├── __init__.py
├── agent.py      # exporta `agent` (instância de LlmAgent)
└── prompt.py     # exporta `description` e `instruction`
```

Opcionalmente inclua `schemas.py` (Pydantic, para `output_schema`) e `tools.py`.

Exemplo mínimo de `agent.py`:

```python
import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from . import prompt

agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", "github_copilot/gpt-4")),
    name="meu_agente",
    description=prompt.description,
    instruction=prompt.instruction,
)
```

### 2. Adicionar o role ao orquestrador

O orquestrador (`agents/roles/orchestrator/agent.py`) é o único agente exposto ao usuário. Para que um novo role seja acessível, registre-o como `AgentTool`:

1. Importe o agente no arquivo do orquestrador:

```python
from agents.roles.meu_agente.agent import agent as meu_agente
```

2. Adicione à lista `tools` do `root_agent`:

```python
from google.adk.tools.agent_tool import AgentTool

root_agent = LlmAgent(
    ...
    tools=[
        ...,                            # ferramentas já existentes
        AgentTool(agent=meu_agente),    # novo role
    ],
)
```

3. Atualize o prompt do orquestrador (`agents/roles/orchestrator/prompt.py`) para que ele saiba **quando** e **por que** acionar o novo agente. Sem essa orientação no prompt, o orquestrador pode nunca invocá-lo.

> **Dica:** Se o novo role deve fazer parte de um workflow existente (ex.: pipeline SDLC), insira-o na lista `sub_agents` do `SequentialAgent` correspondente em `agents/workflows/` em vez de adicioná-lo diretamente ao orquestrador.

### 3. Criar um novo Workflow

Crie `agents/workflows/<nome>/agent.py` exportando um `SequentialAgent` (ou `ParallelAgent`) que referencia roles existentes:

```python
from google.adk.agents import SequentialAgent
from agents.roles.x.agent import agent as x_agent
from agents.roles.y.agent import agent as y_agent

agent = SequentialAgent(
    name="meu_workflow",
    description="...",
    sub_agents=[x_agent, y_agent],
)
```

Registre o workflow como `AgentTool` no orquestrador, assim como faria com um role.

### 4. Expor um novo app ADK (runner)

Se necessário expor outro app além do orquestrador, crie `runners/<nome>/agent.py` re-exportando o `root_agent`:

```python
from agents.roles.<origem>.agent import <variavel> as root_agent  # noqa: F401
```

O ADK descobre automaticamente subpastas de `runners/` que contenham `agent.py` com `root_agent`.

## Regras Gerais

- **Nomenclatura de Branches**: Siga o padrão `tipo/numero-da-issue-breve-descricao` (ex: `feature/42-adicionar-login`).
- **Branches Protegidas**: As branches `main` e `develop` são protegidas. O código deve ser integrado a elas **exclusivamente via Pull Request (PR)**. Nunca realize commits diretos.
- **Commits Descritivos**: A mensagem do commit deve ser curta, objetiva e sempre **conter a referência ao número da issue** de trabalho (ex: `#42 Adiciona validação de login`).
- **Sincronização**: Antes de finalizar sua tarefa, sincronize sua branch com as mudanças mais recentes da branch de destino (ex: `git pull origin develop`).
