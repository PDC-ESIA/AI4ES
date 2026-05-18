# Fix Orchestrator Bugs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar 6 bugs reproduzidos no E2E do `orchestrator` de 2026-05-17, fazendo o SDLC produzir um app FastAPI rodável end-to-end com pytest verde e HITL acessível via REST.

**Architecture:** Mudanças não-invasivas: (1) 4 patches em prompts de agentes (`coder`, `requirements`, `markdown_specialist`, `action_planner`); (2) retry layer no `_PipelineOrchestrator._handle_fresh_run` para resposta vazia do LLM; (3) ajustes em `e2e.sh` / `run-agent.sh` / `stop-server.sh` para persistir SESSION_ID entre invocações e manter o servidor up quando HITL pausa; (4) script novo `verify-coder-output.sh` que valida o app gerado.

**Tech Stack:** Python 3.12, Google ADK, FastAPI, pytest, uv, bash, Gemini 2.5 Flash via GOOGLE_API_KEY.

**Spec:** `docs/superpowers/specs/2026-05-17-fix-orchestrator-bugs-design.md`

---

## File Structure

**Arquivos a CRIAR:**
- `adk/tests/unit/test_helpers_empty_detection.py` — unit test do `_is_empty_response`
- `adk/tests/unit/test_orchestrator_retry.py` — unit test do retry layer
- `.claude/skills/ai4es-e2e/scripts/verify-coder-output.sh` — valida o app gerado pelo coder

**Arquivos a MODIFICAR:**
- `adk/src/agents/orchestrator/_helpers.py` — adiciona `_is_empty_response` + `EMPTY_RETRY_PROMPT`
- `adk/src/agents/orchestrator/agent.py` — adiciona retry no `_handle_fresh_run`
- `adk/src/agents/coder/prompt.py` — contrato de estrutura de projeto Python
- `adk/src/agents/workflow_coding_review/agent.py` — espelha contrato em `_CODER_INSTRUCTION`
- `adk/src/agents/requirements/prompt.py` — tratamento de accumulated_outputs como read-only
- `adk/src/agents/markdown_specialist/prompt.py` — guardrail anti-empty
- `adk/src/agents/qa_agent/subagents/action_planner/prompt.py` — guardrail anti-empty
- `.claude/skills/ai4es-e2e/scripts/e2e.sh` — KEEP_UP=1 default + detecção HITL + persistência SESSION_ID
- `.claude/skills/ai4es-e2e/scripts/run-agent.sh` — usa SESSION_FILE para reuso de IDs
- `.claude/skills/ai4es-e2e/scripts/stop-server.sh` — limpa SESSION_FILE

Cada task abaixo é commit-sized (1 commit por task). Ordem importa apenas onde explicitamente notada nas dependências.

---

### Task 1: Helper `_is_empty_response` + `EMPTY_RETRY_PROMPT`

**Files:**
- Modify: `adk/src/agents/orchestrator/_helpers.py`
- Create: `adk/tests/unit/test_helpers_empty_detection.py`

- [ ] **Step 1: Write the failing test**

Criar `adk/tests/unit/test_helpers_empty_detection.py`:

```python
"""Testes da helper _is_empty_response (detecção de resposta vazia do LLM)."""

import pytest

from src.agents.orchestrator._helpers import _is_empty_response


def test_string_vazia_e_empty():
    assert _is_empty_response("") is True


def test_so_whitespace_e_empty():
    assert _is_empty_response("   ") is True
    assert _is_empty_response("\n\n") is True
    assert _is_empty_response("\t \n") is True


def test_none_e_empty():
    assert _is_empty_response(None) is True


def test_texto_real_nao_e_empty():
    assert _is_empty_response("ok") is False
    assert _is_empty_response("plan generated") is False


def test_json_curto_nao_e_empty():
    assert _is_empty_response("{}") is False


def test_texto_com_whitespace_lateral_nao_e_empty():
    assert _is_empty_response("  ok  ") is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd adk && .venv/bin/pytest tests/unit/test_helpers_empty_detection.py -v
```

Expected: `ImportError` ou `AttributeError` indicando que `_is_empty_response` não existe em `_helpers.py`.

- [ ] **Step 3: Add `_is_empty_response` + `EMPTY_RETRY_PROMPT` to `_helpers.py`**

Editar `adk/src/agents/orchestrator/_helpers.py`, adicionando no topo (após os imports):

```python
EMPTY_RETRY_PROMPT = (
    "Sua resposta anterior veio vazia. Por favor, reprocesse o pedido. "
    "Se não conseguir gerar um output útil, devolva um JSON ou texto curto "
    "explicando o bloqueio — NUNCA devolva string vazia."
)


def _is_empty_response(last_text) -> bool:
    """True quando o texto do LLM é vazio (None, "", ou só whitespace).

    Usado pelo orchestrator para detectar pipelines que devolveram nada
    e disparar retry uma vez antes de propagar falha.

    Args:
        last_text: Último texto acumulado do pipeline. Pode ser None,
            string vazia, whitespace, ou texto real.

    Returns:
        True se vazio (não-utilizável), False caso contrário.
    """
    if last_text is None:
        return True
    return not last_text.strip()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd adk && .venv/bin/pytest tests/unit/test_helpers_empty_detection.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/src/agents/orchestrator/_helpers.py adk/tests/unit/test_helpers_empty_detection.py
git commit -m "add: helper _is_empty_response + EMPTY_RETRY_PROMPT no orchestrator

Prepara retry layer (próxima task) para detectar resposta vazia do LLM
e disparar retry 1x antes de propagar como falha.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Retry layer no `_handle_fresh_run`

**Files:**
- Modify: `adk/src/agents/orchestrator/agent.py:188-266` (método `_handle_fresh_run`)
- Create: `adk/tests/unit/test_orchestrator_retry.py`

**Dependência:** Task 1 (precisa de `_is_empty_response` + `EMPTY_RETRY_PROMPT`).

- [ ] **Step 1: Write the failing tests**

Criar `adk/tests/unit/test_orchestrator_retry.py`:

```python
"""Testes do retry layer do _PipelineOrchestrator (bugs 1 e 2).

Quando um pipeline conclui com last_text vazio (sem pending_pause), o
orchestrator reinvoca o mesmo runner com EMPTY_RETRY_PROMPT uma vez
antes de propagar a falha. Estratégia: mockar Runner.run_async via
monkeypatch e contar invocações.
"""

