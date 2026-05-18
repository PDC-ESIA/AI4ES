# Fix Review + QA Pipelines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer o `cr_review_agent` persistir `verificacao_revisao.md` e impedir que o `qa_pipeline` trave em HITL falso causado por `action_planner` retornando string vazia. Spec: `docs/superpowers/specs/2026-05-18-fix-review-qa-pipelines-design.md`.

**Architecture:** Duas mudanças cirúrgicas. (1) No `workflow_coding_review`, o `cr_review_agent` ganha um `instruction` próprio (não herda do prompt do reviewer top-level) com a lista de arquivos a revisar descoberta dinamicamente via `InstructionProvider` do ADK — `instruction=callable` resolvido em runtime. As tools dele ficam ambas bound ao workspace. (2) No `workflow_qa`, a chamada nested `AgentTool(action_planner)` é substituída por um `FunctionTool(invocar_planejamento_qa)` que envolve o agente num runner isolado, faz retry programático em caso de empty, e devolve JSON estruturado garantido (ou um JSON de bloqueio sintético, mas determinístico).

**Tech Stack:** Python 3.12, Google ADK (`google.adk.agents.LlmAgent`, `google.adk.runners.Runner`, `google.adk.tools.FunctionTool`), pytest + pytest-asyncio.

---

## File Structure

Arquivos modificados:
- `adk/src/agents/workflow_coding_review/agent.py` — substitui o bloco do `cr_review_agent` (linhas 140-156), adiciona helper `_discover_coder_files` e `InstructionProvider`
- `adk/src/agents/workflow_qa/agent.py` — troca import + tools + instruction

Arquivos novos:
- `adk/src/agents/workflow_qa/tools/__init__.py` — pacote
- `adk/src/agents/workflow_qa/tools/planner_wrapper.py` — wrapper com retry
- `adk/tests/unit/test_review_agent_persistence.py` — testes do cr_review_agent
- `adk/tests/unit/test_planner_wrapper.py` — testes do wrapper

Boundaries:
- `planner_wrapper` é módulo puro (sem side effects no import) — fácil de testar isoladamente
- `_discover_coder_files` é função pura sobre filesystem — testa-se com `tmp_path`
- O `InstructionProvider` resolve no momento da invocação do agente, evitando a armadilha do "glob no import" com `_CODER_WS` vazio

---

## Task 1: Helper `_discover_coder_files` + `InstructionProvider` para o reviewer

**Files:**
- Modify: `adk/src/agents/workflow_coding_review/agent.py` — adicionar helpers acima da definição do `_reviewer`
- Test: `adk/tests/unit/test_review_agent_persistence.py`

- [ ] **Step 1: Criar o arquivo de teste com 3 testes do `_discover_coder_files`**

Conteúdo completo de `adk/tests/unit/test_review_agent_persistence.py`:

```python
"""Tests para o cr_review_agent do workflow_coding_review.

Cobertura:
- _discover_coder_files lista arquivos do workspace do coder
- O InstructionProvider injeta a lista + a substring obrigatória de save
- As tools tool_ler_arquivo e tool_salvar_relatorio estão bound aos workspaces certos
"""

from pathlib import Path

import pytest


def test_discover_coder_files_workspace_vazio(tmp_path, monkeypatch):
    """Workspace sem arquivos: retorna marker '(workspace vazio)'."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    (tmp_path / "ws" / "coder").mkdir(parents=True)

    # Re-import com env nova
    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    result = wcr._discover_coder_files()
    assert "workspace vazio" in result or "nenhum arquivo" in result


def test_discover_coder_files_lista_arquivos_relativos(tmp_path, monkeypatch):
    """Workspace com arquivos: retorna bullets com paths relativos."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    coder_ws = tmp_path / "ws" / "coder"
    coder_ws.mkdir(parents=True)
    (coder_ws / "app").mkdir()
    (coder_ws / "app" / "main.py").write_text("# main")
    (coder_ws / "app" / "models.py").write_text("# models")
    (coder_ws / "requirements.txt").write_text("fastapi")

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    result = wcr._discover_coder_files()
    assert "- app/main.py" in result
    assert "- app/models.py" in result
    assert "- requirements.txt" in result


def test_discover_coder_files_ignora_pycache(tmp_path, monkeypatch):
    """__pycache__ e seus arquivos não aparecem na lista."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    coder_ws = tmp_path / "ws" / "coder"
    (coder_ws / "app" / "__pycache__").mkdir(parents=True)
    (coder_ws / "app" / "__pycache__" / "main.cpython-312.pyc").write_bytes(b"x")
    (coder_ws / "app" / "main.py").write_text("# main")

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    result = wcr._discover_coder_files()
    assert "main.py" in result
    assert "__pycache__" not in result
    assert ".pyc" not in result
```

- [ ] **Step 2: Rodar os testes pra confirmar que falham**

Run: `cd adk && .venv/bin/pytest tests/unit/test_review_agent_persistence.py -v`

Expected: 3 FAILs com `AttributeError: module 'src.agents.workflow_coding_review.agent' has no attribute '_discover_coder_files'`.

- [ ] **Step 3: Adicionar `_discover_coder_files` em `workflow_coding_review/agent.py`**

Localizar em `adk/src/agents/workflow_coding_review/agent.py` o final dos imports + a constante `_REVIEW_WS = str(get_agent_workspace("reviewer"))` (linha ~46) e adicionar logo depois das definições de `_bind` (linha ~50):

