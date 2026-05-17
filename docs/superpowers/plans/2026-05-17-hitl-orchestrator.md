# HITL real no orchestrator SDLC — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer com que "aprovar" depois de uma pausa HITL retome o `qa_pipeline` no ponto em que parou, em vez de reiniciar todos os 4 pipelines do orchestrator.

**Architecture:** `qa_pipeline` ganha uma `LongRunningFunctionTool` (`aguardar_aprovacao_humana`) que pausa nativamente via ADK. O `_PipelineOrchestrator` detecta a pausa via `Event.long_running_tool_ids`, persiste estado em `ctx.session.state`, mantém o `Runner` interno vivo em `_live_runners[outer_session_id]`, e na próxima invocação envia o texto do usuário como `function_response` ao runner pausado.

**Tech Stack:** Python 3.12, Google ADK (`google.adk.tools.LongRunningFunctionTool`, `google.adk.events.event.Event.long_running_tool_ids`), `pytest` com `asyncio_mode=auto`, `unittest.mock.AsyncMock`/`MagicMock`.

**Spec:** `docs/superpowers/specs/2026-05-17-hitl-orchestrator-design.md`

**Branch alvo:** `feature/code/1-initial-project-setup` (mesma branch)

---

## File Structure

**Created:**
- `adk/src/agents/qa_agent/tools/hitl_tool.py` — função `aguardar_aprovacao_humana` (será envolta em `LongRunningFunctionTool` pelo `workflow_qa`)
- `adk/src/agents/orchestrator/_helpers.py` — funções puras testáveis: `_parse_decision`, `_is_pending_long_running_call`, `_extract_user_text`, `_build_input`, `_set_pause_state`, `_clear_pause_state`
- `adk/tests/unit/test_hitl_tool.py` — assinatura, tipo de retorno, compat com Gemini schema
- `adk/tests/unit/test_orchestrator_helpers.py` — todos os helpers
- `adk/tests/unit/test_orchestrator_hitl.py` — `_PipelineOrchestrator` com runners mockados
- `adk/tests/unit/test_workflow_qa_hitl.py` — `LongRunningFunctionTool` registrada e instruction atualizada
- `adk/tests/integration/test_hitl_e2e.py` — orchestrator real com fake LLM emitindo `function_call` long-running
- `adk/tests/integration/__init__.py` — vazio (pacote)

**Modified:**
- `adk/src/agents/qa_agent/tools/__init__.py` — re-exporta `aguardar_aprovacao_humana`
- `adk/src/agents/workflow_qa/agent.py` — importa, registra como `LongRunningFunctionTool`, atualiza `_INSTRUCTION`
- `adk/src/agents/orchestrator/agent.py` — `_PipelineOrchestrator` reescrito (FRESH/RESUME branches, `_live_runners`)
- `adk/pyproject.toml` — adiciona `tests/integration` aos testpaths se estiver fora
- `CLAUDE.md` — nova subseção em "Gotchas e lições" documentando como o HITL agora funciona

**Separação de responsabilidades:**
- `orchestrator/agent.py` fica responsável por orquestração (loop, branching, runner lifecycle).
- `orchestrator/_helpers.py` concentra lógica pura (parsing, state manipulation, event inspection) — fácil de testar sem mocks.
- `qa_agent/tools/hitl_tool.py` isola a única tool nova; segue padrão existente (`pytest_runner.py`, `doubt_tool.py`).

---

## Convenções do projeto

- Linguagem: Português brasileiro em prompts, docstrings, commit messages, descrições de PR.
- Tipos: `Optional[str]` em parâmetros de tools (NUNCA `str | None` por causa do Gemini schema).
- Prefixos de commit: `add:`, `update:`, `fix:`, `refactor:`, `docs:`, `test:` (CONTRIBUTING.md).
- Commits assinados: `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
- Diretório de execução de comandos: `adk/` (a venv vive lá; `pythonpath="."`).
- Cada commit deve passar `pytest tests/unit` sem regressão.

---

## Pre-flight

### Task 0: Sanity check do ADK API

**Files:** nenhum (read-only)

- [ ] **Step 1: Verificar shape de Event e LongRunningFunctionTool**

Run (cwd = `adk/`):
```bash
.venv/bin/python -c "
from google.adk.events.event import Event
from google.adk.tools import LongRunningFunctionTool
assert 'long_running_tool_ids' in Event.model_fields, 'campo ausente'
ann = Event.model_fields['long_running_tool_ids'].annotation
print('long_running_tool_ids:', ann)
print('LongRunningFunctionTool:', LongRunningFunctionTool)
print('OK')
"
```

Expected output:
```
long_running_tool_ids: set[str] | None
LongRunningFunctionTool: <class 'google.adk.tools.long_running_tool.LongRunningFunctionTool'>
OK
```

Se falhar, escalar para o autor (versão de `google-adk` no `pyproject.toml` mudou). Sem commit nesta task — é sanity check.

---

## M1 — Tool `aguardar_aprovacao_humana`

### Task 1: Criar `hitl_tool.py` com testes

**Files:**
- Create: `adk/src/agents/qa_agent/tools/hitl_tool.py`
- Test: `adk/tests/unit/test_hitl_tool.py`

- [ ] **Step 1: Escrever o teste antes da implementação**

Create `adk/tests/unit/test_hitl_tool.py`:
```python
"""Testes da função aguardar_aprovacao_humana (HITL tool do qa_pipeline).

A função em si é um stub — quando registrada como LongRunningFunctionTool,
o ADK pausa antes do corpo executar. Os testes garantem:
  1. Assinatura compatível com Gemini schema (sem `str | None`).
  2. Retorno tipado com as chaves contratuais.
  3. Comportamento determinístico em chamada direta (importante para
     testes integration que invocam sem passar pelo runner).
"""

import inspect

import pytest


@pytest.mark.asyncio
async def test_aguardar_aprovacao_humana_retorna_dict_com_chaves_contratuais():
    from src.agents.qa_agent.tools.hitl_tool import aguardar_aprovacao_humana

    resultado = await aguardar_aprovacao_humana(
        checkpoint_id="abc",
        approval_question="Você aprova?",
        allowed_decisions=["aprovar", "rejeitar"],
        pause_reason="motivo",
    )

    assert isinstance(resultado, dict)
    for key in (
        "decision", "comments", "reviewer", "validated_at",
        "checkpoint_id", "approval_question",
        "allowed_decisions", "pause_reason",
    ):
        assert key in resultado, f"chave ausente: {key}"

    assert resultado["checkpoint_id"] == "abc"
    assert resultado["allowed_decisions"] == ["aprovar", "rejeitar"]


def test_aguardar_aprovacao_humana_assinatura_sem_union_pipe():
    """Gemini API rejeita anyOf gerado por `str | None`. Use Optional[str]."""
    from src.agents.qa_agent.tools.hitl_tool import aguardar_aprovacao_humana

    sig = inspect.signature(aguardar_aprovacao_humana)
    # pause_reason é o único Optional. Inspecionar a annotation.
    ann = sig.parameters["pause_reason"].annotation
    # Optional[str] aparece como Union[str, None] ou typing.Optional[str].
    # Não pode ser `str | None` (PEP 604) que vira tipo nativo `types.UnionType`.
    import types as _types
    assert not isinstance(ann, _types.UnionType), (
        f"pause_reason usa `str | None` (UnionType), rejeitado pelo Gemini. "
        f"Troque por Optional[str]. Got: {ann}"
    )


@pytest.mark.asyncio
async def test_pause_reason_pode_ser_omitido():
    from src.agents.qa_agent.tools.hitl_tool import aguardar_aprovacao_humana

    resultado = await aguardar_aprovacao_humana(
        checkpoint_id="x",
        approval_question="?",
        allowed_decisions=["aprovar"],
    )
    assert resultado["pause_reason"] is None
```

- [ ] **Step 2: Rodar o teste e confirmar falha**

Run (cwd = `adk/`):
```bash
.venv/bin/pytest tests/unit/test_hitl_tool.py -v
```

Expected: 3 erros de import (`ModuleNotFoundError: src.agents.qa_agent.tools.hitl_tool`).

- [ ] **Step 3: Implementar `hitl_tool.py`**

Create `adk/src/agents/qa_agent/tools/hitl_tool.py`:
```python
"""Tool de pausa HITL para o qa_pipeline.

Empacotada como LongRunningFunctionTool no workflow_qa/agent.py. Quando o
LLM chama esta função, o ADK emite um function_call event sem auto-resposta
e o runner devolve controle. A resposta vem da próxima invocação do
orchestrator como um function_response, montado a partir do texto livre do
usuário ("aprovar" / "rejeitar" / "solicitar_ajustes ...").
"""

from typing import Any, Optional