from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.adk.events.event import Event
from google.genai import types


def _make_text_event(author: str, text: str) -> Event:
    return Event(
        author=author,
        invocation_id="inv-test",
        content=types.Content(role="model", parts=[types.Part(text=text)]),
    )


def _make_long_running_pause_event(author: str, call_id: str) -> Event:
    fc = types.FunctionCall(
        id=call_id,
        name="aguardar_aprovacao_humana",
        args={
            "checkpoint_id": "ck-1",
            "approval_question": "?",
            "allowed_decisions": ["aprovar", "rejeitar"],
        },
    )
    return Event(
        author=author,
        invocation_id="inv-test",
        content=types.Content(
            role="model", parts=[types.Part(function_call=fc)]
        ),
        long_running_tool_ids={call_id},
    )


class _FakeSession:
    def __init__(self, session_id: str = "inner-sid", user_id: str = "u"):
        self.id = session_id
        self.user_id = user_id


class _FakeSessionService:
    async def create_session(self, *, app_name, user_id, state):
        return _FakeSession()


def _make_recording_runner(
    sequences: list[list[Event]],
) -> tuple[MagicMock, list[dict]]:
    """Runner que retorna um seq de eventos por chamada e grava cada call.

    sequences[0] vai na 1ª chamada de run_async; sequences[1] na 2ª; etc.
    Retorna (runner, calls), onde `calls` é uma lista de dicts com os
    kwargs de cada invocação.
    """
    runner = MagicMock()
    runner.session_service = _FakeSessionService()
    runner.close = AsyncMock(return_value=None)
    calls: list[dict] = []
    seq_iter = iter(sequences)

    async def fake_run_async(**kwargs) -> AsyncGenerator[Event, None]:
        calls.append(kwargs)
        for e in next(seq_iter):
            yield e

    runner.run_async = fake_run_async
    return runner, calls


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


# --- R1: empty na 1ª invocação dispara retry, 2ª devolve texto válido ---


@pytest.mark.asyncio
async def test_empty_response_triggers_retry(monkeypatch):
    """Pipeline retorna empty na 1ª chamada; orchestrator chama 2ª vez."""
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    # 4 runners, um por pipeline. O 1º (requirements) emite empty na 1ª
    # chamada e texto válido na 2ª (após o EMPTY_RETRY_PROMPT).
    req_runner, req_calls = _make_recording_runner([
        [_make_text_event("requirements_pipeline", "")],   # 1ª: empty
        [_make_text_event("requirements_pipeline", "req-ok")],  # 2ª: ok
    ])
    runners_iter = iter([
        req_runner,
        _make_recording_runner([[_make_text_event("design_pipeline", "d")]])[0],
        _make_recording_runner([[_make_text_event("coding_review_pipeline", "c")]])[0],
        _make_recording_runner([[_make_text_event("qa_pipeline", "q")]])[0],
    ])
    monkeypatch.setattr(
        "src.agents.orchestrator.agent.Runner",
        lambda **kwargs: next(runners_iter),
    )

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    ctx = _FakeCtx("prompt inicial")

    _ = [e async for e in orch._run_async_impl(ctx)]

    # requirements runner foi chamado 2x (1 original + 1 retry)
    assert len(req_calls) == 2
    # Conteúdo da 2ª chamada deve ser o EMPTY_RETRY_PROMPT
    from src.agents.orchestrator._helpers import EMPTY_RETRY_PROMPT
    retry_msg = req_calls[1]["new_message"]
    retry_text = retry_msg.parts[0].text
    assert retry_text == EMPTY_RETRY_PROMPT


# --- R2: retry sucede → accumulated_outputs recebe o texto da 2ª ---


@pytest.mark.asyncio
async def test_retry_succeeds_then_propagates(monkeypatch):
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    req_runner, _ = _make_recording_runner([
        [_make_text_event("requirements_pipeline", "")],
        [_make_text_event("requirements_pipeline", "req-retry-ok")],
    ])
    runners_iter = iter([
        req_runner,
        _make_recording_runner([[_make_text_event("design_pipeline", "d")]])[0],
        _make_recording_runner([[_make_text_event("coding_review_pipeline", "c")]])[0],
        _make_recording_runner([[_make_text_event("qa_pipeline", "q")]])[0],
    ])
    monkeypatch.setattr(
        "src.agents.orchestrator.agent.Runner",
        lambda **kwargs: next(runners_iter),
    )

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    ctx = _FakeCtx("prompt inicial")
    _ = [e async for e in orch._run_async_impl(ctx)]

    accumulated = ctx.session.state["accumulated_outputs"]
    # primeiro item é (nome_pipeline, last_text). Esperamos last_text = retry ok
    names = [name for name, _ in accumulated]
    texts = dict(accumulated)
    assert "requirements_pipeline" in names
    assert texts["requirements_pipeline"] == "req-retry-ok"


# --- R3: duas empties consecutivas marcam falha ---


