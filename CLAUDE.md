# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository scope

This is the **AI4ES / PDC – IA Generativa Aplicada à Engenharia de Software** repository (CEIA/UFG). It is a mixed research + code monorepo. Most of the tree is **documentation** (research artifacts, RSL, benchmarks, comparative analyses) under `docs/` organized by squad and by SWEBOK "Time" (Time 1 = Requisitos, Time 2 = Design, Time 3 = Testes, Time 4 = Codificação). Executable code lives in `adk/`.

Documentation, commits, PRs, code comments, and prompts in this project are written in **Portuguese (pt-BR)**. Preserve that language when editing existing artifacts; do not auto-translate.

## The `adk/` application

`adk/` is a [Google ADK](https://google.github.io/adk-docs/) (Agent Development Kit) FastAPI app that hosts the multi-agent system produced by the four SWEBOK Times. Each Time owns one or more agents; they're composed into workflows that span the SDLC.

### Commands (run from `adk/`)

```bash
# Install deps (creates .venv at the adk/ level, not repo root)
uv sync

# Activate (Linux / Windows)
source .venv/bin/activate
# or: .venv\Scripts\activate

# Dev server — entrypoint is app.main:app (NOT main:app)
uvicorn app.main:app --reload --port 8081
```

Dev UI: `http://127.0.0.1:8081/dev-ui/?app=<agent_name>` — see "Available agents" below.

Docker alternative:

```bash
# from adk/
docker compose up                                  # volume-mounted, slower starts
docker compose -f docker-compose.build.yml up --build  # baked image, faster restarts
```

### Tests

Pytest config lives in `adk/pyproject.toml` (testpaths=tests, asyncio_mode=auto, coverage source=agents):

```bash
# from adk/
pytest                          # full suite
pytest tests/unit               # unit only
pytest tests/unit/test_filesystem_tools.py::TestCriarArquivoSucesso  # one class
```

The QA agent ships its own local-test fixtures in `adk/src/agents/qa_agent/testesLocal/` — those are *inputs* the agent processes, not pytest targets.

### LLM provider

Agents use `github_copilot/*` via [LiteLLM](https://docs.litellm.ai/docs/providers/github_copilot). The default model is `github_copilot/gpt-4`; override per-process with `ADK_LLM_MODEL` in `.env`.

First run triggers OAuth device flow in the uvicorn terminal — open `https://github.com/login/device`, paste the code, authorize once. Tokens persist in `~/.config/litellm/github_copilot/` (or in the `copilot-tokens` Docker volume).

There is no `GOOGLE_API_KEY` requirement on this branch despite ADK's name — the Google ADK framework is just the agent runtime; the actual model calls go through LiteLLM → Copilot.

## Agent architecture

`adk/app/main.py` is a thin entrypoint:

```python
app = get_fast_api_app(
    agents_dir=os.environ.get("ADK_AGENTS_DIR", "src/agents"),
    web=True, allow_origins=["*"],
)
```

**ADK auto-discovers every subdirectory of `adk/src/agents/` as a runnable agent**, keyed by directory name. To add an agent, create `adk/src/agents/<name>/` — no registration in `main.py` needed. The override env var `ADK_AGENTS_DIR` exists for legacy reasons; on this branch the default `src/agents` is the source of truth.

### Per-agent layout

Minimum required:

```
adk/src/agents/<agent_name>/
├── __init__.py       # MUST expose `root_agent`
└── agent.py          # defines the agent (LlmAgent / SequentialAgent / ParallelAgent)
```

`__init__.py` is one of these two one-liners:

```python
from .agent import agent as root_agent       # when agent.py defines `agent = LlmAgent(...)`
from .agent import root_agent                # when agent.py defines `root_agent = ...`
```

`__all__ = ["root_agent"]` follows. **If `root_agent` is not exposed, ADK silently skips the agent** — debug by hitting `GET /list-apps` and verifying the name appears.

Optional files (vary by agent, no enforced convention):

- `prompt.py` — `description` and `instruction` strings (the dominant pattern across Times 1/2/4)
- `qa_prompt.py` or any other name — Time 3's QA agent does it differently; don't unify gratuitously
- `schemas.py` — Pydantic output schemas (used with `output_schema=` on LlmAgent)
- `subagents/` — local sub-agents specific to this agent (qa_agent has this)
- `tools/` — local tools specific to this agent (qa_agent has this); **shared tools live in `adk/shared/tools/`, not duplicated per agent**
- `README.md` — agent-level docs, often written by the squad that built it

### Cross-agent imports

Agents compose each other via absolute imports rooted at `adk/`:

```python
from src.agents.coder.agent import agent as coder_specialist
from src.agents.reviewer.agent import agent as reviewer_specialist
```

This works because `adk/pyproject.toml` sets `pythonpath = ["."]` — when uvicorn runs from `adk/`, both `src.agents.X` and `shared.tools` resolve. Do **not** use `from agents.roles.X` — that path no longer exists (the consolidation moved roles into `src/agents/`).

### Workflows vs. roles

Two composition patterns coexist:

- **`SequentialAgent` with `sub_agents=[...]`** — strict pipeline; each step's output feeds the next. Used by `workflow_coding`, `workflow_coding_review`. **Caveat**: an LlmAgent can have only one parent, so a `SequentialAgent` cannot embed an agent that's already a sub-agent of another `SequentialAgent`. Either instantiate fresh `LlmAgent`s with the same prompt (see `workflow_coding_review`) or use `AgentTool` instead.
- **`LlmAgent` orchestrator with `tools=[AgentTool(agent=X), ...]`** — flexible delegation; the orchestrator decides when to call which agent. Used by `workflow_design_pipeline`, `workflow_requirements`, `workflow_qa`, and the top-level `orchestrator`. **`AgentTool` does NOT create a parent relationship**, so the wrapped agent can also be a top-level discoverable agent — this is why all 14 roles AND all 5 workflows coexist in `src/agents/`.

### Shared tools

`adk/shared/tools/__init__.py` re-exports every tool. Import from there, not from sub-modules:

```python
from shared.tools import (
    tool_criar_arquivo, tool_salvar_relatorio, tool_ler_arquivo, tool_substituir_trecho,
    tool_salvar_artefato_requisito,
    tool_git_add, tool_git_commit, tool_git_checkout, tool_ler_diff,
    run_slicer, ler_chunk, extract_text,
    gerar_doubt_artifact, registrar_duvida, listar_duvidas_pendentes,
    run_search, check_glossary, add_to_glossary,
    tool_ask_clarification_adk,
)
```

Design-specific tools (Time 2) live alongside in `adk/shared/tools/design_*` (`design_date.py`, `design_filesystem.py`, `design_logger.py`, `design_validate/`) — imported directly, not via the `__init__.py` aggregator.

When adding a new shared tool: add the implementation file in `adk/shared/tools/`, then re-export it in `adk/shared/tools/__init__.py` and add to `__all__`. **Tools that any other agent might reasonably reuse belong here, not in a per-agent `tools/` folder.**

### Available agents (19 total)

**14 individual roles**

- Time 1 (Requisitos): `requirements` (with internal `glossario_agent`)
- Time 2 (Design): `design_architect`, `design_orchestrator`, `io_agent`, `markdown_specialist`, `mermaid_specialist`, `validator`
- Time 3 (Testes): `qa_agent` (with subagents `action_planner`, `code_fix_agent`, `receive_requirements`)
- Time 4 (Codificação): `architect`, `coder`, `finalizer`, `orchestrator`, `reviewer`, `test_planner`

**5 workflows** (compose roles into pipelines)

- `workflow_coding` — SequentialAgent: requirements → architect → test_planner → coder → reviewer → qa → finalizer (full SDLC)
- `workflow_coding_review` — SequentialAgent: requirements → coder → reviewer (lean review pipeline)
- `workflow_design_pipeline` — LlmAgent orchestrator: design_architect → mermaid_specialist → markdown_specialist → validator → io_agent
- `workflow_requirements` — LlmAgent orchestrator wrapping `requirements` agent
- `workflow_qa` — LlmAgent orchestrator: action_planner → receber_requisitos → pytest → code_fix (with 2-cycle autocorrect limit)

## Branch + PR conventions

Defined in `CONTRIBUTING.md`:

- **Branches**: `squadX/<issue_number>-<short-title>` (Squad workflow) or `feature/<context>-<title>` (newer). The `consolidacao/agentes-times-1-2-3-4` branch this work lives on is a one-off integration branch outside the convention.
- **Commit prefixes** (enforced by review): `add:`, `update:`, `fix:`, `refactor:`, `docs:`, `test:` followed by a short Portuguese description. Match this format when authoring commits.
- **PR flow**: feature branch → `develop` (or release branch) → `main`. **Never** PR directly to `main` outside a release closure. Squad PRs need squad-lead review; `develop → main` needs Gestão approval.
- **`coding_review` workflow caveat**: this pipeline was patched during the four-Time consolidation because Time 1 deleted `tools_requirements.py` (its tools `tool_ler_prd_arquivo_adk` and `tool_gerar_doubt_artifact_adk` were replaced with `tool_ler_arquivo` and `gerar_doubt_artifact` from `shared.tools`). It works but the substitutions are functionally close, not semantically identical — flag this if a Time 1/4 dev asks why their workflow behaves differently.

## Gotchas e lições do orchestrator E2E

Esta seção consolida aprendizados de rodar o `orchestrator` em ponta-a-ponta via REST. Aplica-se a quem for tocar nos workflows, em `shared/tools/` ou na infra de workspace.

### Schemas de tool incompatíveis com Gemini API

Tools cuja assinatura usa `str | None` (PEP 604) ou `str | dict` (Union) geram `anyOf` no FunctionDeclaration que o **Gemini API rejeita com `400 INVALID_ARGUMENT` mencionando `additional_properties`**. Use `Optional[str]` (do `typing`) — o ADK serializa como `{nullable: true, type: STRING}` que o Gemini aceita. Para `str | dict`, escolha um tipo e normalize internamente. Vale o mesmo para todo parâmetro de função registrada como `FunctionTool`.

Históricos corrigidos: `shared/tools/filesystem.py`, `shared/tools/git.py`, `src/agents/qa_agent/tools/pytest_runner.py:executar_pytest_tool`. Procure `str | None` ou `Union[` antes de registrar uma tool nova.

### Workspace isolation no `workflow_coding_review`

`workflow_coding_review` instancia `cr_coder_agent` / `cr_requirements_agent` / `cr_review_agent` direto via `LlmAgent` (não via `create_se_agent`). Sem binding ao workspace, o coder **escreve diretamente no repo** — sobrescreveu `adk/app/main.py` e criou branches git aleatórias na primeira execução. O fix em `src/agents/workflow_coding_review/agent.py` usa `_bind_tool_to_workspace` (de `shared.agent_factory`) explicitamente:

```python
from shared.agent_factory import _bind_tool_to_workspace
from shared.workspace import get_agent_workspace, get_workspace_root, init_workspace

_WORKSPACE_ROOT = str(init_workspace())
_CODER_WS = str(get_agent_workspace("coder"))

# Tools bound ao subdiretório do agente:
_bind(FunctionTool(tool_criar_arquivo), _CODER_WS)
```

Removi também `tool_git_*` do `cr_coder_agent` e substituí o `instruction` herdado de `coder/prompt.py` (que dava ordens de git) por uma versão enxuta — o LLM senão alucina `git_checkout` mesmo sem a tool registrada.

### `init_workspace()` não é chamada automaticamente em produção

Só é invocada em testes. Sem chamada explícita no import time de algum workflow, `workspace_output/` nunca aparece. O `workflow_coding_review` agora faz isso, mas é frágil: a primeira invocação de `coding_review_pipeline` apaga e recria o workspace, descartando qualquer output de pipelines anteriores na MESMA sessão.

Considere mover `init_workspace()` para um lifespan hook do FastAPI (`app/main.py`) com flag `--keep` para preservar entre runs.

### Tools de persistência que IGNORAM `base_dir` (precisam refatorar)

Algumas tools hardcodam paths e furam o isolamento do workspace:

- `tool_salvar_artefato_requisito(tipo, id_req, conteudo_md)` em `shared/tools/filesystem.py:266` → escreve em `docs/Time_1_Requisitos/{HUs,RFs,RNFs,...}` relativo ao CWD do servidor, **não** em `workspace_output/requirements/`.
- `gerar_doubt_artifact(...)` em `shared/tools/doubt_generator_analista.py:17` → `caminho_base` default = `'docs/Time_1_Requisitos/setup-ADK/AgenteAnalista/'`. O LLM precisa passar `caminho_base` explicitamente para mudar, mas raramente o faz.

**Sintoma observável**: ao rodar o `orchestrator` em ponta-a-ponta, `workspace_output/requirements/`, `workspace_output/tests/`, `workspace_output/design/` ficam vazios — só `coder/` e `review/` populam (esses dois passaram por `_bind_tool_to_workspace`).

**Fix recomendado** (não aplicado ainda): adicionar `base_dir: Optional[str] = None` a ambas as tools e incluí-las em `_FILESYSTEM_TOOL_NAMES` em `shared/agent_factory.py:36-41` — assim qualquer agente criado via `create_se_agent(agent_subdir="...")` ou via bind manual no `workflow_coding_review` herda o workspace certo. Ao mesmo tempo, padronizar a estrutura de subpastas no `AGENT_DIRS` (`shared/workspace.py:29`) — hoje a tool grava `HUs/`, `RFs/`, `RNFs/`, `RNs/` sob `Time_1_Requisitos`, mas o workspace só tem `requirements/` e `requirements/glossario/`.

### Caveat duplicado do `coding_review` (já existia)

Mantenho a nota original abaixo, ainda válida: o pipeline foi patcheado na consolidação e as tools de Time 1 deletadas (`tool_ler_prd_arquivo_adk`, `tool_gerar_doubt_artifact_adk`) foram substituídas por equivalentes próximos mas não idênticos semanticamente.

### Bug do `cr_requirements_agent`: prompt referencia tool não-registrada

O `cr_requirements_agent` (em `workflow_coding_review`) usava o prompt original de `requirements/prompt.py` que lista `tool_salvar_artefato_requisito`, `run_slicer` e `ler_chunk` como ferramentas — mas só registrava 2 tools. O LLM alucinava a chamada e o ADK quebrava com `ValueError: Tool 'X' not found`. Agora todas estão registradas, mas isso é sintoma do problema mais geral: **se você mudar `tools=[...]` de um LlmAgent, audite o `instruction` por nomes de função mencionados**.

### Verificação rápida de schemas de tool antes de rodar

```bash
cd adk && .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from src.agents.<workflow>.agent import agent
def walk(a, d=0):
    if hasattr(a, 'tools'):
        for i, t in enumerate(a.tools):
            j = t._get_declaration().model_dump_json(exclude_none=True, by_alias=True)
            tag = 'PROBLEM' if 'any_of' in j or 'additional' in j.lower() else 'ok'
            print('  '*d, f'[{i}]', t._get_declaration().name, tag)
    if hasattr(a, 'sub_agents'):
        for sa in a.sub_agents: walk(sa, d+1)
walk(agent)
"
```

Use isso ao introduzir uma tool nova com Pydantic models ou parâmetros opcionais.

### Para subir o app gerado pelo coder

`adk/workspace_output/coder/` é descartado a cada nova execução do `workflow_coding_review`. **Copie para fora** antes de testar:

```bash
cp -r adk/workspace_output/coder /tmp/app-snapshot
cd /tmp/app-snapshot
uv venv --python 3.12
uv pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --port 8090
```

`uv pip install -r requirements.txt` dentro de `adk/workspace_output/coder/` **pode pegar o `.venv` do `adk/` pai** se houver. Use `VIRTUAL_ENV=$PWD/.venv uv pip install ...` ou `uv run --with-requirements requirements.txt uvicorn app.main:app` para forçar o ambiente local.

## Convenção: prompts não citam tools

Prompts (`adk/src/agents/*/prompt.py`) descrevem papel, workflow e protocolos de decisão em **verbos de capacidade** — nunca citam identificadores literais de tool (`tool_*`, `run_*`, `check_*`, etc.). A informação acionável sobre cada tool (propósito, quando usar, Args, Returns) vive na docstring da função, que o ADK entrega ao LLM como `FunctionDeclaration.description`.

Vocabulário canônico de capacidades:
- "ler conteúdo do arquivo", "escrever/criar arquivo", "editar trecho do arquivo"
- "fragmentar em partes processáveis", "ler parte específica do documento fatiado"
- "preparar a mudança para versionamento", "registrar a versão", "consultar o diff acumulado"
- "registrar dúvida / gerar artefato de dúvida"
- "persistir o artefato no repositório de requisitos", "salvar relatório de revisão"
- "registrar artefato em staging", "promover artefato para versão final"
- "delegar ao especialista em X" (para sub-agentes; nunca o slug)

Verificação:

```bash
cd adk && rg -nP '\b(tool_[a-z_]+|run_slicer|ler_chunk|extract_text|run_search)\b' src/agents/*/prompt.py
```

Resultado esperado: zero matches.

Ao adicionar uma tool nova: dê a ela uma docstring GOOD (propósito + Quando usar + Args + Returns ≥ 80 chars). O prompt do agente que vai usar a tool não precisa de update — basta registrar a tool em `tools=[FunctionTool(...)]`.

Sub-agentes (`AgentTool` wrapping): a `description=` do `LlmAgent(...)` é o que o orquestrador pai vê para decidir delegação. Mantenha-a semântica (descrevendo o serviço prestado), nunca cite o slug do agente.

Refs:
- Spec: `docs/superpowers/specs/2026-05-17-prompt-tool-decoupling-design.md`
- Plano: `docs/superpowers/plans/2026-05-17-prompt-tool-decoupling.md`

## `docs/` layout

Research output, not code. Two parallel groupings coexist:

- `docs/squad1/`, `docs/squad2/` — by squad (Squad 1 = systematic review & tool comparison; Squad 2 = environment & experimentation).
- `docs/Time_1_Requisitos/` through `docs/Time_4_Codificacao/` — by SWEBOK phase. Each agent in `adk/src/agents/` has a corresponding Time folder here with prompts, templates, and research notes.

When adding a research artifact, place it under the matching squad/Time folder and follow the templates already there. Don't restructure these directories — the squads/Times own them.