async def aguardar_aprovacao_humana(
    checkpoint_id: str,
    approval_question: str,
    allowed_decisions: list[str],
    pause_reason: Optional[str] = None,
) -> dict[str, Any]:
    """Pausa o agente até receber decisão humana explícita.

    Quando usar:
        Apenas quando o action_planner retornou um plano com
        `hitl_checkpoint.required=true`. Chame ANTES de prosseguir para
        a etapa de geração de testes. Após a tool retornar, leia o campo
        `decision` para decidir o próximo passo.

    Args:
        checkpoint_id: Identificador do checkpoint criado por
            create_hitl_checkpoint.
        approval_question: Texto literal da pergunta a ser exibida ao humano.
        allowed_decisions: Lista de decisões aceitáveis
            (ex.: ["aprovar", "rejeitar", "solicitar_ajustes"]).
        pause_reason: Motivo opcional da pausa (mostrado ao humano).

    Returns:
        dict com chaves: decision, comments, reviewer, validated_at,
        checkpoint_id, approval_question, allowed_decisions, pause_reason.
        `decision` é uma das opções de `allowed_decisions` quando a
        execução real acontece (via ADK + orchestrator); em chamada direta
        retorna "pending".
    """
    return {
        "decision": "pending",
        "comments": "",
        "reviewer": "usuario",
        "validated_at": None,
        "checkpoint_id": checkpoint_id,
        "approval_question": approval_question,
        "allowed_decisions": allowed_decisions,
        "pause_reason": pause_reason,
    }
```

- [ ] **Step 4: Rodar o teste e confirmar PASS**

Run (cwd = `adk/`):
```bash
.venv/bin/pytest tests/unit/test_hitl_tool.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add adk/src/agents/qa_agent/tools/hitl_tool.py adk/tests/unit/test_hitl_tool.py
git commit -m "$(cat <<'EOF'
add: tool aguardar_aprovacao_humana para HITL real do qa_pipeline

Stub que será envolvido em LongRunningFunctionTool em workflow_qa.
ADK pausa antes do corpo executar; o orchestrator envia function_response
com a decisão humana parseada de texto livre.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Re-exportar `aguardar_aprovacao_humana`

**Files:**
- Modify: `adk/src/agents/qa_agent/tools/__init__.py`
- Test: `adk/tests/unit/test_hitl_tool.py` (adiciona caso)

- [ ] **Step 1: Adicionar teste de re-export**

Append to `adk/tests/unit/test_hitl_tool.py`:
```python
def test_aguardar_aprovacao_humana_reexportada_no_init():
    """Tools do qa_agent devem ser importáveis do pacote tools/."""
    from src.agents.qa_agent.tools import aguardar_aprovacao_humana as exported
    from src.agents.qa_agent.tools.hitl_tool import aguardar_aprovacao_humana as direct
    assert exported is direct
```

- [ ] **Step 2: Rodar e confirmar falha**

Run:
```bash
.venv/bin/pytest tests/unit/test_hitl_tool.py::test_aguardar_aprovacao_humana_reexportada_no_init -v
```

Expected: ImportError ou AttributeError.

- [ ] **Step 3: Ler `__init__.py` atual e adicionar re-export**

Read `adk/src/agents/qa_agent/tools/__init__.py` para entender o formato (lista de imports + `__all__`).

Adicionar:
```python
from .hitl_tool import aguardar_aprovacao_humana
```

E acrescentar `"aguardar_aprovacao_humana"` em `__all__` (mantendo ordem alfabética se o arquivo já segue isso, senão append).

- [ ] **Step 4: Rodar e confirmar PASS**

Run:
```bash
.venv/bin/pytest tests/unit/test_hitl_tool.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add adk/src/agents/qa_agent/tools/__init__.py adk/tests/unit/test_hitl_tool.py
git commit -m "$(cat <<'EOF'
add: re-export aguardar_aprovacao_humana no pacote qa_agent.tools

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Registrar como `LongRunningFunctionTool` no `workflow_qa`

**Files:**
- Modify: `adk/src/agents/workflow_qa/agent.py`
- Test: `adk/tests/unit/test_workflow_qa_hitl.py` (novo)

- [ ] **Step 1: Escrever teste de registro**

Create `adk/tests/unit/test_workflow_qa_hitl.py`:
```python
"""Testes do registro de aguardar_aprovacao_humana no workflow_qa."""

from google.adk.tools import LongRunningFunctionTool


def test_workflow_qa_registra_aguardar_aprovacao_como_longrunning():
    """A tool DEVE ser LongRunningFunctionTool, não FunctionTool."""
    from src.agents.workflow_qa.agent import agent

    long_running_tools = [
        t for t in agent.tools if isinstance(t, LongRunningFunctionTool)
    ]
    assert len(long_running_tools) == 1, (
        f"Esperado exatamente 1 LongRunningFunctionTool. "
        f"Encontradas: {[type(t).__name__ for t in agent.tools]}"
    )

    decl = long_running_tools[0]._get_declaration()
    assert decl.name == "aguardar_aprovacao_humana", (
        f"Nome inesperado: {decl.name}"
    )


def test_workflow_qa_instruction_menciona_aguardar_aprovacao():
    """O instruction precisa instruir o LLM a chamar a tool quando hitl_checkpoint.required=true."""
    from src.agents.workflow_qa.agent import agent

    assert "aguardar_aprovacao_humana" in agent.instruction
    assert "hitl_checkpoint.required" in agent.instruction or "hitl_checkpoint" in agent.instruction


def test_workflow_qa_aguardar_aprovacao_schema_nao_quebra_gemini():
    """O FunctionDeclaration não pode ter any_of (Gemini 400 INVALID_ARGUMENT)."""
    from src.agents.workflow_qa.agent import agent

    long_running_tools = [
        t for t in agent.tools if isinstance(t, LongRunningFunctionTool)
    ]
    decl_json = long_running_tools[0]._get_declaration().model_dump_json(
        exclude_none=True, by_alias=True
    )
    # Gemini rejeita anyOf no schema (gerado por `str | None`).
    assert "any_of" not in decl_json, (
        f"Schema contém any_of (Gemini API rejeita): {decl_json}"
    )
```

- [ ] **Step 2: Rodar e confirmar falha**

Run:
```bash
.venv/bin/pytest tests/unit/test_workflow_qa_hitl.py -v
```

Expected: 3 failed.

- [ ] **Step 3: Modificar `workflow_qa/agent.py`**

Read `adk/src/agents/workflow_qa/agent.py` (97 linhas, vai inteiro no contexto).

Edit:
```python
# Substituir esta linha:
from google.adk.tools import FunctionTool
# Por:
from google.adk.tools import FunctionTool, LongRunningFunctionTool

# Adicionar import:
from src.agents.qa_agent.tools.hitl_tool import aguardar_aprovacao_humana
```

Adicionar à lista `tools=[...]` (após `FunctionTool(DoubtArtifactGenerator.generate)`):
```python
LongRunningFunctionTool(aguardar_aprovacao_humana),
```

Substituir a etapa 1 do `_INSTRUCTION` pelo texto abaixo (mantendo etapas 2–5 intactas):
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

- [ ] **Step 4: Rodar e confirmar PASS**

Run:
```bash
.venv/bin/pytest tests/unit/test_workflow_qa_hitl.py tests/unit/test_orchestrator_discovery.py -v
```

Expected: 7 passed (3 novos + 4 discovery existentes).

- [ ] **Step 5: Rodar suite completa para confirmar zero regressão**

Run:
```bash
.venv/bin/pytest tests/unit -v
```

Expected: todos passando (incluindo os 128 pré-existentes — collect_ignore exclui 2 arquivos).

- [ ] **Step 6: Commit**

```bash
git add adk/src/agents/workflow_qa/agent.py adk/tests/unit/test_workflow_qa_hitl.py
git commit -m "$(cat <<'EOF'
add: aguardar_aprovacao_humana como LongRunningFunctionTool no workflow_qa

qa_pipeline agora pausa nativamente via ADK quando o action_planner
sinaliza hitl_checkpoint.required=true. Instruction atualizada para
mapear decision -> próximo passo.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## M2 — Helpers do orchestrator (módulo `_helpers.py`)

### Task 4: Criar `_helpers.py` com `_parse_decision`

**Files:**
- Create: `adk/src/agents/orchestrator/_helpers.py`
- Test: `adk/tests/unit/test_orchestrator_helpers.py`

- [ ] **Step 1: Escrever testes para `_parse_decision`**