@pytest.mark.asyncio
async def test_double_empty_marks_failure(monkeypatch):
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    req_runner, _ = _make_recording_runner([
        [_make_text_event("requirements_pipeline", "")],
        [_make_text_event("requirements_pipeline", "")],
    ])
    runners_iter = iter([
        req_runner,
        _make_recording_runner([[_make_text_event("design_pipeline", "d")]])[0],
        _make_recording_runner([[_make_text_event("coding_review_pipeline", "c")]])[0],
        _make_recording_runner([[_make_text_event("qa_pipeline", "q")]])[0],
    ])
    monkeypatch.setattr(
        "src.agents.orchestrator.agent.Runner",
        lambda **kwargs: next(runners_iter),
    )

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    ctx = _FakeCtx("prompt inicial")
    _ = [e async for e in orch._run_async_impl(ctx)]

    texts = dict(ctx.session.state["accumulated_outputs"])
    assert "retornou empty após retry" in texts["requirements_pipeline"]


# --- R4: pending_pause NÃO dispara retry ---


@pytest.mark.asyncio
async def test_pending_pause_no_retry(monkeypatch):
    """qa emite pause; mesmo sem texto, orchestrator NÃO faz retry."""
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    pause_event = _make_long_running_pause_event("qa_pipeline", "call-1")
    qa_runner, qa_calls = _make_recording_runner([
        [pause_event],  # só pause, sem texto
    ])
    runners_iter = iter([
        _make_recording_runner([[_make_text_event("requirements_pipeline", "r")]])[0],
        _make_recording_runner([[_make_text_event("design_pipeline", "d")]])[0],
        _make_recording_runner([[_make_text_event("coding_review_pipeline", "c")]])[0],
        qa_runner,
    ])
    monkeypatch.setattr(
        "src.agents.orchestrator.agent.Runner",
        lambda **kwargs: next(runners_iter),
    )

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    ctx = _FakeCtx("prompt", session_id="outer-1")
    _ = [e async for e in orch._run_async_impl(ctx)]

    # qa runner foi chamado APENAS 1x (sem retry, porque pausa é sucesso)
    assert len(qa_calls) == 1
    assert ctx.session.state["paused_pipeline"] == "qa_pipeline"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd adk && .venv/bin/pytest tests/unit/test_orchestrator_retry.py -v
```

Expected: 4 tests fail — `R1/R2/R3` falham (orchestrator não faz retry hoje, então só 1 chamada por runner); `R4` provavelmente passa de graça (não há retry hoje). Pelo menos R1, R2, R3 vermelhos.

- [ ] **Step 3: Implement retry logic in `_handle_fresh_run`**

Editar `adk/src/agents/orchestrator/agent.py`. Adicionar import no topo (após os existentes de `_helpers`):

```python
from src.agents.orchestrator._helpers import (
    _build_function_response_payload,
    _build_input,
    _clear_pause_state,
    _extract_user_text,
    _is_empty_response,
    _is_pending_long_running_call,
    _parse_decision,
    _set_pause_state,
    EMPTY_RETRY_PROMPT,
)
```

Localizar o bloco no `_handle_fresh_run` (atualmente linhas 221–258). Está assim:

```python
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
                # ... bloco de pausa existente
```

Substituir por (adiciona o bloco de retry entre a 1ª invocação e o check `if pending_pause is not None`):

```python
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

            # RETRY: empty sem pausa = LLM falhou silenciosamente. Reinvoca 1x.
            if pending_pause is None and _is_empty_response(last_text):
                retry_content = types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=EMPTY_RETRY_PROMPT)],
                )
                last_text = ""
                async for event in runner.run_async(
                    user_id=inner_session.user_id,
                    session_id=inner_session.id,
                    new_message=retry_content,
                ):
                    yield event
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                last_text = part.text
                            elif _is_pending_long_running_call(part, event):
                                pending_pause = part.function_call

                if _is_empty_response(last_text) and pending_pause is None:
                    last_text = (
                        f"[orchestrator] pipeline {pipeline.name} "
                        "retornou empty após retry"
                    )

            if pending_pause is not None:
                # ... bloco de pausa existente (não muda)
```

- [ ] **Step 4: Run retry tests to verify they pass**

```bash
cd adk && .venv/bin/pytest tests/unit/test_orchestrator_retry.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Run existing orchestrator tests to verify no regression**

```bash
cd adk && .venv/bin/pytest tests/unit/test_orchestrator_hitl.py tests/unit/test_orchestrator_helpers.py tests/unit/test_workflow_qa_hitl.py -v
```

Expected: todos passam (sem regressão no HITL existente).

- [ ] **Step 6: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/src/agents/orchestrator/_helpers.py adk/src/agents/orchestrator/agent.py adk/tests/unit/test_orchestrator_retry.py
git commit -m "add: retry 1x quando pipeline devolve resposta vazia

Bugs 1 e 2 (markdown_specialist e action_planner retornando empty) são
não-determinísticos do Gemini. O retry layer no _handle_fresh_run reinvoca
o mesmo Runner com EMPTY_RETRY_PROMPT uma vez antes de propagar falha.

Limites:
- 1 retry, não loop infinito
- Só no fresh_run; resume HITL não dispara retry
- pending_pause não é tratado como empty (pausa = sucesso)
- Empty após retry → string sintética em accumulated_outputs

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Guardrail anti-empty no `markdown_specialist`

**Files:**
- Modify: `adk/src/agents/markdown_specialist/prompt.py`

- [ ] **Step 1: Locate the end of the `instruction` string**

```bash
grep -n '^"""$\|instruction = """' adk/src/agents/markdown_specialist/prompt.py | head -5
```

A última `"""` que fecha o `instruction` é o ponto de inserção.

- [ ] **Step 2: Add guardrail block before the closing `"""`**

Editar `adk/src/agents/markdown_specialist/prompt.py`. Antes da linha que fecha `instruction` com `"""`, inserir o bloco:

```
PROTOCOLO ANTI-EMPTY (OBRIGATÓRIO):
PROIBIDO devolver resposta vazia ao pipeline pai. Se você não conseguir gerar o
relatório por qualquer motivo (input inválido, ferramenta indisponível, dúvida
sobre formato), gere um artefato com sufixo `_BLOCKED.md` via save_artifact
explicando o motivo, e retorne ao pipeline o caminho absoluto desse arquivo.
NUNCA devolva string vazia — isso quebra o protocolo de filename passing do
workflow_design_pipeline e termina a pipeline em estado indeterminado.

Exemplo de filename de bloqueio: `relatorio_HU-001_BLOCKED.md` com conteúdo
explicativo curto.
```

- [ ] **Step 3: Verify syntax (Python import OK)**

```bash
cd adk && .venv/bin/python -c "from src.agents.markdown_specialist import prompt; print(len(prompt.instruction), 'chars')"
```

Expected: imprime um número (sem `SyntaxError`).

- [ ] **Step 4: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/src/agents/markdown_specialist/prompt.py
git commit -m "update: guardrail anti-empty no markdown_specialist (bug 1)

Quando o markdown_specialist falha em gerar relatório, agora deve persistir
um arquivo _BLOCKED.md em vez de devolver string vazia. Combinado com o
retry layer (commit anterior), reduz a chance de design_pipeline travar
silenciosamente no protocolo de filename passing.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Guardrail anti-empty no `action_planner`

**Files:**
- Modify: `adk/src/agents/qa_agent/subagents/action_planner/prompt.py`

**Nota:** A variável do prompt neste arquivo se chama `SYSTEM_PROMPT` (verificado: `SYSTEM_PROMPT = """..."""`), não `instruction`.

- [ ] **Step 1: Locate the closing `"""` of `SYSTEM_PROMPT`**

```bash
grep -n 'SYSTEM_PROMPT\|^"""$' adk/src/agents/qa_agent/subagents/action_planner/prompt.py | head -5
```

A última `"""` na sequência é o ponto de inserção.

- [ ] **Step 2: Add guardrail block before the closing `"""`**

Editar `adk/src/agents/qa_agent/subagents/action_planner/prompt.py`. Antes do fechamento `"""` de `SYSTEM_PROMPT`, inserir:

```
PROTOCOLO ANTI-EMPTY (OBRIGATÓRIO):
PROIBIDO devolver resposta vazia. O retorno DEVE ser sempre um JSON válido
com campos `tipo_entrada` e `lifecycle.status`. Se você não conseguir planejar
(input incompleto, contexto faltando, dúvida sobre escopo), devolva o JSON de
bloqueio:

{
  "tipo_entrada": "indefinido",
  "modo": "indefinido",
  "tools": [],
  "casos_de_teste_propostos": [],
  "lifecycle": {
    "status": "bloqueado",
    "execution_allowed": false,
    "next_step": "aguardar_resolucao_humana"
  },
  "erro": "<motivo curto: o que está faltando ou ambíguo>"
}

NUNCA devolva string vazia — o pipeline qa interpreta isso como falha
não-recuperável e gera Doubt_Artifact espúrio (QA-PLANNING-BLOCK-001),
mesmo quando o problema é resolvível com retry.
```

- [ ] **Step 3: Verify syntax**

```bash
cd adk && .venv/bin/python -c "from src.agents.qa_agent.subagents.action_planner import prompt; print(len(prompt.SYSTEM_PROMPT), 'chars')"
```

Expected: imprime número (sem `SyntaxError`).

- [ ] **Step 4: Verify the action_planner agent still loads**

```bash
cd adk && .venv/bin/python -c "from src.agents.qa_agent.subagents.action_planner.agent import agent; print('agent loaded:', agent.name)"
```

Expected: imprime `agent loaded: action_planner` ou nome similar.

- [ ] **Step 5: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/src/agents/qa_agent/subagents/action_planner/prompt.py
git commit -m "update: guardrail anti-empty no action_planner (bug 2)

Força o action_planner a sempre devolver JSON com lifecycle.status — JSON
de bloqueio explícito em vez de string vazia. Evita QA-PLANNING-BLOCK-001
espúrio quando o problema é resolvível por retry do orchestrator.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Tratamento de `accumulated_outputs` no `requirements/prompt.py`

**Files:**
- Modify: `adk/src/agents/requirements/prompt.py`

**Nota:** `workflow_coding_review/agent.py:65` usa `req_prompt.instruction` diretamente — então editar só `requirements/prompt.py` cobre o `requirements` top-level **e** o `cr_requirements_agent`. Nenhuma alteração necessária em `workflow_coding_review/agent.py` para esta task.

- [ ] **Step 1: Localize the end of the `instruction` string**

```bash
grep -n 'instruction = "\|^"""$' adk/src/agents/requirements/prompt.py | tail -5
```

- [ ] **Step 2: Add accumulated_outputs guidance before closing `"""`**

Editar `adk/src/agents/requirements/prompt.py`. Antes do fechamento `"""` do `instruction`, inserir:

```
TRATAMENTO DO CONTEXTO DE FASES ANTERIORES (CRÍTICO):
Quando o input contém o bloco "CONTEXTO DAS FASES ANTERIORES" ou "Output de
<pipeline>:", esse trecho é HISTÓRICO READ-ONLY — saída de pipelines que já
rodaram antes de você (requirements_pipeline, design_pipeline, etc.).

NÃO trate esse histórico como:
- Pedido para re-analisar requisitos (eles já foram gerados na fase anterior).
- Motivo para gerar Doubt_Artifact (falhas em outras fases NÃO são da sua
  responsabilidade).
- Instrução de ação (você só atua sobre o pedido inicial do usuário no topo
  do input, ANTES do bloco de contexto).

Se TODO o input for apenas contexto de fases anteriores (sem novo pedido do
usuário no topo), responda com um resumo curto reconhecendo o status e devolva
um JSON com listas vazias para todos os campos — NÃO gere Doubt_Artifact e
NÃO duplique requisitos já gerados.
```