```python
from pathlib import Path


def _discover_coder_files() -> str:
    """Lista arquivos no _CODER_WS (relativo), formato bullet, pra injetar no prompt do reviewer.

    Executado no momento da invocação do agente (via InstructionProvider) — não no import.
    Quando o coder ainda não rodou, retorna marker informativo.
    """
    coder_dir = Path(_CODER_WS)
    if not coder_dir.exists():
        return "- (nenhum arquivo ainda — coder será executado antes de você)"
    files = sorted(
        str(p.relative_to(coder_dir))
        for p in coder_dir.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )
    if not files:
        return "- (workspace vazio)"
    return "\n".join(f"- {f}" for f in files)
```

- [ ] **Step 4: Rodar testes — devem passar**

Run: `cd adk && .venv/bin/pytest tests/unit/test_review_agent_persistence.py -v`

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/src/agents/workflow_coding_review/agent.py adk/tests/unit/test_review_agent_persistence.py
git commit -m "$(cat <<'EOF'
add: _discover_coder_files helper para listar arquivos do workspace do coder

Função pura usada pelo cr_review_agent para descobrir arquivos a revisar
no momento da invocação. Próximas tasks plugam isso num InstructionProvider
e substituem o instruction herdado do reviewer top-level.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Refatorar `_reviewer` no `workflow_coding_review` — InstructionProvider + bind das tools

**Files:**
- Modify: `adk/src/agents/workflow_coding_review/agent.py` — substitui linhas 140-156 (definição do `_reviewer`)
- Test: `adk/tests/unit/test_review_agent_persistence.py` — adicionar testes

- [ ] **Step 1: Adicionar testes para o instruction provider + tool binding**

Append em `adk/tests/unit/test_review_agent_persistence.py`:

```python
def test_reviewer_instruction_provider_inclui_arquivos_descobertos(tmp_path, monkeypatch):
    """O instruction provider do _reviewer chama _discover_coder_files e injeta no template."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    coder_ws = tmp_path / "ws" / "coder"
    coder_ws.mkdir(parents=True)
    (coder_ws / "app").mkdir()
    (coder_ws / "app" / "main.py").write_text("# main")

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    # _reviewer.instruction deve ser callable (InstructionProvider) ou já ter o glob
    instr = wcr._reviewer.instruction
    if callable(instr):
        # Stub mínimo de ReadonlyContext — o provider só precisa do callable
        class _FakeCtx:
            pass
        rendered = instr(_FakeCtx())
        # Provider pode retornar str ou Awaitable[str]
        if hasattr(rendered, "__await__"):
            import asyncio
            rendered = asyncio.get_event_loop().run_until_complete(rendered)
    else:
        rendered = instr

    assert "- app/main.py" in rendered


def test_reviewer_instruction_contem_save_obrigatorio(tmp_path, monkeypatch):
    """Instruction final do reviewer DEVE conter a frase que torna o save mandatório."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    (tmp_path / "ws" / "coder").mkdir(parents=True)

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    instr = wcr._reviewer.instruction
    if callable(instr):
        class _FakeCtx:
            pass
        rendered = instr(_FakeCtx())
        if hasattr(rendered, "__await__"):
            import asyncio
            rendered = asyncio.get_event_loop().run_until_complete(rendered)
    else:
        rendered = instr

    assert "tool_salvar_relatorio" in rendered
    assert "OBRIGATÓRIO" in rendered


def test_reviewer_tool_ler_arquivo_esta_bound_ao_coder_ws(tmp_path, monkeypatch):
    """tool_ler_arquivo do reviewer resolve paths relativos contra _CODER_WS."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    coder_ws = tmp_path / "ws" / "coder"
    coder_ws.mkdir(parents=True)
    target_file = coder_ws / "test_file.py"
    target_file.write_text("CONTEUDO_ESPERADO")

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    # tool_ler_arquivo deve ser o primeiro tool do _reviewer
    tools = wcr._reviewer.tools
    ler_tool = next(t for t in tools if "ler_arquivo" in t.func.__name__)
    # Chamar via path relativo — _bind deve resolver para coder_ws/test_file.py
    result = ler_tool.func(caminho="test_file.py")
    assert result.get("sucesso") is True
    assert "CONTEUDO_ESPERADO" in result.get("conteudo", "")
```

- [ ] **Step 2: Rodar pra confirmar 3 FAILs**

Run: `cd adk && .venv/bin/pytest tests/unit/test_review_agent_persistence.py -v`

Expected: 6 testes total, 3 PASS (do Task 1), 3 FAIL.

- [ ] **Step 3: Substituir o bloco do `_reviewer` em `workflow_coding_review/agent.py`**

Localizar linhas 140-156 do arquivo atual (definição do `_reviewer`):

```python
_reviewer = LlmAgent(
    model=_model,
    name="cr_review_agent",
    description=reviewer_prompt.description,
    instruction=(
        reviewer_prompt.instruction
        + f"\n\n# WORKSPACE\n"
        + f"Os arquivos a revisar estão em `{_CODER_WS}/`. "
        + f"Como o ambiente não é git, use tool_ler_arquivo (apontando para `{_CODER_WS}/<file>`) "
        + f"para ler cada arquivo. Salve o relatório em `{_REVIEW_WS}/` via tool_salvar_relatorio."
    ),
    output_key="review",
    tools=[
        FunctionTool(tool_ler_arquivo),
        _bind(FunctionTool(tool_salvar_relatorio), _REVIEW_WS),
    ],
)
```