Create `adk/tests/unit/test_orchestrator_helpers.py`:
```python
"""Testes dos helpers puros do orchestrator (sem dependência de ADK runtime)."""

import pytest


# --- _parse_decision ---


def test_parse_decision_exato():
    from src.agents.orchestrator._helpers import _parse_decision
    assert _parse_decision("aprovar", ["aprovar", "rejeitar"]) == ("aprovar", "")


def test_parse_decision_case_insensitive():
    from src.agents.orchestrator._helpers import _parse_decision
    assert _parse_decision("APROVAR", ["aprovar"]) == ("aprovar", "")
    assert _parse_decision("Aprovar", ["aprovar"]) == ("aprovar", "")


def test_parse_decision_com_pontuacao_no_primeiro_token():
    from src.agents.orchestrator._helpers import _parse_decision
    assert _parse_decision("aprovar.", ["aprovar"]) == ("aprovar", "")
    assert _parse_decision("aprovar,", ["aprovar"]) == ("aprovar", "")


def test_parse_decision_com_comentarios():
    from src.agents.orchestrator._helpers import _parse_decision
    decision, comments = _parse_decision(
        "aprovar com cuidado em X",
        ["aprovar", "rejeitar"],
    )
    assert decision == "aprovar"
    assert comments == "com cuidado em X"


def test_parse_decision_prefixo_casa():
    from src.agents.orchestrator._helpers import _parse_decision
    # "aprov" é prefixo de "aprovar"
    assert _parse_decision("aprov", ["aprovar"]) == ("aprovar", "")


def test_parse_decision_invalido_levanta():
    from src.agents.orchestrator._helpers import _parse_decision
    with pytest.raises(ValueError, match="oi"):
        _parse_decision("oi", ["aprovar", "rejeitar"])


def test_parse_decision_vazio_levanta():
    from src.agents.orchestrator._helpers import _parse_decision
    with pytest.raises(ValueError, match="vazio"):
        _parse_decision("   ", ["aprovar"])


def test_parse_decision_solicitar_ajustes_com_comentarios():
    from src.agents.orchestrator._helpers import _parse_decision
    decision, comments = _parse_decision(
        "solicitar_ajustes Adicione cenário negativo para upload duplicado",
        ["aprovar", "rejeitar", "solicitar_ajustes"],
    )
    assert decision == "solicitar_ajustes"
    assert comments == "Adicione cenário negativo para upload duplicado"
```

- [ ] **Step 2: Rodar e confirmar falha**

Run:
```bash
.venv/bin/pytest tests/unit/test_orchestrator_helpers.py -v
```

Expected: ImportError em todos.

- [ ] **Step 3: Implementar `_parse_decision`**

Create `adk/src/agents/orchestrator/_helpers.py`:
```python
"""Funções puras do orchestrator — testáveis sem ADK runtime.

Separadas de `agent.py` para isolar a lógica de orquestração (loop,
runners, eventos) das funções determinísticas (parsing, manipulação
de state, inspeção de event shape).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _parse_decision(text: str, allowed: list[str]) -> tuple[str, str]:
    """Parseia texto livre humano em (decision, comments).

    Regras:
        - Primeiro token (separado por whitespace) é a decisão.
        - Case insensitive; trailing punctuation removida.
        - Match exato ou prefixo (ex: "aprov" → "aprovar").
        - Resto do texto vira `comments`.

    Args:
        text: Texto digitado pelo usuário.
        allowed: Lista de decisões aceitáveis.

    Returns:
        (decision_lower, comments_stripped). `decision_lower` é uma das
        strings de `allowed` (lowercase).

    Raises:
        ValueError: Se o texto for vazio ou não casar com nenhuma opção.
    """
    stripped = text.strip()
    if not stripped:
        raise ValueError("texto vazio")
    parts = stripped.split(None, 1)
    first = parts[0].lower().rstrip(",.;:!?")
    rest = parts[1] if len(parts) > 1 else ""

    for opt in allowed:
        opt_lower = opt.lower()
        if first == opt_lower or opt_lower.startswith(first):
            return opt_lower, rest

    raise ValueError(
        f"'{first}' não casa com nenhuma das decisões permitidas: {allowed}"
    )
```

- [ ] **Step 4: Rodar e confirmar PASS**

Run:
```bash
.venv/bin/pytest tests/unit/test_orchestrator_helpers.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add adk/src/agents/orchestrator/_helpers.py adk/tests/unit/test_orchestrator_helpers.py
git commit -m "$(cat <<'EOF'
add: helper _parse_decision do orchestrator (texto livre -> tupla)

Função pura testável que mapeia "aprovar com motivo X" -> ("aprovar",
"com motivo X"). Suporta match por prefixo e remove pontuação.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Helper `_is_pending_long_running_call`

**Files:**
- Modify: `adk/src/agents/orchestrator/_helpers.py`
- Modify: `adk/tests/unit/test_orchestrator_helpers.py`

- [ ] **Step 1: Adicionar testes**

Append to `adk/tests/unit/test_orchestrator_helpers.py`:
```python
# --- _is_pending_long_running_call ---


def _make_event(long_running_ids=None, function_call=None):
    """Helper local: monta um Event mínimo com Content + Part."""
    from google.adk.events.event import Event
    from google.genai import types

    parts = []
    if function_call:
        parts.append(types.Part(function_call=function_call))

    content = types.Content(role="model", parts=parts) if parts else None

    return Event(
        author="qa_pipeline",
        invocation_id="inv-1",
        content=content,
        long_running_tool_ids=set(long_running_ids) if long_running_ids else None,
    )


def test_is_pending_long_running_call_detecta_via_ids():
    from google.genai import types
    from src.agents.orchestrator._helpers import _is_pending_long_running_call

    fc = types.FunctionCall(
        id="call-1", name="aguardar_aprovacao_humana", args={}
    )
    event = _make_event(long_running_ids={"call-1"}, function_call=fc)
    part = event.content.parts[0]

    assert _is_pending_long_running_call(part, event) is True


def test_is_pending_long_running_call_ignora_function_call_nao_long_running():
    from google.genai import types
    from src.agents.orchestrator._helpers import _is_pending_long_running_call

    fc = types.FunctionCall(id="call-2", name="tool_normal", args={})
    event = _make_event(long_running_ids=None, function_call=fc)
    part = event.content.parts[0]

    assert _is_pending_long_running_call(part, event) is False


def test_is_pending_long_running_call_part_sem_function_call():
    from google.genai import types
    from src.agents.orchestrator._helpers import _is_pending_long_running_call

    event = _make_event(long_running_ids={"call-1"})
    # part texto, sem function_call
    text_part = types.Part(text="oi")

    assert _is_pending_long_running_call(text_part, event) is False


def test_is_pending_long_running_call_id_diferente():
    from google.genai import types
    from src.agents.orchestrator._helpers import _is_pending_long_running_call

    fc = types.FunctionCall(id="call-X", name="tool", args={})
    event = _make_event(long_running_ids={"call-OTHER"}, function_call=fc)
    part = event.content.parts[0]

    assert _is_pending_long_running_call(part, event) is False
```

- [ ] **Step 2: Rodar e confirmar falha**

Run:
```bash
.venv/bin/pytest tests/unit/test_orchestrator_helpers.py::test_is_pending_long_running_call_detecta_via_ids -v
```

Expected: ImportError / AttributeError em `_is_pending_long_running_call`.

- [ ] **Step 3: Implementar**

Append to `adk/src/agents/orchestrator/_helpers.py`:
```python
def _is_pending_long_running_call(part, event) -> bool:
    """True quando o part contém function_call long-running pendente no event.

    Detecção: `event.long_running_tool_ids` (set[str] | None) contém o
    `part.function_call.id`. ADK popula esse set quando emite um
    function_call de uma LongRunningFunctionTool sem auto-resposta.

    Args:
        part: `google.genai.types.Part` candidato.
        event: `google.adk.events.Event` que contém o part.

    Returns:
        True se part.function_call é um long-running pendente.
    """
    fc = getattr(part, "function_call", None)
    if fc is None:
        return False
    ids = getattr(event, "long_running_tool_ids", None)
    if not ids:
        return False
    return fc.id in ids
```

- [ ] **Step 4: Rodar e confirmar PASS**

Run:
```bash
.venv/bin/pytest tests/unit/test_orchestrator_helpers.py -v
```

Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add adk/src/agents/orchestrator/_helpers.py adk/tests/unit/test_orchestrator_helpers.py
git commit -m "$(cat <<'EOF'
add: helper _is_pending_long_running_call para detectar pausa HITL

Inspeciona Event.long_running_tool_ids (populado pelo ADK quando uma
LongRunningFunctionTool é chamada).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Helpers de state e input

**Files:**
- Modify: `adk/src/agents/orchestrator/_helpers.py`
- Modify: `adk/tests/unit/test_orchestrator_helpers.py`

- [ ] **Step 1: Adicionar testes**

Append to `adk/tests/unit/test_orchestrator_helpers.py`:
```python
# --- _set_pause_state / _clear_pause_state ---


