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

## `docs/` layout

Research output, not code. Two parallel groupings coexist:

- `docs/squad1/`, `docs/squad2/` — by squad (Squad 1 = systematic review & tool comparison; Squad 2 = environment & experimentation).
- `docs/Time_1_Requisitos/` through `docs/Time_4_Codificacao/` — by SWEBOK phase. Each agent in `adk/src/agents/` has a corresponding Time folder here with prompts, templates, and research notes.

When adding a research artifact, place it under the matching squad/Time folder and follow the templates already there. Don't restructure these directories — the squads/Times own them.