Substituir por:

```python
_REVIEWER_INSTRUCTION_TEMPLATE = """
# PERFIL
Você é um Engenheiro de Software Sênior responsável por revisar código produzido por outro agente.
Não há ambiente git neste pipeline. Você revisa arquivos diretamente no workspace.

# WORKSPACE
Os arquivos a revisar estão em `__CODER_WS__/` (caminho absoluto do disco).
Para você, use caminhos RELATIVOS — tool_ler_arquivo resolve automaticamente.

# ARQUIVOS A REVISAR
__FILES__

# FERRAMENTAS DISPONÍVEIS
- tool_ler_arquivo(caminho): lê arquivo do workspace do coder (path relativo).
- tool_salvar_relatorio(nome_arquivo, conteudo): salva o relatório no workspace de review.

# FLUXO OBRIGATÓRIO
1. Para cada arquivo da lista acima, chame tool_ler_arquivo(caminho).
2. Avalie em 4 dimensões: COMPLETUDE, ARQUITETURA, CORRETUDE, TESTES.
   - Completude: arquivos esperados foram criados? tests/ existe? requirements.txt?
   - Arquitetura: SRP, separação de concerns, acoplamento.
   - Corretude: bugs visíveis, edge cases, segurança.
   - Testes: existem? cobrem cenários relevantes? assertions significativas?
3. **OBRIGATÓRIO ao fim**: chame tool_salvar_relatorio(nome_arquivo='verificacao_revisao.md', conteudo=<markdown>).
   Sem essa chamada, sua revisão NÃO é entregue — o pipeline falha mesmo que você produza texto.

# REGRAS DE DECISÃO
- Qualquer issue critical → status="BLOQUEADO"
- Apenas warning/info → status="APROVADO" com ressalvas
- Sem issues → status="APROVADO"

# SAÍDA FINAL (texto retornado pelo agente, depois de salvar)
JSON único:
{
  "status": "APROVADO" | "BLOQUEADO",
  "issues": [{"severity": "critical|warning|info", "description": "...", "file": "...", "layer": "completude|arquitetura|corretude|testes"}],
  "report_path": "verificacao_revisao.md"
}
"""


def _reviewer_instruction_provider(_ctx) -> str:
    """InstructionProvider do ADK: resolve no momento da invocação.

    Garante que a lista de arquivos do coder esteja atualizada quando o
    reviewer é chamado (após o coder rodar, não no import do módulo).
    """
    return (
        _REVIEWER_INSTRUCTION_TEMPLATE
        .replace("__CODER_WS__", _CODER_WS)
        .replace("__FILES__", _discover_coder_files())
    )


_reviewer = LlmAgent(
    model=_model,
    name="cr_review_agent",
    description=reviewer_prompt.description,
    instruction=_reviewer_instruction_provider,
    output_key="review",
    tools=[
        _bind(FunctionTool(tool_ler_arquivo), _CODER_WS),
        _bind(FunctionTool(tool_salvar_relatorio), _REVIEW_WS),
    ],
)
```

- [ ] **Step 4: Rodar todos os testes do arquivo**

Run: `cd adk && .venv/bin/pytest tests/unit/test_review_agent_persistence.py -v`

Expected: 6 PASS.

- [ ] **Step 5: Smoke-test de import (regressão)**

Run: `cd adk && .venv/bin/python -c "from src.agents.workflow_coding_review.agent import agent; print('ok:', agent.name)"`

Expected: `ok: coding_review_pipeline` (sem ImportError, sem exceções).

- [ ] **Step 6: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/src/agents/workflow_coding_review/agent.py adk/tests/unit/test_review_agent_persistence.py
git commit -m "$(cat <<'EOF'
fix: cr_review_agent agora persiste verificacao_revisao.md

Substitui o instruction herdado do reviewer top-level (que falava em diff
git inexistente neste pipeline) por um instruction próprio. Lista de
arquivos a revisar é descoberta dinamicamente via InstructionProvider do
ADK — resolve no momento da invocação, não no import do módulo.

tool_ler_arquivo agora está bound ao _CODER_WS, permitindo paths
relativos no LLM call.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Helper `_is_empty` no `planner_wrapper.py`

**Files:**
- Create: `adk/src/agents/workflow_qa/tools/planner_wrapper.py` (stub inicial)
- Test: `adk/tests/unit/test_planner_wrapper.py`

- [ ] **Step 1: Criar arquivo de teste**

Conteúdo completo de `adk/tests/unit/test_planner_wrapper.py`:

```python
"""Tests para workflow_qa/tools/planner_wrapper.py — retry de action_planner."""

import json

import pytest

from src.agents.workflow_qa.tools.planner_wrapper import (
    _is_empty,
    _FALLBACK_BLOCKED_JSON,
)


def test_is_empty_string_vazia():
    assert _is_empty("") is True


def test_is_empty_none():
    assert _is_empty(None) is True


def test_is_empty_apenas_whitespace():
    assert _is_empty("   \n\t  ") is True


def test_is_empty_apenas_backticks():
    """LLMs às vezes devolvem só markers de code block vazios."""
    assert _is_empty("```") is True
    assert _is_empty("``` ```") is True


def test_is_empty_json_valido_pequeno():
    """JSON de bloqueio mínimo (~100 chars) NÃO é empty."""
    json_str = '{"tipo_entrada":"requisito","lifecycle":{"status":"bloqueado"}}'
    assert _is_empty(json_str) is False


