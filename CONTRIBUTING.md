# Contribuindo com o Projeto (Gitflow)

Este projeto utiliza o fluxo de trabalho **Gitflow** para gerenciar o versionamento de código. Suas contribuições devem seguir este padrão.

## Branches Principais

- **`main`**: Reflete o estado exato da produção. Restrita a merges vindos de `release` ou `hotfix`.
- **`develop`**: Branch principal de desenvolvimento. O código atual da próxima versão fica centralizado aqui.

## Como Contribuir

### 1. Novas Funcionalidades (`feature/`)
Crie sempre a partir da `develop`. **Obrigatório incluir o prefixo da equipe e o número da issue**:
```bash
git checkout develop
git checkout -b feature/code/123-nome-da-sua-feature
```
*Ao finalizar, abra um Pull Request (PR) para a `develop`.*

### 2. Correções Emergenciais (`hotfix/`)
Para bugs críticos em produção, crie a partir da `main`. **Inclua o prefixo da equipe e o número da issue**:
```bash
git checkout main
git checkout -b hotfix/code/124-nome-do-bug
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
| **Runner**   | `runners/<nome>/`        | Entry point ADK - re-exporta um `root_agent` para ser exposto via FastAPI. Na prática, filtra os agentes root  |

### 1. Criar um novo Role

Crie a pasta `agents/roles/<nome>/` com no mínimo:

```text
agents/roles/meu_agente/
├── __init__.py
├── agent.py      # exporta `agent` (instância de Agent)
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

### 2. Adicionar o role a um Workflow

O orquestrador **não executa roles diretamente**. Ele é um `LlmAgent` de roteamento que decide qual **workflow** (`AgentTool`) acionar com base no pedido do usuário. Cada workflow compõe roles em sequência ou paralelo.

Portanto, um novo role de engenharia de software deve ser inserido no workflow adequado (e não no orquestrador):

```python
# agents/workflows/coding/agent.py
agent = SequentialAgent(
    name="sdlc_pipeline",
    sub_agents=[
        requirements_agent,
        architecture_agent,
        test_planning_agent,
        implementation_agent,   # roles existentes
        review_agent,
        meu_novo_role,          # ← insira aqui
        finalization_agent,
    ],
)
```

Depois, atualize o prompt do orquestrador (`agents/roles/orchestrator/prompt.py`) para descrever a nova capacidade que o workflow ganhou.

### 3. Criar um novo Workflow

Se o role não se encaixa em nenhum workflow existente, crie um novo em `agents/workflows/<nome>/agent.py`:

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

Em seguida, registre-o como `AgentTool` no orquestrador para que ele possa selecioná-lo:

```python
# agents/roles/orchestrator/agent.py
from agents.workflows.meu_workflow.agent import agent as meu_workflow

root_agent = LlmAgent(
    ...
    tools=[
        AgentTool(agent=sdlc_pipeline),       # workflow existente
        AgentTool(agent=meu_workflow),         # ← novo workflow
        AgentTool(agent=coder_specialist),
        AgentTool(agent=reviewer_specialist),
    ],
)
```

Atualize também o prompt do orquestrador para que ele saiba **quando** e **por que** acionar o novo workflow. Sem essa orientação, o orquestrador pode nunca selecioná-lo.

> **Resumo da arquitetura:** Usuário → Orquestrador (roteador) → `AgentTool` (workflow ou agente pontual) → Roles especialistas.

### 4. Expor um novo app ADK (runner)

Se necessário expor outro app além do orquestrador, crie `runners/<nome>/agent.py` re-exportando o `root_agent`:

```python
from agents.roles.<origem>.agent import <variavel> as root_agent  # noqa: F401
```

O ADK descobre automaticamente subpastas de `runners/` que contenham `agent.py` com `root_agent`.

## Regras Gerais

- **Nomenclatura de Branches**: Siga o padrão `tipo/<equipe>/<issue>-breve-descricao` (ex: `feature/code/42-adicionar-login`). Veja a tabela de prefixos de equipe abaixo.
- **Branches Protegidas**: As branches `main` e `develop` são protegidas. O código deve ser integrado a elas **exclusivamente via Pull Request (PR)**. Nunca realize commits diretos.
- **Sincronização**: Antes de finalizar sua tarefa, sincronize sua branch com as mudanças mais recentes da branch de destino (ex: `git pull origin develop`).

### Prefixos de Equipe

Use o prefixo da sua sub-equipe no nome da branch para facilitar a rastreabilidade:

| Sub-equipe   | Prefixo   | Exemplo                              |
| ------------ | --------- | ------------------------------------ |
| Requisitos   | `req`     | `feature/req/206-politica-branching` |
| Design       | `des`     | `feature/des/210-arquitetura-api` |
| Codificação  | `cod`     | `feature/cod/42-adicionar-login`    |
| Testes       | `tst`     | `feature/tst/99-cobertura-auth`     |

### Conventional Commits

Este projeto adota o padrão [Conventional Commits](https://www.conventionalcommits.org/). Toda mensagem de commit deve seguir o formato:

```text
<tipo>(<escopo>): <descrição curta> #<issue>
```

**Tipos permitidos:**

| Tipo       | Quando usar                                  |
| ---------- | -------------------------------------------- |
| `feat`     | Nova funcionalidade                          |
| `fix`      | Correção de bug                              |
| `docs`     | Alteração exclusiva em documentação          |
| `refactor` | Refatoração sem mudança de comportamento     |
| `test`     | Criação ou ajuste de testes                  |
| `chore`    | Tarefas de manutenção (CI, deps, configs)    |
| `ci`       | Alteração em pipelines de CI/CD              |
| `style`    | Formatação (sem mudança de lógica)           |
| `perf`     | Melhoria de desempenho                       |

**Escopos sugeridos** (alinhados às sub-equipes):

`req` · `design` · `code` · `test` · `orchestrator` · `pipeline`

**Exemplos:**

```text
feat(code): adiciona validação de login #42
fix(test): corrige flaky test de auth #99
docs(req): atualiza requisitos do módulo X #101
refactor(orchestrator): simplifica roteamento de agentes #150
ci(pipeline): adiciona lint de commits no workflow #206
```

> **Agentes ADK** também devem seguir este padrão ao executar `git commit`. As instruções estão embutidas nos prompts dos agentes (veja `adk/agents/roles/coder/prompt.py`).

### Proteção de Branches (Branch Protection Rules)

As seguintes regras de proteção são recomendadas no GitHub:

| Regra                                     | `main`       | `develop`    |
| ----------------------------------------- | ------------ | ------------ |
| Requer PR para merge                      | Sim          | Sim          |
| Aprovações mínimas                        | 1            | 1            |
| Bloquear force push                       | Sim          | Sim          |