- [ ] **Step 3: Verify syntax**

```bash
cd adk && .venv/bin/python -c "from src.agents.requirements import prompt; print('instr len:', len(prompt.instruction))"
```

Expected: número, sem erro.

- [ ] **Step 4: Verify both consumers still load**

```bash
cd adk && .venv/bin/python -c "
from src.agents.requirements.agent import agent as r
from src.agents.workflow_coding_review.agent import agent as cr
print('requirements ok:', r.name)
print('coding_review ok:', cr.name)
"
```

Expected: ambos imprimem nomes.

- [ ] **Step 5: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/src/agents/requirements/prompt.py
git commit -m "update: tratamento de accumulated_outputs como read-only (bug 3)

Resolve Doubt_Artifact_D-001 espúrio: cr_requirements_agent (que herda este
prompt via req_prompt.instruction) deixa de interpretar 'design_pipeline
falhou' do accumulated_outputs como pedido para re-analisar requisitos.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Contrato de estrutura no `_CODER_INSTRUCTION`

**Files:**
- Modify: `adk/src/agents/workflow_coding_review/agent.py:80-116` (string `_CODER_INSTRUCTION`)
- Modify: `adk/src/agents/coder/prompt.py` (espelhar contrato no prompt original do coder top-level)

**Por que dois arquivos:** o `cr_coder_agent` em `workflow_coding_review/agent.py` usa `_CODER_INSTRUCTION` próprio (não herda de `coder/prompt.py`). O agente `coder` top-level usa `coder/prompt.py`. Ambos precisam do contrato.

- [ ] **Step 1: Update `_CODER_INSTRUCTION` block in workflow_coding_review**

Em `adk/src/agents/workflow_coding_review/agent.py`, localizar o bloco `# DIRETRIZES` dentro de `_CODER_INSTRUCTION` (linhas 96-106). Substituir o item `2. **Estrutura de projeto** ...` (atualmente linhas 98-104) por:

```python
2. **ESTRUTURA OBRIGATÓRIA DE PROJETO PYTHON** (para app FastAPI/Flask/CLI):
   - Raiz do workspace contém: `requirements.txt`, `conftest.py` (vazio basta), `pyproject.toml` opcional.
   - Pacote principal em `app/` com `app/__init__.py` (vazio) e `app/main.py`.
   - Testes em `tests/` com `tests/__init__.py` (vazio) e `tests/test_*.py`.
   - Imports de teste SEMPRE absolutos a partir da raiz (`from app.main import app`), nunca `from main import app`.
   - Sem `__init__.py` na raiz do workspace.
   - Para CLI/script único: dispense `app/`, mas mantenha `tests/__init__.py` e `conftest.py` na raiz.

   Os arquivos `__init__.py` e `conftest.py` são OBRIGATÓRIOS mesmo vazios — sem eles, `pytest` falha
   em coletar testes com erro `ModuleNotFoundError: No module named 'app'`. Crie-os explicitamente
   via `tool_criar_arquivo`.

   Estrutura padrão para apps FastAPI:
   - `app/models.py` (SQLAlchemy ou Pydantic) — se aplicável
   - `app/routers/<recurso>.py` (rotas por recurso) — se aplicável
   - `app/templates/*.html` (Jinja2) — se aplicável
```

- [ ] **Step 2: Mirror contract in coder/prompt.py**

Editar `adk/src/agents/coder/prompt.py`. Localizar a seção de diretrizes / estrutura (similar ao `_CODER_INSTRUCTION`) e adicionar a mesma cláusula sobre `__init__.py` e `conftest.py` se ainda não estiver lá. Se o prompt já fala em estrutura mas omite `__init__.py`, adicionar uma sub-seção:

```
ARQUIVOS OBRIGATÓRIOS PARA PYTEST COLETAR TESTES:
- `app/__init__.py` (vazio basta) — torna `app` pacote importável
- `tests/__init__.py` (vazio basta) — torna `tests` pacote
- `conftest.py` na raiz (vazio basta) — pytest usa para detectar rootdir

Sem esses 3 arquivos, pytest falha com `ModuleNotFoundError: No module named 'app'`
ao executar `tests/test_*.py` que importam `from app.main import app`. Crie-os SEMPRE
que entregar um projeto Python testável.
```

- [ ] **Step 3: Verify syntax of both files**

```bash
cd adk && .venv/bin/python -c "
from src.agents.workflow_coding_review.agent import agent as cr
from src.agents.coder.agent import agent as c
print('coding_review:', cr.name, '| coder:', c.name)
"
```

Expected: ambos imprimem nomes.

- [ ] **Step 4: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/src/agents/workflow_coding_review/agent.py adk/src/agents/coder/prompt.py
git commit -m "update: contrato de estrutura Python obrigatória no coder (bugs 4+5)

Força criação de app/__init__.py, tests/__init__.py e conftest.py para que
pytest colete testes (resolve ModuleNotFoundError reproduzido no E2E de
2026-05-17). Padroniza layout app/+tests/ para reduzir não-determinismo
entre runs.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Persistência de SESSION_ID em `run-agent.sh`

**Files:**
- Modify: `.claude/skills/ai4es-e2e/scripts/run-agent.sh`

- [ ] **Step 1: Edit run-agent.sh to source SESSION_FILE**

Em `.claude/skills/ai4es-e2e/scripts/run-agent.sh`, localizar as linhas que definem `USER_ID` e `SESSION_ID` (atualmente linha 47):

```bash
USER_ID="${USER_ID:-u_$(date +%s)}"
SESSION_ID="${SESSION_ID:-s_$(date +%s%N)}"
```

Substituir por:

```bash
SESSION_FILE="${SESSION_FILE:-/tmp/ai4es-current-session.env}"
if [ -f "${SESSION_FILE}" ]; then
  # shellcheck disable=SC1090
  source "${SESSION_FILE}"
fi
USER_ID="${USER_ID:-u_$(date +%s)}"
SESSION_ID="${SESSION_ID:-s_$(date +%s%N)}"
printf 'SESSION_ID=%s\nUSER_ID=%s\n' "${SESSION_ID}" "${USER_ID}" > "${SESSION_FILE}"
export SESSION_ID USER_ID
```

- [ ] **Step 2: Test SESSION_FILE round-trip**

```bash
rm -f /tmp/ai4es-current-session.env
# 1ª invocação: gera novos IDs e grava
SESSION_FILE=/tmp/test-session.env bash -c '
SESSION_FILE="${SESSION_FILE:-/tmp/ai4es-current-session.env}"
if [ -f "${SESSION_FILE}" ]; then source "${SESSION_FILE}"; fi
USER_ID="${USER_ID:-u_$(date +%s)}"
SESSION_ID="${SESSION_ID:-s_$(date +%s%N)}"
printf "SESSION_ID=%s\nUSER_ID=%s\n" "${SESSION_ID}" "${USER_ID}" > "${SESSION_FILE}"
echo "RUN1: SID=$SESSION_ID UID=$USER_ID"
'
# 2ª invocação: reusa
SESSION_FILE=/tmp/test-session.env bash -c '
SESSION_FILE="${SESSION_FILE:-/tmp/ai4es-current-session.env}"
if [ -f "${SESSION_FILE}" ]; then source "${SESSION_FILE}"; fi
USER_ID="${USER_ID:-u_$(date +%s)}"
SESSION_ID="${SESSION_ID:-s_$(date +%s%N)}"
echo "RUN2: SID=$SESSION_ID UID=$USER_ID"
'
rm -f /tmp/test-session.env
```

Expected: RUN1 e RUN2 imprimem **o mesmo** `SID=` e `UID=`.

- [ ] **Step 3: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add .claude/skills/ai4es-e2e/scripts/run-agent.sh
git commit -m "update: run-agent.sh persiste SESSION_ID/USER_ID em /tmp (bug 6)

Permite que a segunda invocação do run-agent.sh (resposta ao HITL) reuse
o mesmo outer_session_id, batendo no branch RESUME do _PipelineOrchestrator
em vez do branch FRESH RUN.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: KEEP_UP=1 default + detecção HITL em `e2e.sh`

**Files:**
- Modify: `.claude/skills/ai4es-e2e/scripts/e2e.sh`

**Dependência:** Task 7 (run-agent.sh já persiste SESSION_FILE).

- [ ] **Step 1: Change KEEP_UP default and capture run output**

Editar `.claude/skills/ai4es-e2e/scripts/e2e.sh`. Substituir:

```bash
KEEP_UP="${KEEP_UP:-}"
```

por:

```bash
KEEP_UP="${KEEP_UP:-1}"
```

E garantir que o `run-agent.sh` herda SESSION_FILE no mesmo escopo. Adicionar logo após `PORT="${PORT:-8081}"`:

```bash
# Sessão persistente entre invocações (resposta ao HITL reusa o ID).
SESSION_FILE="${SESSION_FILE:-/tmp/ai4es-current-session.env}"
export SESSION_FILE
```

- [ ] **Step 2: Replace single-pipe run with captured output + HITL detection**

Localizar o bloco atual (no fim do script):

```bash
PORT="${PORT}" bash "${SCRIPT_DIR}/run-agent.sh" "${APP}" "${PROMPT_FILE}" | \
  "${SCRIPT_DIR}/pretty-response.py"

echo ""
echo "===================="
echo "Output em: ./workspace_output/"
echo "Doubts pendentes: find . -name 'Doubt_Artifact*.md' 2>/dev/null"
echo "===================="

if [ "${KEEP_UP}" != "1" ]; then
  echo ""
  PORT="${PORT}" bash "${SCRIPT_DIR}/stop-server.sh"
fi
```

Substituir por:

```bash
RUN_OUTPUT=$(PORT="${PORT}" bash "${SCRIPT_DIR}/run-agent.sh" "${APP}" "${PROMPT_FILE}")
echo "${RUN_OUTPUT}" | "${SCRIPT_DIR}/pretty-response.py"

echo ""
echo "===================="
echo "Output em: ./workspace_output/"
echo "Doubts pendentes: find . -name 'Doubt_Artifact*.md' 2>/dev/null"
echo "===================="

PAUSED_PIPELINE=$(echo "${RUN_OUTPUT}" | python3 -c "
import json, sys
try:
    events = json.load(sys.stdin)
    for ev in events:
        actions = ev.get('actions') or {}
        delta = actions.get('state_delta') or {}
        if delta.get('paused_pipeline'):
            print(delta['paused_pipeline']); break
except Exception:
    pass
" 2>/dev/null)

if [ -n "${PAUSED_PIPELINE}" ]; then
  echo ""
  echo "🔶 [HITL] Pipeline pausado: ${PAUSED_PIPELINE}"
  echo "   Servidor MANTIDO em :${PORT} para você responder."
  echo "   Para retomar:"
  echo "     echo 'aprovar' | bash ${SCRIPT_DIR}/run-agent.sh ${APP}"
  echo "     (ou 'rejeitar' / 'solicitar_ajustes <comentários>')"
  echo "   Quando terminar: bash ${SCRIPT_DIR}/stop-server.sh"
  exit 0
fi

if [ "${KEEP_UP}" != "1" ]; then
  echo ""
  PORT="${PORT}" bash "${SCRIPT_DIR}/stop-server.sh"
else
  echo ""
  echo "✓ Pipeline completou. Servidor permanece em :${PORT} (KEEP_UP=1)."
  echo "  Para parar: bash ${SCRIPT_DIR}/stop-server.sh"
fi
```

- [ ] **Step 3: Bash syntax check**

```bash
bash -n .claude/skills/ai4es-e2e/scripts/e2e.sh && echo "SYNTAX OK"
```

Expected: `SYNTAX OK`.

- [ ] **Step 4: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add .claude/skills/ai4es-e2e/scripts/e2e.sh
git commit -m "update: e2e.sh KEEP_UP=1 default + detecção HITL (bug 6)

Servidor permanece up após pipeline pausar no HITL. Mensagem 🔶 [HITL]
explica como retomar via 'aprovar'/'rejeitar'/'solicitar_ajustes'. Sem
isso, _live_runners morre junto com uvicorn e a sessão fica órfã.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Cleanup de SESSION_FILE em `stop-server.sh`

**Files:**
- Modify: `.claude/skills/ai4es-e2e/scripts/stop-server.sh`

- [ ] **Step 1: Add SESSION_FILE removal**

Editar `.claude/skills/ai4es-e2e/scripts/stop-server.sh`. Antes do `if pkill...`, adicionar:

```bash
SESSION_FILE="${SESSION_FILE:-/tmp/ai4es-current-session.env}"
rm -f "${SESSION_FILE}"
```

O arquivo completo deve ficar assim:

```bash
#!/usr/bin/env bash
# Mata uvicorn na porta indicada. Idempotente.
set -euo pipefail
PORT="${PORT:-8081}"
SESSION_FILE="${SESSION_FILE:-/tmp/ai4es-current-session.env}"
rm -f "${SESSION_FILE}"
if pkill -f "uvicorn.*--port ${PORT}" 2>/dev/null; then
  echo "Uvicorn na porta ${PORT} foi finalizado."
else
  echo "Nenhum uvicorn na porta ${PORT}."
fi
```

- [ ] **Step 2: Bash syntax check**

```bash
bash -n .claude/skills/ai4es-e2e/scripts/stop-server.sh && echo "SYNTAX OK"
```

Expected: `SYNTAX OK`.

- [ ] **Step 3: Round-trip test**

```bash
printf 'SESSION_ID=test\nUSER_ID=test\n' > /tmp/ai4es-current-session.env
bash .claude/skills/ai4es-e2e/scripts/stop-server.sh
test ! -f /tmp/ai4es-current-session.env && echo "SESSION_FILE removido OK"
```

Expected: `SESSION_FILE removido OK`.

- [ ] **Step 4: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add .claude/skills/ai4es-e2e/scripts/stop-server.sh
git commit -m "update: stop-server.sh limpa SESSION_FILE (bug 6)

Garante que a próxima invocação de e2e.sh começa com sessão fresh,
sem reusar IDs órfãos de runs anteriores.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Script `verify-coder-output.sh`

**Files:**
- Create: `.claude/skills/ai4es-e2e/scripts/verify-coder-output.sh`

- [ ] **Step 1: Create the script**

Criar `.claude/skills/ai4es-e2e/scripts/verify-coder-output.sh` com conteúdo:

```bash
#!/usr/bin/env bash
# Valida o app gerado pelo coder em workspace_output/coder/:
#   1. snapshot para /tmp (init_workspace apaga workspace_output a cada run)
#   2. uv venv + uv pip install -r requirements.txt
#   3. pytest -q tests/ (verde = bug 4 corrigido)
#   4. uvicorn sobe e responde GET /healthcheck com {"status": "ok"}
#
# Uso: bash verify-coder-output.sh [coder_dir]

set -euo pipefail

CODER_DIR="${1:-adk/workspace_output/coder}"
DEST="/tmp/coder-verify-$(date +%s)"
APP_PORT="${APP_PORT:-8090}"

if [ ! -d "${CODER_DIR}" ]; then
  echo "ERRO: Coder workspace não encontrado: ${CODER_DIR}" >&2
  exit 1
fi

echo "==> Snapshot ${CODER_DIR} → ${DEST}"
cp -r "${CODER_DIR}" "${DEST}"
cd "${DEST}"

echo "==> Criando venv (python 3.12)"
uv venv --python 3.12 --quiet

echo "==> Instalando requirements.txt"
if [ ! -f requirements.txt ]; then
  echo "ERRO: requirements.txt não encontrado em ${DEST}" >&2
  exit 1
fi
VIRTUAL_ENV="${DEST}/.venv" uv pip install -q -r requirements.txt

echo "==> Rodando pytest"
set +e
.venv/bin/pytest -q tests/
PYTEST_EXIT=$?
set -e

echo "==> Subindo uvicorn em :${APP_PORT}"
.venv/bin/uvicorn app.main:app --port "${APP_PORT}" >/tmp/coder-verify-uvicorn.log 2>&1 &
UVICORN_PID=$!
sleep 2

RESPONSE=$(curl -sf "http://127.0.0.1:${APP_PORT}/healthcheck" 2>/dev/null || echo "FAIL")
kill "${UVICORN_PID}" 2>/dev/null || true
wait "${UVICORN_PID}" 2>/dev/null || true

echo ""
echo "===================="
echo "RESULTADO"
echo "===================="
echo "pytest exit: ${PYTEST_EXIT}"
echo "endpoint response: ${RESPONSE}"
echo "snapshot em: ${DEST}"

if [ "${PYTEST_EXIT}" = "0" ] && echo "${RESPONSE}" | grep -q '"status":"ok"'; then
  echo "✓ Coder output verificado (pytest verde + endpoint responde)"
  exit 0
else
  echo "❌ Verification failed" >&2
  exit 1
fi
```

- [ ] **Step 2: Make executable**

```bash
chmod +x .claude/skills/ai4es-e2e/scripts/verify-coder-output.sh
```

- [ ] **Step 3: Bash syntax check**

```bash
bash -n .claude/skills/ai4es-e2e/scripts/verify-coder-output.sh && echo "SYNTAX OK"
```

Expected: `SYNTAX OK`.

- [ ] **Step 4: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add .claude/skills/ai4es-e2e/scripts/verify-coder-output.sh
git commit -m "add: verify-coder-output.sh valida o app gerado pelo coder

Script encapsula o ciclo manual de:
  snapshot → venv → pip install → pytest → uvicorn → curl

Verde = bugs 4 e 5 corrigidos (app rodável end-to-end). Cumpre feedback
do usuário 'testar app gerado antes de declarar pronto'.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Validação E2E final + verificação do app gerado

**Files:** nenhum (verificação manual end-to-end, sem commits a menos que se descubra regressão).

**Dependência:** Tasks 1–10 completas e commitadas.

- [ ] **Step 1: Reset clean state**

```bash
cd /home/hhiroshi92/github/AI4ES
bash .claude/skills/ai4es-e2e/scripts/stop-server.sh
rm -rf adk/workspace_output/
```

Expected: workspace limpo, sem uvicorn rodando.

- [ ] **Step 2: Run diagnose to confirm no schema regressions**

```bash
bash .claude/skills/ai4es-e2e/scripts/diagnose.sh
```

Expected: `✓ DIAGNOSE OK`.

- [ ] **Step 3: Run full E2E**

```bash
bash .claude/skills/ai4es-e2e/scripts/e2e.sh .claude/skills/ai4es-e2e/examples/healthcheck-prompt.md 2>&1 | tee /tmp/ai4es-e2e-post-fix.log
```

Expected:
- Script completa sem erro (exit 0).
- Mensagem final: `✓ Pipeline completou. Servidor permanece em :8081 (KEEP_UP=1).` OU `🔶 [HITL] Pipeline pausado: qa_pipeline` (ambos são sucesso).

- [ ] **Step 4: Validate workspace artifacts (7 critérios do spec D.2)**

```bash
cd /home/hhiroshi92/github/AI4ES
# 1. requirements populado
ls adk/workspace_output/requirements/RFs/ | head
# 2. design/reports não-vazio
find adk/workspace_output/design/reports -type f | head
# 3. design/validation não-vazio
find adk/workspace_output/design/validation -type f | head
# 4. zero Doubt_Artifact_D-001 em requirements
test -z "$(find adk/workspace_output/requirements -name 'Doubt_Artifact_D-001*' 2>/dev/null)" && echo "✓ sem D-001"
# 5. coder com __init__.py + conftest.py
ls adk/workspace_output/coder/app/__init__.py adk/workspace_output/coder/tests/__init__.py adk/workspace_output/coder/conftest.py
# 6. zero QA-PLANNING-BLOCK-001
test -z "$(find adk/workspace_output/tests/inputs/doubt_artifacts -name '*QA-PLANNING-BLOCK*' 2>/dev/null)" && echo "✓ sem QA-PLANNING-BLOCK"
```

Expected: critérios 1, 5 listam arquivos; critérios 4 e 6 imprimem `✓`. Critérios 2 e 3 (design/reports e design/validation) podem estar vazios se o LLM ainda travou — neste caso passar para Step 5.

- [ ] **Step 5: If design empty, run E2E once more (rule out flakiness)**

```bash
bash .claude/skills/ai4es-e2e/scripts/stop-server.sh
rm -rf adk/workspace_output/
bash .claude/skills/ai4es-e2e/scripts/e2e.sh .claude/skills/ai4es-e2e/examples/healthcheck-prompt.md
ls adk/workspace_output/design/reports adk/workspace_output/design/validation
```

Se mesmo na 2ª execução `design/reports` ou `design/validation` ficam vazios, é regressão real — investigar (provavelmente retry layer não disparou; rodar `tail -100 /tmp/ai4es-uvicorn-8081.log` para ver). Se passa na 2ª, é flakiness residual a documentar (item 5 do §7 do spec).

- [ ] **Step 6: Run verify-coder-output.sh**

```bash
bash .claude/skills/ai4es-e2e/scripts/verify-coder-output.sh
```

Expected: `✓ Coder output verificado (pytest verde + endpoint responde)`. Se falhar, o coder ainda não está obedecendo ao contrato A.1 — investigar prompt e ajustar.

- [ ] **Step 7: Stop server and cleanup**

```bash
bash .claude/skills/ai4es-e2e/scripts/stop-server.sh
```

- [ ] **Step 8: Update memory if anything surprising surfaced**

Se algum bug novo apareceu (não previsto neste plan), salvar memória nova em `/home/hhiroshi92/.claude/projects/-home-hhiroshi92-github-AI4ES/memory/` seguindo o padrão de `feedback_*.md` ou `project_*.md`. Se o E2E passou limpo, atualizar `project_orchestrator_sdlc_state.md` registrando que os 6 bugs foram fechados em 2026-05-17.

- [ ] **Step 9: Final commit (apenas se atualizou memória)**

Nada para commit no repo se Steps 4 e 6 passaram limpos — a evidência fica em `/tmp/ai4es-e2e-post-fix.log`. Os commits relevantes (Tasks 1–10) já foram feitos.

---

## Verification commands cheat-sheet

```bash
# Unit tests
cd adk && .venv/bin/pytest tests/unit/test_helpers_empty_detection.py tests/unit/test_orchestrator_retry.py -v

# Regression on existing tests
cd adk && .venv/bin/pytest tests/unit/test_orchestrator_hitl.py tests/unit/test_orchestrator_helpers.py tests/unit/test_workflow_qa_hitl.py -v

# Full E2E + verify
bash .claude/skills/ai4es-e2e/scripts/diagnose.sh
bash .claude/skills/ai4es-e2e/scripts/e2e.sh .claude/skills/ai4es-e2e/examples/healthcheck-prompt.md
bash .claude/skills/ai4es-e2e/scripts/verify-coder-output.sh
```