def test_set_pause_state_grava_tres_chaves():
    from src.agents.orchestrator._helpers import _set_pause_state

    state = {}
    _set_pause_state(
        state,
        pipeline_name="qa_pipeline",
        inner_session_id="sid-abc",
        function_call_id="call-1",
        function_call_name="aguardar_aprovacao_humana",
        function_call_args={"checkpoint_id": "ck-1", "allowed_decisions": ["aprovar"]},
    )

    assert state["paused_pipeline"] == "qa_pipeline"
    assert state["paused_inner_session_id"] == "sid-abc"
    assert state["paused_function_call"] == {
        "id": "call-1",
        "name": "aguardar_aprovacao_humana",
        "args": {"checkpoint_id": "ck-1", "allowed_decisions": ["aprovar"]},
    }


def test_clear_pause_state_zera_tres_chaves():
    from src.agents.orchestrator._helpers import _clear_pause_state

    state = {
        "paused_pipeline": "qa_pipeline",
        "paused_inner_session_id": "sid",
        "paused_function_call": {"id": "x"},
        "accumulated_outputs": [("req", "...")],  # NÃO deve ser limpo
    }
    _clear_pause_state(state)

    assert state["paused_pipeline"] is None
    assert state["paused_inner_session_id"] is None
    assert state["paused_function_call"] is None
    # accumulated_outputs preservado
    assert state["accumulated_outputs"] == [("req", "...")]


# --- _extract_user_text ---


class _FakePart:
    def __init__(self, text):
        self.text = text


class _FakeUserContent:
    def __init__(self, parts):
        self.parts = parts


class _FakeCtx:
    def __init__(self, user_content):
        self.user_content = user_content


def test_extract_user_text_concatena_parts():
    from src.agents.orchestrator._helpers import _extract_user_text

    ctx = _FakeCtx(_FakeUserContent([_FakePart("foo"), _FakePart("bar")]))
    assert _extract_user_text(ctx) == "foo\nbar"


def test_extract_user_text_sem_content():
    from src.agents.orchestrator._helpers import _extract_user_text
    ctx = _FakeCtx(None)
    assert _extract_user_text(ctx) == ""


def test_extract_user_text_part_sem_text():
    from src.agents.orchestrator._helpers import _extract_user_text

    class P:
        text = None
    ctx = _FakeCtx(_FakeUserContent([P(), _FakePart("hello")]))
    assert _extract_user_text(ctx) == "hello"


# --- _build_input ---


def test_build_input_sem_accumulated():
    from src.agents.orchestrator._helpers import _build_input
    assert _build_input("prompt original", []) == "prompt original"


def test_build_input_com_accumulated():
    from src.agents.orchestrator._helpers import _build_input
    result = _build_input(
        "prompt",
        [("requirements_pipeline", "RF-001: criar ensaio"), ("design_pipeline", "diag.md")],
    )
    assert "prompt" in result
    assert "CONTEXTO DAS FASES ANTERIORES" in result
    assert "### Output de requirements_pipeline" in result
    assert "RF-001: criar ensaio" in result
    assert "### Output de design_pipeline" in result
    assert "diag.md" in result


def test_build_input_trunca_output_em_8000_chars():
    from src.agents.orchestrator._helpers import _build_input
    huge = "x" * 20000
    result = _build_input("prompt", [("req", huge)])
    # 8000 chars do output devem aparecer; o resto não
    assert "x" * 8000 in result
    # Tolerância: pode ter sufixo de truncagem; verifica que não tem 20000 x's seguidos
    assert "x" * 20000 not in result
```

- [ ] **Step 2: Rodar e confirmar falha**

Run:
```bash
.venv/bin/pytest tests/unit/test_orchestrator_helpers.py -v
```

Expected: 8 novos falhando.

- [ ] **Step 3: Implementar helpers**

Append to `adk/src/agents/orchestrator/_helpers.py`:
```python
def _extract_user_text(ctx) -> str:
    """Concatena os textos dos parts de `ctx.user_content`.

    Retorna string vazia quando user_content é None ou todos os parts
    são não-texto (function_response, function_call, etc.).
    """
    user_content = getattr(ctx, "user_content", None)
    if user_content is None:
        return ""
    parts = getattr(user_content, "parts", None) or []
    chunks = []
    for part in parts:
        text = getattr(part, "text", None)
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()


def _build_input(user_text: str, accumulated: list[tuple[str, str]]) -> str:
    """Monta input para um pipeline interno.

    Sem accumulated: retorna `user_text` sem modificações (FRESH RUN do
    primeiro pipeline). Com accumulated: anexa "CONTEXTO DAS FASES
    ANTERIORES" com cada output truncado em 8000 caracteres.
    """
    if not accumulated:
        return user_text

    prior = "\n\n".join(
        f"### Output de {nome}:\n{texto[:8000]}"
        for nome, texto in accumulated
    )
    return (
        f"{user_text}\n\n"
        f"---\n"
        f"CONTEXTO DAS FASES ANTERIORES:\n{prior}\n"
        f"---\n"
    )


def _set_pause_state(
    state: dict[str, Any],
    *,
    pipeline_name: str,
    inner_session_id: str,
    function_call_id: str,
    function_call_name: str,
    function_call_args: dict[str, Any],
) -> None:
    """Grava as 3 chaves de pausa em state. Invariante: ou todas ou nenhuma."""
    state["paused_pipeline"] = pipeline_name
    state["paused_inner_session_id"] = inner_session_id
    state["paused_function_call"] = {
        "id": function_call_id,
        "name": function_call_name,
        "args": function_call_args,
    }


def _clear_pause_state(state: dict[str, Any]) -> None:
    """Zera as 3 chaves de pausa. Preserva `accumulated_outputs`."""
    state["paused_pipeline"] = None
    state["paused_inner_session_id"] = None
    state["paused_function_call"] = None