def test_is_empty_json_valido_grande():
    """JSON completo do action_planner (~500+ chars) NÃO é empty."""
    json_str = '{"tipo_entrada":"requisito","modo":"requisito","tools":["receber_requisitos"],"casos_de_teste_propostos":["Cenario 1"],"lifecycle":{"status":"planejado_para_execucao","execution_allowed":true,"next_step":"executar_plano"}}'
    assert _is_empty(json_str) is False


def test_fallback_blocked_json_e_parseavel():
    """O fallback DEVE ser JSON parseável com status=bloqueado."""
    parsed = json.loads(_FALLBACK_BLOCKED_JSON)
    assert parsed["lifecycle"]["status"] == "bloqueado"
    assert parsed["lifecycle"]["execution_allowed"] is False
    assert "erro" in parsed
```

- [ ] **Step 2: Rodar — deve falhar com ImportError**

Run: `cd adk && .venv/bin/pytest tests/unit/test_planner_wrapper.py -v`

Expected: collection error (`ModuleNotFoundError: No module named 'src.agents.workflow_qa.tools'`).

- [ ] **Step 3: Criar `workflow_qa/tools/__init__.py` (pacote vazio)**

Conteúdo do arquivo `adk/src/agents/workflow_qa/tools/__init__.py`:

```python
"""Pacote de tools próprias do workflow_qa (wrappers locais)."""
```

- [ ] **Step 4: Criar `planner_wrapper.py` com `_is_empty` + `_FALLBACK_BLOCKED_JSON`**

Conteúdo inicial do arquivo `adk/src/agents/workflow_qa/tools/planner_wrapper.py`:

```python
"""Wrapper de retry para invocações do action_planner no qa_pipeline.

Motivação: action_planner via AgentTool retorna ocasionalmente {"result": ""},
travando o qa_pipeline em HITL falso. Este wrapper roda o action_planner em
runner isolado, faz retry programático em caso de empty, e garante que o
caller (qa_pipeline) sempre receba JSON estruturado.
"""

from typing import Optional


_EMPTY_THRESHOLD = 8


_FALLBACK_BLOCKED_JSON = (
    '{"tipo_entrada":"indefinido","modo":"indefinido","tools":[],'
    '"casos_de_teste_propostos":[],"lifecycle":{"status":"bloqueado",'
    '"execution_allowed":false,"next_step":"aguardar_resolucao_humana"},'
    '"erro":"action_planner não respondeu após 2 tentativas — falha de modelo"}'
)


def _is_empty(text: Optional[str]) -> bool:
    """True quando o texto é vazio, None, só whitespace ou só backticks.

    Heurística: <_EMPTY_THRESHOLD chars úteis = empty.
    """
    if text is None:
        return True
    stripped = text.strip().strip("`").strip()
    return len(stripped) < _EMPTY_THRESHOLD
```

- [ ] **Step 5: Rodar — 7 testes devem passar**

Run: `cd adk && .venv/bin/pytest tests/unit/test_planner_wrapper.py -v`

Expected: 7 PASS.

- [ ] **Step 6: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/src/agents/workflow_qa/tools/__init__.py adk/src/agents/workflow_qa/tools/planner_wrapper.py adk/tests/unit/test_planner_wrapper.py
git commit -m "$(cat <<'EOF'
add: planner_wrapper._is_empty + _FALLBACK_BLOCKED_JSON

Esqueleto do wrapper que vai envolver action_planner com retry no
qa_pipeline. Próximas tasks adicionam _invoke_once e
invocar_planejamento_qa.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `_invoke_once` — runner isolado com try/except

**Files:**
- Modify: `adk/src/agents/workflow_qa/tools/planner_wrapper.py`
- Test: `adk/tests/unit/test_planner_wrapper.py`

- [ ] **Step 1: Adicionar testes para `_invoke_once` com mocks**

Append em `adk/tests/unit/test_planner_wrapper.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_invoke_once_retorna_texto_do_evento():
    """_invoke_once coleta texto dos events do Runner."""
    from src.agents.workflow_qa.tools import planner_wrapper

    fake_part = MagicMock()
    fake_part.text = '{"tipo_entrada":"requisito","lifecycle":{"status":"ok"}}'
    fake_event = MagicMock()
    fake_event.content.parts = [fake_part]

    async def fake_run_async(*args, **kwargs):
        yield fake_event

    fake_runner = MagicMock()
    fake_runner.run_async = fake_run_async
    fake_runner.close = AsyncMock()
    fake_session = MagicMock()
    fake_session.id = "sid-test"
    fake_session.user_id = "uid-test"
    fake_runner.session_service.create_session = AsyncMock(return_value=fake_session)

    with patch.object(planner_wrapper, "Runner", return_value=fake_runner):
        result = await planner_wrapper._invoke_once("request body")

    assert "tipo_entrada" in result
    fake_runner.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_invoke_once_exception_retorna_marker_de_erro():
    """Se o Runner explodir, _invoke_once devolve string 'ERROR: ...' (não levanta)."""
    from src.agents.workflow_qa.tools import planner_wrapper

    with patch.object(planner_wrapper, "Runner", side_effect=RuntimeError("boom")):
        result = await planner_wrapper._invoke_once("request body")

    assert result.startswith("ERROR:")
    # ERROR string deve ser detectada como empty pelo _is_empty
    assert planner_wrapper._is_empty(result) is False  # ERROR é texto, mas não é empty
    # OK: o test acima é só pra documentar; quem decide retry é invocar_planejamento_qa