def _build_function_response_payload(
    decision: str,
    comments: str,
    checkpoint_id: str,
) -> dict[str, Any]:
    """Payload do function_response enviado ao runner pausado."""
    return {
        "decision": decision,
        "comments": comments,
        "reviewer": "usuario",
        "validated_at": datetime.now(timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checkpoint_id": checkpoint_id,
    }
```

- [ ] **Step 4: Rodar e confirmar PASS**

Run:
```bash
.venv/bin/pytest tests/unit/test_orchestrator_helpers.py -v
```

Expected: 20 passed.

- [ ] **Step 5: Commit**

```bash
git add adk/src/agents/orchestrator/_helpers.py adk/tests/unit/test_orchestrator_helpers.py
git commit -m "$(cat <<'EOF'
add: helpers de state, extracao de input e function_response payload

_extract_user_text, _build_input, _set_pause_state, _clear_pause_state e
_build_function_response_payload. Funções puras testáveis sem ADK runtime.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## M2 + M3 — `_PipelineOrchestrator` reescrito

### Task 7: Reescrita do orchestrator com FRESH RUN + RESUME

**Files:**
- Modify: `adk/src/agents/orchestrator/agent.py`
- Test: `adk/tests/unit/test_orchestrator_hitl.py` (novo)

Esta task é grande — agrupa as 6 mudanças no `_run_async_impl` num único commit porque elas são interdependentes (FRESH branch escreve estado que RESUME branch lê). Os 7 casos de teste são escritos primeiro.

- [ ] **Step 1: Escrever todos os 7 testes da reescrita**

Create `adk/tests/unit/test_orchestrator_hitl.py`:
```python
"""Testes do _PipelineOrchestrator com HITL.

Estratégia: mockar Runner.run_async para emitir Events controlados.
Cada teste constrói um Runner falso, injeta no orchestrator via
monkeypatch do Runner(...) construtor.
"""

from __future__ import annotations

from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.adk.events.event import Event
from google.genai import types


# --- Helpers de fixture ---


def _make_text_event(author: str, text: str) -> Event:
    return Event(
        author=author,
        invocation_id="inv-test",
        content=types.Content(role="model", parts=[types.Part(text=text)]),
    )


def _make_long_running_pause_event(
    author: str,
    call_id: str,
    call_name: str = "aguardar_aprovacao_humana",
    call_args: dict | None = None,
) -> Event:
    fc = types.FunctionCall(
        id=call_id,
        name=call_name,
        args=call_args or {
            "checkpoint_id": "ck-1",
            "approval_question": "?",
            "allowed_decisions": ["aprovar", "rejeitar", "solicitar_ajustes"],
        },
    )
    return Event(
        author=author,
        invocation_id="inv-test",
        content=types.Content(role="model", parts=[types.Part(function_call=fc)]),
        long_running_tool_ids={call_id},
    )


class _FakeSession:
    def __init__(self, session_id: str = "inner-sid", user_id: str = "u"):
        self.id = session_id
        self.user_id = user_id


class _FakeSessionService:
    async def create_session(self, *, app_name, user_id, state):
        return _FakeSession()


def _make_fake_runner(events_to_yield: list[Event]) -> MagicMock:
    """Runner falso que retorna eventos pré-definidos em run_async."""
    runner = MagicMock()
    runner.session_service = _FakeSessionService()
    runner.close = AsyncMock(return_value=None)

    async def fake_run_async(**kwargs) -> AsyncGenerator[Event, None]:
        for e in events_to_yield:
            yield e

    runner.run_async = fake_run_async
    return runner


class _FakeCtx:
    def __init__(self, user_text: str, session_id: str = "outer-sid",
                 state: dict | None = None):
        self.user_content = types.Content(
            role="user", parts=[types.Part(text=user_text)]
        )
        self.user_id = "test-user"
        self.session = MagicMock()
        self.session.id = session_id
        self.session.state = state if state is not None else {}
        self.artifact_service = MagicMock()
        self.credential_service = MagicMock()
        self.plugin_manager = MagicMock()
        self.plugin_manager.plugins = []


# --- U1: FRESH RUN sem pausa ---


@pytest.mark.asyncio
async def test_fresh_run_sem_pausa_executa_4_pipelines(monkeypatch):
    """Todos os 4 pipelines rodam; state.paused_pipeline fica None."""
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    runners_iter = iter([
        _make_fake_runner([_make_text_event("requirements_pipeline", "req-out")]),
        _make_fake_runner([_make_text_event("design_pipeline", "design-out")]),
        _make_fake_runner([_make_text_event("coding_review_pipeline", "cr-out")]),
        _make_fake_runner([_make_text_event("qa_pipeline", "qa-out")]),
    ])
    monkeypatch.setattr(
        "src.agents.orchestrator.agent.Runner",
        lambda **kwargs: next(runners_iter),
    )

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    ctx = _FakeCtx("Prompt do fotógrafo")

    events = [e async for e in orch._run_async_impl(ctx)]

    # Pelo menos 4 textos vistos (um por pipeline)
    texts_seen = [
        p.text
        for e in events
        if e.content
        for p in e.content.parts
        if p.text
    ]
    assert "req-out" in texts_seen
    assert "design-out" in texts_seen
    assert "cr-out" in texts_seen
    assert "qa-out" in texts_seen

    # State final: sem pausa
    assert ctx.session.state.get("paused_pipeline") is None
    assert len(ctx.session.state["accumulated_outputs"]) == 4


# --- U2: FRESH RUN com pausa em qa ---


@pytest.mark.asyncio
async def test_fresh_run_com_pausa_para_em_qa(monkeypatch):
    """qa_pipeline emite long-running call. Iteração para; state.paused_pipeline=qa."""
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    pause_event = _make_long_running_pause_event("qa_pipeline", call_id="call-XYZ")

    runners_iter = iter([
        _make_fake_runner([_make_text_event("requirements_pipeline", "req")]),
        _make_fake_runner([_make_text_event("design_pipeline", "design")]),
        _make_fake_runner([_make_text_event("coding_review_pipeline", "cr")]),
        _make_fake_runner([_make_text_event("qa_pipeline", "planning..."), pause_event]),
    ])
    monkeypatch.setattr(
        "src.agents.orchestrator.agent.Runner",
        lambda **kwargs: next(runners_iter),
    )

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    ctx = _FakeCtx("Prompt do fotógrafo", session_id="outer-1")

    _ = [e async for e in orch._run_async_impl(ctx)]

    assert ctx.session.state["paused_pipeline"] == "qa_pipeline"
    assert ctx.session.state["paused_function_call"]["id"] == "call-XYZ"
    assert ctx.session.state["paused_function_call"]["name"] == "aguardar_aprovacao_humana"
    # _live_runners deve ter o runner do qa
    assert "outer-1" in orch._live_runners
    # 3 outputs antes da pausa
    assert len(ctx.session.state["accumulated_outputs"]) == 3


# --- U3: RESUME aprovar conclui ---


@pytest.mark.asyncio
async def test_resume_aprovar_envia_function_response_e_conclui(monkeypatch):
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    # Runner que estava vivo: vai receber function_response e emitir conclusão
    resume_runner = _make_fake_runner(
        [_make_text_event("qa_pipeline", "qa-final-output")]
    )
    # Captura o new_message passado para run_async
    captured = {}
    async def fake_resume(**kwargs):
        captured["new_message"] = kwargs.get("new_message")
        captured["session_id"] = kwargs.get("session_id")
        for e in [_make_text_event("qa_pipeline", "qa-final-output")]:
            yield e
    resume_runner.run_async = fake_resume

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    orch._live_runners["outer-1"] = (resume_runner, "inner-qa-sid")

    ctx = _FakeCtx(
        "aprovar com cuidado em X",
        session_id="outer-1",
        state={
            "paused_pipeline": "qa_pipeline",
            "paused_inner_session_id": "inner-qa-sid",
            "paused_function_call": {
                "id": "call-XYZ",
                "name": "aguardar_aprovacao_humana",
                "args": {
                    "checkpoint_id": "ck-1",
                    "allowed_decisions": ["aprovar", "rejeitar", "solicitar_ajustes"],
                },
            },
            "accumulated_outputs": [
                ("requirements_pipeline", "req"),
                ("design_pipeline", "design"),
                ("coding_review_pipeline", "cr"),
            ],
        },
    )

    _ = [e async for e in orch._run_async_impl(ctx)]

    # Foi enviado function_response no session_id correto
    assert captured["session_id"] == "inner-qa-sid"
    msg = captured["new_message"]
    assert msg.role == "user"
    assert len(msg.parts) == 1
    fr = msg.parts[0].function_response
    assert fr is not None
    assert fr.name == "aguardar_aprovacao_humana"
    assert fr.id == "call-XYZ"
    assert fr.response["decision"] == "aprovar"
    assert fr.response["comments"] == "com cuidado em X"
    assert fr.response["checkpoint_id"] == "ck-1"

    # State limpo
    assert ctx.session.state["paused_pipeline"] is None
    assert ctx.session.state["paused_inner_session_id"] is None
    assert ctx.session.state["paused_function_call"] is None
    # accumulated ganhou qa
    nomes = [n for n, _ in ctx.session.state["accumulated_outputs"]]
    assert "qa_pipeline" in nomes
    # runner limpo
    assert "outer-1" not in orch._live_runners
    # runner.close foi chamado
    resume_runner.close.assert_awaited_once()


# --- U4: RESUME rejeitar com comentário ---


@pytest.mark.asyncio
async def test_resume_rejeitar_preserva_comentario(monkeypatch):
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    captured = {}
    async def fake_resume(**kwargs):
        captured["new_message"] = kwargs.get("new_message")
        for e in [_make_text_event("qa_pipeline", "abortado por rejeicao")]:
            yield e

    runner = _make_fake_runner([])
    runner.run_async = fake_resume

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    orch._live_runners["outer-1"] = (runner, "inner-qa-sid")

    ctx = _FakeCtx(
        "rejeitar criterios insuficientes",
        session_id="outer-1",
        state={
            "paused_pipeline": "qa_pipeline",
            "paused_inner_session_id": "inner-qa-sid",
            "paused_function_call": {
                "id": "call-1",
                "name": "aguardar_aprovacao_humana",
                "args": {
                    "checkpoint_id": "ck-1",
                    "allowed_decisions": ["aprovar", "rejeitar", "solicitar_ajustes"],
                },
            },
            "accumulated_outputs": [],
        },
    )

    _ = [e async for e in orch._run_async_impl(ctx)]

    fr = captured["new_message"].parts[0].function_response
    assert fr.response["decision"] == "rejeitar"
    assert fr.response["comments"] == "criterios insuficientes"


# --- U5: RESUME texto inválido mantém pausa ---


@pytest.mark.asyncio
async def test_resume_texto_invalido_yields_erro_e_mantem_pausa(monkeypatch):
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    runner = _make_fake_runner([])
    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    orch._live_runners["outer-1"] = (runner, "inner-qa-sid")

    state_pause = {
        "paused_pipeline": "qa_pipeline",
        "paused_inner_session_id": "inner-qa-sid",
        "paused_function_call": {
            "id": "call-1",
            "name": "aguardar_aprovacao_humana",
            "args": {"checkpoint_id": "ck-1", "allowed_decisions": ["aprovar", "rejeitar"]},
        },
        "accumulated_outputs": [],
    }
    ctx = _FakeCtx("oi", session_id="outer-1", state=dict(state_pause))

    events = [e async for e in orch._run_async_impl(ctx)]

    # Pelo menos um event de erro com texto contendo "Decisão inválida"
    texts = [
        p.text
        for e in events if e.content
        for p in e.content.parts if p.text
    ]
    assert any("inválida" in t.lower() or "invalid" in t.lower() for t in texts)

    # Pausa intacta
    assert ctx.session.state["paused_pipeline"] == "qa_pipeline"
    assert "outer-1" in orch._live_runners
    # runner.close NÃO foi chamado
    runner.close.assert_not_awaited()


# --- U6: RESUME sem _live_runners (servidor reiniciou) ---


@pytest.mark.asyncio
async def test_resume_sem_live_runner_volta_erro_e_limpa_state():
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    # _live_runners vazio; servidor "foi reiniciado"

    ctx = _FakeCtx(
        "aprovar",
        session_id="outer-1",
        state={
            "paused_pipeline": "qa_pipeline",
            "paused_inner_session_id": "inner-qa-sid",
            "paused_function_call": {
                "id": "call-1", "name": "aguardar_aprovacao_humana",
                "args": {"checkpoint_id": "ck-1", "allowed_decisions": ["aprovar"]},
            },
            "accumulated_outputs": [],
        },
    )

    events = [e async for e in orch._run_async_impl(ctx)]

    texts = [
        p.text
        for e in events if e.content
        for p in e.content.parts if p.text
    ]
    assert any("expirada" in t.lower() or "reinic" in t.lower() for t in texts)
    # State limpo
    assert ctx.session.state["paused_pipeline"] is None


# --- U7: RESUME com pausa encadeada ---


@pytest.mark.asyncio
async def test_resume_com_pausa_encadeada_mantem_runner_e_atualiza_state():
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    second_pause = _make_long_running_pause_event(
        "qa_pipeline", call_id="call-SECOND",
        call_args={
            "checkpoint_id": "ck-2",
            "approval_question": "?",
            "allowed_decisions": ["aprovar", "rejeitar"],
        },
    )

    async def fake_resume(**kwargs):
        for e in [_make_text_event("qa_pipeline", "another check..."), second_pause]:
            yield e

    runner = _make_fake_runner([])
    runner.run_async = fake_resume

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    orch._live_runners["outer-1"] = (runner, "inner-qa-sid")

    ctx = _FakeCtx(
        "aprovar",
        session_id="outer-1",
        state={
            "paused_pipeline": "qa_pipeline",
            "paused_inner_session_id": "inner-qa-sid",
            "paused_function_call": {
                "id": "call-1", "name": "aguardar_aprovacao_humana",
                "args": {"checkpoint_id": "ck-1", "allowed_decisions": ["aprovar", "rejeitar"]},
            },
            "accumulated_outputs": [],
        },
    )

    _ = [e async for e in orch._run_async_impl(ctx)]

    # Estado de pausa atualizado para o segundo call
    assert ctx.session.state["paused_pipeline"] == "qa_pipeline"
    assert ctx.session.state["paused_function_call"]["id"] == "call-SECOND"
    assert ctx.session.state["paused_function_call"]["args"]["checkpoint_id"] == "ck-2"
    # Runner permanece vivo, close NÃO chamado
    assert "outer-1" in orch._live_runners
    runner.close.assert_not_awaited()
```

- [ ] **Step 2: Rodar e confirmar 7 falhas**

Run:
```bash
.venv/bin/pytest tests/unit/test_orchestrator_hitl.py -v
```

Expected: 7 failed (importe orchestrator.agent ainda funciona mas `_live_runners` não existe; testes detalham qual atributo/comportamento falta).

- [ ] **Step 3: Reescrever `orchestrator/agent.py`**

Read `adk/src/agents/orchestrator/agent.py` (137 linhas) inteiramente.

Substituir o arquivo por:
```python
"""Orchestrator SDLC v5 — Custom BaseAgent com HITL via LongRunningFunctionTool.

Evolução do v4 (sessões isoladas) com suporte real a pausa HITL no
qa_pipeline. Em vez de descartar a sessão do qa_pipeline ao fim de cada
invocação, mantemos o Runner vivo em `_live_runners[outer_session_id]`
quando o pipeline emite um function_call long-running pendente. Na
próxima invocação, o texto do usuário ("aprovar"/"rejeitar"/...) é
parseado em (decision, comments), embalado em function_response e
enviado ao runner pausado via runner.run_async — qa_pipeline retoma
exatamente de onde parou.

Estado persistido em ctx.session.state (sessão externa):
    accumulated_outputs: list[tuple[name, last_text]]
    paused_pipeline: str | None
    paused_inner_session_id: str | None
    paused_function_call: {id, name, args} | None

Estado em memória do processo (NÃO persistido — limitação documentada):
    _live_runners: dict[outer_session_id, tuple[Runner, inner_session_id]]
"""

from __future__ import annotations

from typing import Any, AsyncGenerator, ClassVar, Dict, List, Tuple

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import ConfigDict, PrivateAttr

from src.agents.workflow_requirements.agent import agent as requirements_pipeline
from src.agents.workflow_design_pipeline.agent import agent as design_pipeline
from src.agents.workflow_coding_review.agent import agent as coding_review_pipeline
from src.agents.workflow_qa.agent import agent as qa_pipeline

from src.agents.orchestrator._helpers import (
    _build_function_response_payload,
    _build_input,
    _clear_pause_state,
    _extract_user_text,
    _is_pending_long_running_call,
    _parse_decision,
    _set_pause_state,
)


class _PipelineOrchestrator(BaseAgent):
    """Roda pipelines em sequência, com pausa HITL no qa_pipeline."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    _pipelines: ClassVar[List[BaseAgent]] = [
        requirements_pipeline,
        design_pipeline,
        coding_review_pipeline,
        qa_pipeline,
    ]

    # Runners vivos do pipeline pausado, indexados por outer_session_id.
    # NÃO persistido — reinício do servidor entre T0 e T1 perde isto.
    _live_runners: Dict[str, Tuple[Any, str]] = PrivateAttr(default_factory=dict)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        outer_sid = ctx.session.id
        user_text = _extract_user_text(ctx)
        if not user_text:
            return

        paused = state.get("paused_pipeline")

        # === Branch RESUME ===
        if paused:
            async for ev in self._handle_resume(ctx, outer_sid, user_text):
                yield ev
            return

        # === Branch FRESH RUN ===
        async for ev in self._handle_fresh_run(ctx, outer_sid, user_text):
            yield ev

    async def _handle_resume(
        self, ctx: InvocationContext, outer_sid: str, user_text: str
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        paused = state["paused_pipeline"]
        runner_handle = self._live_runners.get(outer_sid)

        if runner_handle is None:
            # Servidor reiniciou entre T0 e T1 — runner perdeu-se.
            _clear_pause_state(state)
            yield self._make_text_event(
                paused,
                "Sessão HITL expirada (servidor foi reiniciado entre a pausa "
                "e a resposta). Por favor reenvie o prompt original para "
                "iniciar uma nova sessão."
            )
            return

        runner, inner_sid = runner_handle
        call = state["paused_function_call"]
        allowed = call["args"].get("allowed_decisions", []) or []

        try:
            decision, comments = _parse_decision(user_text, allowed)
        except ValueError as exc:
            yield self._make_text_event(
                paused,
                f"Decisão inválida: {exc}. "
                f"Por favor responda com uma destas opções: "
                f"{', '.join(allowed)}."
            )
            return  # pausa intacta

        # ADK exige que `id` no function_response case com o id do
        # function_call original. Construímos via FunctionResponse direto
        # porque `types.Part.from_function_response` não expõe `id=` em
        # algumas versões.
        function_response = types.Content(
            role="user",
            parts=[types.Part(function_response=types.FunctionResponse(
                id=call["id"],
                name=call["name"],
                response=_build_function_response_payload(
                    decision=decision,
                    comments=comments,
                    checkpoint_id=call["args"].get("checkpoint_id", ""),
                ),
            ))],
        )

        last_text = ""
        new_pause = None
        async for event in runner.run_async(
            user_id=ctx.user_id,
            session_id=inner_sid,
            new_message=function_response,
        ):
            yield event
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        last_text = part.text
                    elif _is_pending_long_running_call(part, event):
                        new_pause = part.function_call

        if new_pause is not None:
            # Pausa encadeada — atualiza state, mantém runner.
            _set_pause_state(
                state,
                pipeline_name=paused,
                inner_session_id=inner_sid,
                function_call_id=new_pause.id,
                function_call_name=new_pause.name,
                function_call_args=dict(new_pause.args or {}),
            )
            return

        # Conclusão: cleanup.
        _clear_pause_state(state)
        accumulated = state.get("accumulated_outputs", []) or []
        accumulated.append((paused, last_text))
        state["accumulated_outputs"] = accumulated
        await runner.close()
        self._live_runners.pop(outer_sid, None)

    async def _handle_fresh_run(
        self, ctx: InvocationContext, outer_sid: str, user_text: str
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        # Fresh run reseta accumulated (nova conversa SDLC).
        state["accumulated_outputs"] = []
        accumulated: list[tuple[str, str]] = []

        # Se houver _live_runner legado em outer_sid (sessão zombie), fecha.
        legacy = self._live_runners.pop(outer_sid, None)
        if legacy is not None:
            await legacy[0].close()

        for pipeline in self._pipelines:
            pipeline_input = _build_input(user_text, accumulated)
            content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=pipeline_input)],
            )

            runner = Runner(
                app_name=pipeline.name,
                agent=pipeline,
                artifact_service=ctx.artifact_service,
                session_service=InMemorySessionService(),
                memory_service=InMemoryMemoryService(),
                credential_service=ctx.credential_service,
                plugins=ctx.plugin_manager.plugins if ctx.plugin_manager else None,
            )
            inner_session = await runner.session_service.create_session(
                app_name=pipeline.name, user_id=ctx.user_id, state={},
            )

            last_text = ""
            pending_pause = None
            async for event in runner.run_async(
                user_id=inner_session.user_id,
                session_id=inner_session.id,
                new_message=content,
            ):
                yield event
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            last_text = part.text
                        elif _is_pending_long_running_call(part, event):
                            pending_pause = part.function_call

            if pending_pause is not None:
                # Salva estado, MANTÉM runner vivo (não fecha).
                self._live_runners[outer_sid] = (runner, inner_session.id)
                _set_pause_state(
                    state,
                    pipeline_name=pipeline.name,
                    inner_session_id=inner_session.id,
                    function_call_id=pending_pause.id,
                    function_call_name=pending_pause.name,
                    function_call_args=dict(pending_pause.args or {}),
                )
                state["accumulated_outputs"] = accumulated
                return  # NÃO roda pipelines subsequentes

            # Pipeline concluiu sem pausa.
            accumulated.append((pipeline.name, last_text))
            await runner.close()

        state["accumulated_outputs"] = accumulated

    @staticmethod
    def _make_text_event(author: str, text: str) -> Event:
        return Event(
            author=author,
            invocation_id="orchestrator-error",
            content=types.Content(role="model", parts=[types.Part(text=text)]),
        )


root_agent = _PipelineOrchestrator(
    name="orchestrator",
    description=(
        "Orchestrator SDLC v5 — executa requirements → design → coding+review → qa "
        "em sessões isoladas com HITL real no qa_pipeline. Sem MALFORMED_FUNCTION_CALL "
        "(sem LLM no topo) e sem token overflow (sessões dedicadas)."
    ),
)
```

- [ ] **Step 4: Rodar testes do orchestrator e confirmar PASS**

Run:
```bash
.venv/bin/pytest tests/unit/test_orchestrator_hitl.py tests/unit/test_orchestrator_discovery.py -v
```

Expected: 7 + 4 = 11 passed.

- [ ] **Step 5: Rodar suite completa**

Run:
```bash
.venv/bin/pytest tests/unit -v
```

Expected: todos verdes (sem regressão).

- [ ] **Step 6: Commit**

```bash
git add adk/src/agents/orchestrator/agent.py adk/tests/unit/test_orchestrator_hitl.py
git commit -m "$(cat <<'EOF'
update: orchestrator v5 com HITL real (FRESH/RESUME branches + _live_runners)

_PipelineOrchestrator detecta pausa via Event.long_running_tool_ids,
persiste state em ctx.session.state e mantém runner do pipeline pausado
vivo em _live_runners[outer_session_id]. Próxima invocação parseia
texto livre do usuário em (decision, comments), embala em function_response
e envia ao runner pausado.

Cobre: U1 fresh sem pausa, U2 fresh com pausa, U3 resume aprovar, U4
resume rejeitar, U5 texto inválido, U6 servidor reiniciado, U7 pausa
encadeada.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Integration test

### Task 8: Test E2E com Runner real + agente stub

**Files:**
- Create: `adk/tests/integration/__init__.py`
- Create: `adk/tests/integration/test_hitl_e2e.py`
- Modify: `adk/pyproject.toml` (se `tests/integration` não estiver em `testpaths`)

- [ ] **Step 1: Conferir pyproject.toml testpaths**

Read `adk/pyproject.toml` para encontrar `[tool.pytest.ini_options]`. Se `testpaths` for só `["tests"]`, OK (pega `tests/integration` recursivo). Se for `["tests/unit"]`, expandir para `["tests/unit", "tests/integration"]`.

- [ ] **Step 2: Criar package marker**

Create `adk/tests/integration/__init__.py` (vazio).

- [ ] **Step 3: Escrever integration test**

Create `adk/tests/integration/test_hitl_e2e.py`:
```python
"""Integration: orchestrator real (sem LLM real) com agente stub que pausa.

Em vez de stubar Runner como no unit, aqui usamos o Runner real do ADK
contra um BaseAgent stub que emite um function_call long-running. Valida
a integração end-to-end com a infra ADK.
"""

from __future__ import annotations

from typing import AsyncGenerator, ClassVar

import pytest
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import ConfigDict


class _StubPausesOnce(BaseAgent):
    """Agente stub: na primeira invocação emite function_call long-running.
    Na segunda (recebendo function_response), emite texto final."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # Detecta function_response no user_content
        if ctx.user_content and ctx.user_content.parts:
            for p in ctx.user_content.parts:
                fr = getattr(p, "function_response", None)
                if fr is not None:
                    yield Event(
                        author=self.name,
                        invocation_id=ctx.invocation_id,
                        content=types.Content(
                            role="model",
                            parts=[types.Part(text=f"decisao recebida: {fr.response.get('decision')}")],
                        ),
                    )
                    return

        # Primeiro turno: emite long-running pendente
        fc = types.FunctionCall(
            id="call-stub-1",
            name="aguardar_aprovacao_humana",
            args={
                "checkpoint_id": "ck-stub",
                "approval_question": "?",
                "allowed_decisions": ["aprovar", "rejeitar"],
            },
        )
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            content=types.Content(role="model", parts=[types.Part(function_call=fc)]),
            long_running_tool_ids={"call-stub-1"},
        )


@pytest.mark.asyncio
async def test_orchestrator_pausa_real_e_resume_via_runner_adk(monkeypatch):
    """Integration: pausa real + resume através do Runner ADK."""
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    # Substitui os 4 pipelines do orchestrator por um único stub.
    stub = _StubPausesOnce(name="qa_pipeline", description="stub")
    monkeypatch.setattr(
        _PipelineOrchestrator,
        "_pipelines",
        [stub],
    )

    orch = _PipelineOrchestrator(name="orchestrator", description="test")

    # T0: invoca via Runner externo
    outer_runner = Runner(
        app_name="orchestrator",
        agent=orch,
        artifact_service=None,
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
        credential_service=None,
    )
    outer_session = await outer_runner.session_service.create_session(
        app_name="orchestrator", user_id="u", state={},
    )

    msg_t0 = types.Content(role="user", parts=[types.Part.from_text(text="prompt inicial")])
    events_t0 = [e async for e in outer_runner.run_async(
        user_id="u", session_id=outer_session.id, new_message=msg_t0,
    )]

    # T0 deve ter emitido function_call long-running
    has_long_running = any(
        e.long_running_tool_ids for e in events_t0 if e.long_running_tool_ids
    )
    assert has_long_running, f"function_call long-running ausente em T0: {events_t0}"

    # State setado
    refreshed = await outer_runner.session_service.get_session(
        app_name="orchestrator", user_id="u", session_id=outer_session.id,
    )
    assert refreshed.state.get("paused_pipeline") == "qa_pipeline"
    assert outer_session.id in orch._live_runners

    # T1: envia "aprovar" como texto livre
    msg_t1 = types.Content(role="user", parts=[types.Part.from_text(text="aprovar")])
    events_t1 = [e async for e in outer_runner.run_async(
        user_id="u", session_id=outer_session.id, new_message=msg_t1,
    )]

    # T1 deve ter texto "decisao recebida: aprovar" do stub
    texts_t1 = [
        p.text for e in events_t1 if e.content
        for p in e.content.parts if p.text
    ]
    assert any("decisao recebida: aprovar" in t for t in texts_t1), (
        f"resume não chegou ao stub: {texts_t1}"
    )

    # State limpo
    refreshed = await outer_runner.session_service.get_session(
        app_name="orchestrator", user_id="u", session_id=outer_session.id,
    )
    assert refreshed.state.get("paused_pipeline") is None
    assert outer_session.id not in orch._live_runners

    await outer_runner.close()
```

- [ ] **Step 4: Rodar e ajustar se ADK tiver quirks**

Run:
```bash
.venv/bin/pytest tests/integration/test_hitl_e2e.py -v
```

Possíveis ajustes (não pré-determinados):
- Se `artifact_service=None` quebrar, passar `InMemoryArtifactService()`.
- Se `Part.from_function_response` na versão ADK exigir `id=` como kwarg, ajustar (já está manual no orchestrator).
- Se `session_service.get_session` requerer `await`, manter (já está).

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add adk/tests/integration/ adk/pyproject.toml
git commit -m "$(cat <<'EOF'
test: integration E2E do HITL no orchestrator (Runner ADK real + stub agent)

Valida pausa real via Event.long_running_tool_ids e resume via
function_response, sem mockar Runner. Cobertura complementa os unit
tests com a infra ADK genuína.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Validação manual + docs

### Task 9: Reproduzir o JSON do fotógrafo via dev-ui

**Files:** nenhum (validação manual)

- [ ] **Step 1: Subir o servidor**

Run (cwd = `adk/`):
```bash
.venv/bin/uvicorn app.main:app --reload --port 8081
```

Aguardar startup. Em outro terminal:

- [ ] **Step 2: Confirmar discoverable**

Run:
```bash
curl -s http://127.0.0.1:8081/list-apps | python3 -m json.tool | grep orchestrator
```

Expected: `"orchestrator"` listado.

- [ ] **Step 3: Abrir dev-ui e mandar o prompt do fotógrafo**

Abrir `http://127.0.0.1:8081/dev-ui/?app=orchestrator`. Colar o texto inicial do JSON da sessão (evento 0 do arquivo `Sou fotógrafo profissional...json`).

Aguardar até aparecer a mensagem de HITL ("Por favor, responda com 'aprovar', 'rejeitar' ou 'solicitar_ajustes'") — agora deve vir do call de `aguardar_aprovacao_humana`, não de texto-só do qa.

- [ ] **Step 4: Responder "aprovar"**

Digitar `aprovar` no input.

**Expected NOVO comportamento:**
- NÃO aparece `requirements_pipeline` / `design_pipeline` / `cr_*` agents (eles não rodam de novo)
- Aparecem eventos de `receber_requisitos_agent` ou geração de testes
- Eventualmente `executar_pytest_tool` é chamado
- `workspace_output/tests/inputs/` é populado

- [ ] **Step 5: Confirmar artefatos no filesystem**

Run:
```bash
ls -la adk/workspace_output/tests/inputs/
```

Expected: pasta existe e contém ao menos uma estrutura `<slug>/test_<slug>.py`.

Se algo falhar nesta task, NÃO commit nada. Voltar para Task 7 ou 8 com o problema descrito.

- [ ] **Step 6: Encerrar servidor**

`Ctrl-C` no terminal do uvicorn.

(Nenhum commit nesta task — é validação.)

---

### Task 10: Atualizar `CLAUDE.md` com a nova gotcha

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Ler a seção "Gotchas e lições do orchestrator E2E"**

Run:
```bash
grep -n "Gotchas e lições do orchestrator E2E" CLAUDE.md
```

Pegar o número de linha para localizar onde adicionar.

- [ ] **Step 2: Adicionar subseção**

Inserir após a subseção existente sobre HITL caveat, com o seguinte conteúdo:

```markdown
### HITL real no qa_pipeline (orchestrator v5)

Desde o spec `docs/superpowers/specs/2026-05-17-hitl-orchestrator-design.md`,
o `qa_pipeline` pausa nativamente via `LongRunningFunctionTool`
(`adk/src/agents/qa_agent/tools/hitl_tool.py`). Quando `action_planner`
retorna plano com `hitl_checkpoint.required=true`, o LLM do qa chama
`aguardar_aprovacao_humana(...)` — ADK emite `function_call` com
`long_running_tool_ids` e devolve controle ao runner.

O `_PipelineOrchestrator` (v5) detecta o evento, persiste `paused_pipeline`,
`paused_inner_session_id` e `paused_function_call` em `ctx.session.state`,
e mantém o `Runner` do qa_pipeline vivo em `self._live_runners[outer_sid]`.
Na próxima mensagem do usuário ("aprovar" / "rejeitar" / "solicitar_ajustes
<comentários>"), o orchestrator parseia o texto via `_parse_decision`,
embala em `function_response` com o `call_id` salvo, e envia ao runner
pausado — `qa_pipeline` retoma de onde parou.

**Limitações conhecidas (documentadas como follow-up):**
- `_live_runners` é in-process memory. Reinício do servidor entre T0
  (pausa) e T1 (resposta) perde o runner. O orchestrator detecta e
  devolve "Sessão HITL expirada — reenvie o prompt original" em vez
  de quebrar.
- Outros pipelines (`requirements_pipeline`, `design_pipeline`,
  `coding_review_pipeline`) ainda usam o padrão one-shot sem pausa.
  Quando algum deles bloqueia (ex: design por Doubt_Artifacts), apenas
  produz output incompleto e segue. Generalizar HITL fica para spec
  futuro.
- As tools antigas `create_hitl_checkpoint` e `register_human_validation`
  (em `qa_agent/tools/planner_tools.py`) ficam como audit trail.
  `aguardar_aprovacao_humana` é quem dirige o controle agora.

**Detecção em código:** `event.long_running_tool_ids: set[str] | None`
contém o `function_call.id`. Helper `_is_pending_long_running_call(part,
event)` em `orchestrator/_helpers.py`.

**Validação rápida do registro da tool:**
```bash
cd adk && .venv/bin/pytest tests/unit/test_workflow_qa_hitl.py -v
```
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: documenta HITL real no orchestrator v5 (CLAUDE.md gotchas)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review (executado ao terminar todas as tasks)

Após Task 10, conferir:

- [ ] **Cobertura do spec:** cada uma das 10 seções do spec tem task correspondente.
  - § 2 (Visão geral M1+M2+M3) → Tasks 1–7
  - § 3 (M1) → Tasks 1–3
  - § 4 (M2 estado + helpers) → Tasks 4–6, 7
  - § 5 (M3 _live_runners) → Task 7
  - § 6 (Fluxo end-to-end) → Task 8 (integration) + Task 9 (manual)
  - § 7 (Testes) → Tasks 1, 3, 4, 5, 6, 7, 8 cobrem U1–U9 + I1–I2
  - § 8 (Riscos) → mitigados nos próprios testes (U6 = servidor reiniciado, U7 = pausa encadeada)
  - § 9 (Critérios de aceite) → Task 9 valida #1–#6 manualmente; #7 (testes verdes) é Step 5 da Task 7
  - § 10 (Follow-ups) → Task 10 documenta na CLAUDE.md

- [ ] **Final sanity run:**

```bash
cd adk && .venv/bin/pytest tests/ -v --tb=short
```

Expected: tudo verde. Se houver flakes, rodar 2 vezes; se reproduzir, abrir issue antes de declarar concluído.

- [ ] **Git log limpo:**

```bash
git log --oneline -12
```

Expected: ~10 commits ordenados (Tasks 1–10, com Task 0 e 9 sem commit). Mensagens em prefixo correto (`add:`, `update:`, `test:`, `docs:`).

---

## Critérios de aceite (replay do spec § 9)

Validados nas tasks:

1. ✅ JSON do fotógrafo reproduzido com novo comportamento → Task 9
2. ✅ `workspace_output/tests/inputs/` populado → Task 9 Step 5
3. ✅ Nova sessão começa do zero → Task 7 (FRESH branch reseta `accumulated_outputs`; legacy `_live_runners` é fechado)
4. ✅ "rejeitar" / "solicitar_ajustes" param qa com Doubt + comments → Task 3 (instruction) + Task 7 (U4 testa)
5. ✅ Texto inválido devolve erro, mantém pausa → Task 7 (U5)
6. ✅ 128 unit tests existentes verdes → Task 3 Step 5, Task 7 Step 5
7. ✅ Novos testes verdes (U1–U9 + I1–I2) → Tasks 1, 4, 5, 6, 7, 8

---

## Resumo de commits esperados

| # | Prefixo | Resumo |
|---|---|---|
| 1 | `add:` | tool aguardar_aprovacao_humana |
| 2 | `add:` | re-export no qa_agent.tools |
| 3 | `add:` | LongRunningFunctionTool no workflow_qa + instruction |
| 4 | `add:` | helper _parse_decision |
| 5 | `add:` | helper _is_pending_long_running_call |
| 6 | `add:` | helpers de state/input/payload |
| 7 | `update:` | orchestrator v5 (FRESH+RESUME branches, _live_runners) |
| 8 | `test:` | integration E2E |
| 9 | (sem commit) | validação manual via dev-ui |
| 10 | `docs:` | CLAUDE.md gotchas |

Total: 9 commits. Cada um deve passar `pytest tests/unit` sem regressão.