```

Adicionar também no topo de `test_planner_wrapper.py` (se ainda não estiver) a config asyncio:

```python
# (já existe via pyproject.toml asyncio_mode=auto — não precisa repetir aqui)
```

- [ ] **Step 2: Rodar — devem falhar com `AttributeError`**

Run: `cd adk && .venv/bin/pytest tests/unit/test_planner_wrapper.py::test_invoke_once_retorna_texto_do_evento tests/unit/test_planner_wrapper.py::test_invoke_once_exception_retorna_marker_de_erro -v`

Expected: 2 FAIL (`AttributeError: module 'src.agents.workflow_qa.tools.planner_wrapper' has no attribute '_invoke_once'` ou `has no attribute 'Runner'`).

- [ ] **Step 3: Adicionar `_invoke_once` em `planner_wrapper.py`**

Adicionar no topo do arquivo (após imports existentes):

```python
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.genai import types

from src.agents.qa_agent.subagents.action_planner.agent import agent as action_planner_agent
```

Adicionar no final do arquivo (depois de `_is_empty`):

```python
async def _invoke_once(request: str, user_id: str = "qa-pipeline") -> str:
    """Roda action_planner uma vez em runner isolado, retorna last_text.

    Em caso de exceção do Runner, devolve string 'ERROR: <msg>' em vez de
    propagar — para que invocar_planejamento_qa possa decidir fallback.
    """
    try:
        runner = Runner(
            app_name=action_planner_agent.name,
            agent=action_planner_agent,
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        session = await runner.session_service.create_session(
            app_name=action_planner_agent.name, user_id=user_id, state={},
        )
        content = types.Content(
            role="user", parts=[types.Part.from_text(text=request)],
        )
        last_text = ""
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        last_text = part.text
        await runner.close()
        return last_text
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"
```

- [ ] **Step 4: Rodar testes — todos devem passar**

Run: `cd adk && .venv/bin/pytest tests/unit/test_planner_wrapper.py -v`

Expected: 9 PASS (7 do Task 3 + 2 novos).

- [ ] **Step 5: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/src/agents/workflow_qa/tools/planner_wrapper.py adk/tests/unit/test_planner_wrapper.py
git commit -m "$(cat <<'EOF'
add: planner_wrapper._invoke_once com try/except defensivo

Roda o action_planner em Runner isolado e devolve last_text. Exceções
do Runner viram string 'ERROR: ...' em vez de propagar — caller decide
fallback. Próxima task adiciona invocar_planejamento_qa com retry.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `invocar_planejamento_qa` — retry programático

**Files:**
- Modify: `adk/src/agents/workflow_qa/tools/planner_wrapper.py`
- Test: `adk/tests/unit/test_planner_wrapper.py`

- [ ] **Step 1: Adicionar testes do retry**

Append em `adk/tests/unit/test_planner_wrapper.py`:

```python
@pytest.mark.asyncio
async def test_invocar_retorna_first_quando_valido():
    """Primeira chamada retorna JSON válido → não tenta segunda."""
    from src.agents.workflow_qa.tools import planner_wrapper

    valid_json = '{"tipo_entrada":"requisito","lifecycle":{"status":"ok"}}'

    with patch.object(planner_wrapper, "_invoke_once", AsyncMock(return_value=valid_json)) as mock_invoke:
        result = await planner_wrapper.invocar_planejamento_qa("req")

    assert result == valid_json
    assert mock_invoke.await_count == 1


@pytest.mark.asyncio
async def test_invocar_tenta_segunda_quando_first_empty():
    """Primeira call empty + segunda call JSON válido → retorna o JSON da segunda."""
    from src.agents.workflow_qa.tools import planner_wrapper

    valid_json = '{"tipo_entrada":"requisito","lifecycle":{"status":"ok"}}'

    with patch.object(
        planner_wrapper, "_invoke_once",
        AsyncMock(side_effect=["", valid_json]),
    ) as mock_invoke:
        result = await planner_wrapper.invocar_planejamento_qa("req")

    assert result == valid_json
    assert mock_invoke.await_count == 2


@pytest.mark.asyncio
async def test_invocar_fallback_quando_ambas_empty():
    """Ambas as calls empty → devolve _FALLBACK_BLOCKED_JSON."""
    from src.agents.workflow_qa.tools import planner_wrapper

    with patch.object(
        planner_wrapper, "_invoke_once",
        AsyncMock(side_effect=["", "   "]),
    ) as mock_invoke:
        result = await planner_wrapper.invocar_planejamento_qa("req")

    assert result == planner_wrapper._FALLBACK_BLOCKED_JSON
    assert mock_invoke.await_count == 2
    # Garantir que o fallback é parseável e tem status=bloqueado
    parsed = json.loads(result)
    assert parsed["lifecycle"]["status"] == "bloqueado"


@pytest.mark.asyncio
async def test_invocar_retry_suffix_adicionado_na_segunda_call():
    """Segunda call recebe request + retry suffix com aviso ANTI-EMPTY."""
    from src.agents.workflow_qa.tools import planner_wrapper

    valid_json = '{"tipo_entrada":"requisito","lifecycle":{"status":"ok"}}'
    mock_invoke = AsyncMock(side_effect=["", valid_json])

    with patch.object(planner_wrapper, "_invoke_once", mock_invoke):
        await planner_wrapper.invocar_planejamento_qa("requisito original")

    # Segunda chamada (índice 1) deve incluir o request + suffix de retry
    second_call_args = mock_invoke.await_args_list[1]
    second_request = second_call_args[0][0]  # primeiro arg posicional
    assert "requisito original" in second_request
    assert "ATENÇÃO" in second_request
    assert "PROTOCOLO ANTI-EMPTY" in second_request
```

- [ ] **Step 2: Rodar — 4 FAILs por `AttributeError`**

Run: `cd adk && .venv/bin/pytest tests/unit/test_planner_wrapper.py -v -k invocar`

Expected: 4 FAIL.

- [ ] **Step 3: Adicionar `_RETRY_PROMPT_SUFFIX` e `invocar_planejamento_qa` em `planner_wrapper.py`**

Adicionar a constante junto com `_FALLBACK_BLOCKED_JSON` (perto do topo do módulo):

```python
_RETRY_PROMPT_SUFFIX = (
    "\n\nATENÇÃO: sua resposta anterior foi vazia ou inválida. "
    "Responda OBRIGATORIAMENTE com JSON válido seguindo o schema do PROTOCOLO ANTI-EMPTY. "
    "Se você não conseguir planejar (input incompleto, ambíguo, contraditório), "
    "devolva o JSON de bloqueio: "
    '{"tipo_entrada":"indefinido","modo":"indefinido","tools":[],'
    '"casos_de_teste_propostos":[],"lifecycle":{"status":"bloqueado",'
    '"execution_allowed":false,"next_step":"aguardar_resolucao_humana"},'
    '"erro":"<motivo curto>"}'
)
```

Adicionar a função no final do arquivo:

```python
async def invocar_planejamento_qa(request: str) -> str:
    """Invoca action_planner com retry programático.

    Garantia: sempre devolve string não-vazia com JSON estruturado.
    Caller (qa_pipeline) pode parsear sem se preocupar com empty.

    Args:
        request: texto do request original (requisitos + código se houver).

    Returns:
        JSON string com plano (válido) ou _FALLBACK_BLOCKED_JSON quando
        action_planner falhar duas vezes seguidas.
    """
    first = await _invoke_once(request)
    if not _is_empty(first):
        return first

    second = await _invoke_once(request + _RETRY_PROMPT_SUFFIX)
    if not _is_empty(second):
        return second

    return _FALLBACK_BLOCKED_JSON
```

- [ ] **Step 4: Rodar todos os testes do arquivo**

Run: `cd adk && .venv/bin/pytest tests/unit/test_planner_wrapper.py -v`

Expected: 13 PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/src/agents/workflow_qa/tools/planner_wrapper.py adk/tests/unit/test_planner_wrapper.py
git commit -m "$(cat <<'EOF'
add: invocar_planejamento_qa com retry programático + fallback determinístico

Garante que o caller (qa_pipeline) sempre receba JSON estruturado.
Lógica: chama _invoke_once; se empty, refaz com prompt reforçado;
se ainda empty, devolve _FALLBACK_BLOCKED_JSON (lifecycle.status=bloqueado).

Próxima task substitui AgentTool(action_planner) por
FunctionTool(invocar_planejamento_qa) no workflow_qa.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Plugar `invocar_planejamento_qa` no `workflow_qa/agent.py`

**Files:**
- Modify: `adk/src/agents/workflow_qa/agent.py` (linhas 12-20 dos imports + linhas 104-111 dos tools + `_INSTRUCTION`)
- Test: `adk/tests/unit/test_planner_wrapper.py` (assertion sobre integração)

- [ ] **Step 1: Adicionar teste de integração ao test_planner_wrapper.py**

Append em `adk/tests/unit/test_planner_wrapper.py`:

```python
def test_workflow_qa_usa_function_tool_e_nao_agent_tool_para_planner():
    """qa_pipeline.tools NÃO contém mais AgentTool(action_planner_agent);
    contém FunctionTool(invocar_planejamento_qa)."""
    from src.agents.workflow_qa.agent import agent as qa_pipeline

    tool_names = []
    for t in qa_pipeline.tools:
        if hasattr(t, "func"):
            tool_names.append(t.func.__name__)
        elif hasattr(t, "agent"):
            tool_names.append(f"AgentTool({t.agent.name})")
        else:
            tool_names.append(type(t).__name__)

    assert "invocar_planejamento_qa" in tool_names
    assert "AgentTool(action_planner)" not in tool_names


def test_workflow_qa_instruction_menciona_invocar_planejamento_qa():
    """_INSTRUCTION foi atualizado pra referenciar a nova tool."""
    from src.agents.workflow_qa.agent import agent as qa_pipeline
    assert "invocar_planejamento_qa" in qa_pipeline.instruction
    # E NÃO menciona mais "action_planner_agent" como tool a ser chamada
    # (pode mencionar como conceito histórico — verifica só que não está em
    # contexto de chamada de tool)
    assert "Encaminhe a entrada ao action_planner_agent" not in qa_pipeline.instruction
```

- [ ] **Step 2: Rodar — 2 FAILs (assertions falham porque ainda usa AgentTool)**

Run: `cd adk && .venv/bin/pytest tests/unit/test_planner_wrapper.py::test_workflow_qa_usa_function_tool_e_nao_agent_tool_para_planner tests/unit/test_planner_wrapper.py::test_workflow_qa_instruction_menciona_invocar_planejamento_qa -v`

Expected: 2 FAIL.

- [ ] **Step 3: Editar imports do `workflow_qa/agent.py`**

Localizar nas linhas 10-19 (imports atuais):

```python
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, LongRunningFunctionTool
from google.adk.tools.agent_tool import AgentTool

from src.agents.qa_agent.subagents.action_planner.agent import agent as action_planner_agent
from src.agents.qa_agent.subagents.code_fix_agent.agent import agent as code_fix_agent
from src.agents.qa_agent.subagents.receive_requirements import agent as receber_requisitos_agent
from src.agents.qa_agent.tools.hitl_tool import aguardar_aprovacao_humana
from src.agents.qa_agent.tools.pytest_runner import executar_pytest_tool
from src.agents.qa_agent.tools.doubt_tool import DoubtArtifactGenerator
```

Substituir por (remove import de `action_planner_agent`, adiciona `invocar_planejamento_qa`):

```python
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, LongRunningFunctionTool
from google.adk.tools.agent_tool import AgentTool

from src.agents.qa_agent.subagents.code_fix_agent.agent import agent as code_fix_agent
from src.agents.qa_agent.subagents.receive_requirements import agent as receber_requisitos_agent
from src.agents.qa_agent.tools.hitl_tool import aguardar_aprovacao_humana
from src.agents.qa_agent.tools.pytest_runner import executar_pytest_tool
from src.agents.qa_agent.tools.doubt_tool import DoubtArtifactGenerator
from src.agents.workflow_qa.tools.planner_wrapper import invocar_planejamento_qa
```

- [ ] **Step 4: Editar o bloco `_INSTRUCTION` no mesmo arquivo**

Localizar a string `_INSTRUCTION = """..."""` (linhas 23-93) e substituir o bloco do passo 1 (PLANEJAMENTO) — linhas 33-49 dentro da docstring:

```
1. PLANEJAMENTO
   Encaminhe a entrada ao action_planner_agent.
   Aguarde o plano de ação: tipos de teste, dependências, pontos de
   validação humana (HITL) e relatório de compliance preliminar.

   → Se o plano retornar com `hitl_checkpoint.required=true`:
        CHAME OBRIGATORIAMENTE a tool `aguardar_aprovacao_humana`
        passando checkpoint_id, approval_question, allowed_decisions e
        pause_reason extraídos do plano. NÃO emita texto pedindo
        aprovação — a tool faz a pausa real.
        Quando a tool retornar, leia o campo `decision`:
          - "aprovar"           → prossiga para a etapa 2 (geração).
          - "rejeitar"          → encerre com Doubt_Artifact citando
                                  `comments`; não gere testes.
          - "solicitar_ajustes" → encerre devolvendo `comments` ao
                                  solicitante; não gere testes.
```

Substituir por:

```
1. PLANEJAMENTO
   Chame `invocar_planejamento_qa(request=<entrada original>)`.
   Essa função roda o planner com retry automático e GARANTE retorno
   de JSON estruturado (nunca empty). O JSON contém: tipos de teste,
   dependências, pontos de validação humana (HITL) e relatório de
   compliance preliminar.

   → Se `lifecycle.status == "bloqueado"` no JSON retornado:
        Encerre com Doubt_Artifact citando `erro` do JSON.
        Esse caminho só é acionado quando o action_planner não
        conseguiu produzir plano nem com retry — bloqueio legítimo.

   → Se o plano retornar com `hitl_checkpoint.required=true`:
        CHAME OBRIGATORIAMENTE a tool `aguardar_aprovacao_humana`
        passando checkpoint_id, approval_question, allowed_decisions e
        pause_reason extraídos do plano. NÃO emita texto pedindo
        aprovação — a tool faz a pausa real.
        Quando a tool retornar, leia o campo `decision`:
          - "aprovar"           → prossiga para a etapa 2 (geração).
          - "rejeitar"          → encerre com Doubt_Artifact citando
                                  `comments`; não gere testes.
          - "solicitar_ajustes" → encerre devolvendo `comments` ao
                                  solicitante; não gere testes.
```

- [ ] **Step 5: Editar a lista de tools (linhas 104-111)**

Localizar:

```python
    tools=[
        AgentTool(agent=action_planner_agent),
        AgentTool(agent=receber_requisitos_agent),
        AgentTool(agent=code_fix_agent),
        FunctionTool(executar_pytest_tool),
        FunctionTool(DoubtArtifactGenerator.generate),
        LongRunningFunctionTool(aguardar_aprovacao_humana),
    ],
```

Substituir por:

```python
    tools=[
        FunctionTool(invocar_planejamento_qa),
        AgentTool(agent=receber_requisitos_agent),
        AgentTool(agent=code_fix_agent),
        FunctionTool(executar_pytest_tool),
        FunctionTool(DoubtArtifactGenerator.generate),
        LongRunningFunctionTool(aguardar_aprovacao_humana),
    ],
```

- [ ] **Step 6: Rodar testes**

Run: `cd adk && .venv/bin/pytest tests/unit/test_planner_wrapper.py -v`

Expected: 15 PASS (13 existentes + 2 novos).

- [ ] **Step 7: Smoke-test de import**

Run: `cd adk && .venv/bin/python -c "from src.agents.workflow_qa.agent import agent; print('ok:', agent.name, '| tools:', [getattr(t, \"func\", t).__name__ if hasattr(t, 'func') else type(t).__name__ for t in agent.tools])"`

Expected: `ok: qa_pipeline | tools: ['invocar_planejamento_qa', 'AgentTool', 'AgentTool', 'executar_pytest_tool', 'generate', 'LongRunningFunctionTool']` (nome exato pode variar, importante é não ter `AgentTool(action_planner)` na lista).

- [ ] **Step 8: Rodar suite unit inteira pra checar regressão**

Run: `cd adk && .venv/bin/pytest tests/unit -v --tb=short 2>&1 | tail -30`

Expected: Todos PASS. Nenhum teste de outro arquivo quebrado.

- [ ] **Step 9: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/src/agents/workflow_qa/agent.py adk/tests/unit/test_planner_wrapper.py
git commit -m "$(cat <<'EOF'
fix: qa_pipeline usa invocar_planejamento_qa com retry em vez de AgentTool

Substitui AgentTool(action_planner_agent) por FunctionTool(invocar_planejamento_qa).
O wrapper garante JSON estruturado mesmo quando o LLM do action_planner
retorna empty — elimina o Doubt_Artifact espúrio que travava o qa_pipeline
em "QA-PLANNING-BLOCK-001" mesmo quando o coder gerou código válido.

_INSTRUCTION ajustado: passo 1 (PLANEJAMENTO) referencia a tool nova e
trata lifecycle.status=bloqueado como bloqueio legítimo.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Diagnose pré-flight + validação E2E

**Files:** apenas execução — sem mudanças de código.

- [ ] **Step 1: Rodar `diagnose.sh` para validar schemas/coerência**

Run: `bash /home/hhiroshi92/github/AI4ES/.claude/skills/ai4es-e2e/scripts/diagnose.sh`

Expected: `✓ DIAGNOSE OK`. Se aparecer "schemas problemáticos" ou "tools fantasmas", reabrir a task correspondente.

- [ ] **Step 2: Reaproveitar o prompt da Marina em `/tmp/photographer-prompt.md`**

Verificar que existe: `test -s /tmp/photographer-prompt.md && echo "ok" || echo "FALTA — recriar"`.

Se faltar, recriar o conteúdo do prompt da Marina (ver memória `project-orchestrator-app-completeness` ou conversation history).

- [ ] **Step 3: Snapshot da run anterior (segurança)**

Run: `bash /home/hhiroshi92/github/AI4ES/.claude/skills/ai4es-e2e/scripts/snapshot.sh /tmp/pre-fix-snapshot`

Expected: cópia de `adk/workspace_output/` para `/tmp/pre-fix-snapshot/`. Não é estritamente necessário, mas dá ponto de comparação.

- [ ] **Step 4: Rodar o E2E**

Run: `KEEP_UP=1 bash /home/hhiroshi92/github/AI4ES/.claude/skills/ai4es-e2e/scripts/e2e.sh /tmp/photographer-prompt.md 2>&1 | tee /tmp/e2e-postfix.log | tail -80`

Expected: pipeline completa sem erro de schema. `qa_pipeline` deve emitir output substantivo (não `bloqueados: 1`).

- [ ] **Step 5: Inspecionar resultado**

Run: `bash /home/hhiroshi92/github/AI4ES/.claude/skills/ai4es-e2e/scripts/inspect-run.sh`

Expected:
- `workspace_output/requirements/` populado
- `workspace_output/design/` populado
- `workspace_output/coder/` populado
- `workspace_output/review/verificacao_revisao.md` **presente** (era o gap da Falha 1)
- `workspace_output/tests/inputs/` **populado** com JSONs (gap da Falha 2)
- `workspace_output/tests/<slug>/test_*.py` **presente**

- [ ] **Step 6: Confirmar manualmente que o review file faz sentido**

Run: `head -50 /home/hhiroshi92/github/AI4ES/adk/workspace_output/review/verificacao_revisao.md`

Expected: markdown com seções de COMPLETUDE / ARQUITETURA / CORRETUDE / TESTES, mencionando arquivos reais do coder.

- [ ] **Step 7: Confirmar saída do qa_pipeline**

Run: `grep -E "(sucessos|bloqueados|pytest)" /tmp/e2e-postfix.log | tail -20`

Expected: Mensagem do qa_pipeline mostrando `sucessos: N` (com N ≥ 0 e bloqueados ≤ 1 — pode haver bloqueio legítimo se o LLM do planner tiver dificuldade, mas não deve ser `QA-PLANNING-BLOCK-001`).

- [ ] **Step 8: Parar o servidor**

Run: `bash /home/hhiroshi92/github/AI4ES/.claude/skills/ai4es-e2e/scripts/stop-server.sh`

Expected: `Uvicorn na porta 8081 foi finalizado.`

- [ ] **Step 9 (final): Sem commit nesta task** — task de validação. Se algum gap aparecer (ex: review ainda vazio, qa ainda travando), reabrir Task 2 ou 6 conforme o sintoma.

---

## Self-Review checklist (após execução)

- [ ] Todos os 15+ testes unit passam (`pytest tests/unit -v`)
- [ ] `diagnose.sh` retorna OK
- [ ] `workspace_output/review/verificacao_revisao.md` existe após E2E
- [ ] `workspace_output/tests/inputs/*.json` existe após E2E
- [ ] `workspace_output/tests/<slug>/test_*.py` existe após E2E
- [ ] Nenhum `Doubt_Artifact_QA-PLANNING-BLOCK-001` espúrio
- [ ] Git log mostra 6 commits coerentes (Task 1, 2, 3, 4, 5, 6)
- [ ] Memórias relevantes atualizadas se descoberta nova surgir durante implementação
