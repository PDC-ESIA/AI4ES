# Design — HITL real no orchestrator SDLC (qa_pipeline com `LongRunningFunctionTool`)

**Data:** 2026-05-17
**Status:** Proposta
**Autor:** Hugo Hiroshi (via brainstorming)
**Branch alvo:** `feature/code/1-initial-project-setup`
**Relacionado:**
- `docs/superpowers/specs/2026-05-16-orchestrator-sdlc-design.md` (orchestrator v3)
- `docs/superpowers/specs/2026-05-17-sdlc-gaps-fixes-design.md` (fechamento de gaps; observa caveat HITL como pré-existente)
- `CLAUDE.md` — seção "Gotchas e lições do orchestrator E2E"
- Sessão exemplo: `Sou fotógrafo profissional (retratos e casament....json` (eventos 42–53 evidenciam o bug)

---

## 1. Contexto

Em 2026-05-17 o usuário executou o `orchestrator` com um prompt de site de fotografia. A sessão exportada (54 eventos) mostra o padrão:

1. `requirements_pipeline` → `design_pipeline` → `coding_review_pipeline` rodaram normalmente.
2. `qa_pipeline` → `action_planner` retornou um plano com `hitl_checkpoint.required=true` (evento 41).
3. O LLM do `qa_pipeline` imprimiu (evento 42) "Por favor, responda com 'aprovar', 'rejeitar' ou 'solicitar_ajustes'".
4. O usuário respondeu `aprovar` (evento 43, `invocationId=e-9583895a-...`, diferente do `e-83539535-...` que estava "pausado").
5. **Todos os 4 pipelines reiniciaram do zero** (eventos 44–53), cada um pedindo contexto novo. `qa_pipeline` produziu um Doubt Artifact "QA_Pipeline_Bloqueado_Sem_Artefatos".

### Causa-raiz

Três problemas compostos:

**P1 — HITL é só prosa no prompt.** A tool `create_hitl_checkpoint` em `adk/src/agents/qa_agent/tools/planner_tools.py:450-505` é `FunctionTool` síncrono. Retorna `{"status": "awaiting_human_validation", "checkpoint_id": "..."}` mas não pausa nada: o LLM apenas imprime a pergunta no output final. ADK trata isso como turno normal e encerra a sessão.

**P2 — `_PipelineOrchestrator` é stateless por construção.** Em `adk/src/agents/orchestrator/agent.py:56-127`:
- Linha 60-65: lê apenas `ctx.user_content` (última mensagem)
- Linha 71: itera **sempre** todos os 4 pipelines
- Linha 99: cria `InMemorySessionService()` **novo** por pipeline, descartado após cada `runner.close()` (linha 125)
- Nada é persistido em `ctx.session.state`

**P3 — Sessões internas morrem ao fim do loop.** Mesmo se o orchestrator quisesse "voltar" para o `qa_pipeline`, o `session_service` que continha o turno do `action_planner` já foi descartado.

Consequência: quando o usuário digita "aprovar", o orchestrator trata como nova conversa. Cada pipeline vê apenas a string "aprovar" e pede contexto novamente. `register_human_validation` (que existe em `planner_tools.py:508-550`) nunca é chamado porque o `checkpoint_id` se perdeu junto com a sessão.

### Não-escopo (decidido no brainstorm)

- **Revisitar fases concluídas.** O usuário escolheu "snapshot textual" — outputs de pipelines anteriores ficam como string em `accumulated_outputs`. Não há rota para "refazer só o design".
- **HITL em pipelines além do `qa_pipeline`.** O `design_pipeline` no JSON terminou com saída incompleta (mensagem "identificou lacunas"), mas não pausou — produziu um output final e seguiu. Generalizar HITL para os outros pipelines fica para um spec separado.
- **Cap de contexto / sliding window.** Só uma sessão fica viva por vez (a do pipeline pausado). O `qa_pipeline` típico tem ~3 turnos antes da pausa e ~5–10 depois — longe do 1M do Gemini.
- **Mudanças no dev-ui ou na REST API.** Usuário continua mandando texto livre ("aprovar", "rejeitar", "solicitar_ajustes [comentários]").
- **Persistência DB-backed das sessões.** `_live_runners` continua em memória do processo Python. Reinício do servidor entre T0 e T1 perde o estado — mesma limitação do v3. Documentar como follow-up.
- **Substituir `create_hitl_checkpoint` / `register_human_validation`.** Ficam como audit trail (LLM ainda pode chamar para registro), sem driver de controle.

---

## 2. Visão geral da solução

Três mudanças coordenadas em um único PR:

| # | O que muda | Onde |
|---|---|---|
| M1 | Nova tool long-running `aguardar_aprovacao_humana` | `qa_agent/tools/hitl_tool.py` (novo), `qa_agent/tools/__init__.py`, `workflow_qa/agent.py` |
| M2 | Orchestrator com `ctx.session.state` + routing | `orchestrator/agent.py` |
| M3 | Sessão do pipeline pausado preservada entre invocações | atributo `_live_runners` no `_PipelineOrchestrator` |

Resumo do contrato novo: quando o `action_planner` devolve um plano com `hitl_checkpoint.required=true`, o LLM do `qa_pipeline` chama `aguardar_aprovacao_humana(...)`. ADK emite `function_call` event marcado como `long_running` e devolve controle ao runner sem auto-resposta. O `_PipelineOrchestrator` detecta esse evento pendente no stream, salva o estado em `ctx.session.state` e mantém o `Runner`/`InMemorySessionService` desse pipeline vivo em `self._live_runners[outer_session_id]`. Na próxima invocação do orchestrator (T1), com `state.paused_pipeline` setado, o texto do usuário é parseado em `(decision, comments)`, embalado em `function_response` com o `call_id` salvo, e enviado ao runner vivo via `runner.run_async`. O `qa_pipeline` retoma exatamente de onde parou.

---

## 3. M1 — Tool long-running `aguardar_aprovacao_humana`

### M1.1 — Função base

Novo arquivo: `adk/src/agents/qa_agent/tools/hitl_tool.py`

```python
"""Tool de pausa HITL para o qa_pipeline.

Empacotada como LongRunningFunctionTool no workflow_qa/agent.py. Quando o
LLM chama esta função, o ADK emite um function_call event sem auto-resposta,
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
        a etapa 2 (geração de testes).

    Args:
        checkpoint_id: Identificador do checkpoint criado por create_hitl_checkpoint.
        approval_question: Texto literal da pergunta a ser exibida ao humano.
        allowed_decisions: Lista de decisões aceitáveis (ex.: ["aprovar", "rejeitar", "solicitar_ajustes"]).
        pause_reason: Motivo opcional da pausa (mostrado ao humano para contexto).

    Returns:
        dict com {decision, comments, reviewer, validated_at} após o humano
        responder. `decision` está em `allowed_decisions`.

    Comportamento ADK:
        Esta função é embrulhada em LongRunningFunctionTool. ADK marca o
        function_call como long_running, devolve controle, e injeta o
        function_response no próximo turno do mesmo invocation.
    """
    # Corpo nunca é executado em tempo de invocação real — o ADK pausa antes.
    # Retorno aqui só serve de tipagem / fallback em testes unitários que
    # chamam a função diretamente sem passar pelo runner.
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

**Convenções (CLAUDE.md):**
- Parâmetro opcional usa `Optional[str]` (não `str | None`) por compat com Gemini API.
- Docstring GOOD: propósito + quando usar + Args + Returns.

### M1.2 — Re-export

`adk/src/agents/qa_agent/tools/__init__.py` ganha:

```python
from .hitl_tool import aguardar_aprovacao_humana
```

E `__all__` ganha `"aguardar_aprovacao_humana"`.

### M1.3 — Registro no `workflow_qa`

`adk/src/agents/workflow_qa/agent.py`:

```python
from google.adk.tools import FunctionTool, LongRunningFunctionTool

from src.agents.qa_agent.tools.hitl_tool import aguardar_aprovacao_humana
# ... outros imports inalterados ...

agent = LlmAgent(
    # ... config inalterada ...
    tools=[
        AgentTool(agent=action_planner_agent),
        AgentTool(agent=receber_requisitos_agent),
        AgentTool(agent=code_fix_agent),
        FunctionTool(executar_pytest_tool),
        FunctionTool(DoubtArtifactGenerator.generate),
        LongRunningFunctionTool(aguardar_aprovacao_humana),  # <-- novo
    ],
)
```

### M1.4 — Atualização do `instruction` do `qa_pipeline`

Inserção na etapa 1 do `_INSTRUCTION` em `workflow_qa/agent.py`:

```
1. PLANEJAMENTO
   Encaminhe a entrada ao action_planner_agent.
   Aguarde o plano de ação: tipos de teste, dependências, pontos de
   validação humana (HITL) e relatório de compliance preliminar.

   → Se o plano tiver `hitl_checkpoint.required=true`:
        CHAME OBRIGATORIAMENTE a tool `aguardar_aprovacao_humana`
        passando checkpoint_id, approval_question, allowed_decisions e
        pause_reason extraídos do plano. NÃO emita texto pedindo
        aprovação — a tool faz a pausa. Quando a tool retornar, leia
        `decision`:
          - "aprovar"           → prossiga para a etapa 2.
          - "rejeitar"          → encerre com Doubt_Artifact citando
                                  comments, sem gerar testes.
          - "solicitar_ajustes" → encerre devolvendo comments ao
                                  solicitante, sem gerar testes.
```

A convenção "prompts não citam tools" do CLAUDE.md tem uma exceção registrada para `aguardar_aprovacao_humana` aqui: o nome literal precisa aparecer porque o LLM precisa identificar a tool exata a chamar quando o action_planner emite o sinal de HITL — o vocabulário de capacidade ("pausar até decisão humana") sozinho não desambigua o suficiente para garantir o caminho correto.

---

## 4. M2 — Orchestrator com estado em `ctx.session.state`

### M2.1 — Schema de estado

`ctx.session.state` (sessão **externa**, do orchestrator, persistida pelo runner que chama o orchestrator) ganha quatro chaves:

```python
{
    "accumulated_outputs": [                       # list[tuple[str, str]]
        ("requirements_pipeline", "<último texto>"),
        ("design_pipeline", "<último texto>"),
        ("coding_review_pipeline", "<último texto>"),
    ],
    "paused_pipeline": "qa_pipeline",              # str | None
    "paused_inner_session_id": "<uuid>",           # str | None
    "paused_function_call": {                      # dict | None
        "id": "<call_id ADK>",
        "name": "aguardar_aprovacao_humana",
        "args": {"checkpoint_id": "...", "allowed_decisions": [...], ...},
    },
}
```

Schema invariants:
- `paused_pipeline`, `paused_inner_session_id`, `paused_function_call` são todos `None` OU todos preenchidos. Estados parciais são bug.
- `accumulated_outputs` cresce monotonicamente até a conclusão do `qa_pipeline`; depois disso é resetado se o usuário enviar nova mensagem que não case com nenhum estado pausado (próxima conversa SDLC).

### M2.2 — `_live_runners` (atributo de instância, não persistido)

```python
class _PipelineOrchestrator(BaseAgent):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    _pipelines: ClassVar[List[BaseAgent]] = [...]  # inalterado

    # Novo: runners do pipeline pausado por outer_session. NÃO é state
    # persistido — vive na memória do processo orchestrator. Reinício
    # do servidor entre T0 e T1 perde isto (documentado como limitação).
    _live_runners: dict[str, tuple[Runner, str]] = {}  # outer_sid → (runner, inner_sid)
```

Para suportar `arbitrary_types_allowed` com `dict` mutável de instância, declarar via `PrivateAttr` do Pydantic ou usar `__init__` que atribui explicitamente. Detalhe de implementação fica no plano.

### M2.3 — Loop principal reescrito

Pseudocódigo (`_run_async_impl`):

```python
async def _run_async_impl(self, ctx):
    state = ctx.session.state
    outer_sid = ctx.session.id
    user_text = _extract_user_text(ctx)
    if not user_text:
        return

    paused = state.get("paused_pipeline")

    # --- Branch RESUME ---
    if paused:
        runner_handle = self._live_runners.get(outer_sid)
        if runner_handle is None:
            # Servidor reiniciou entre T0 e T1. Limpa state, sinaliza erro.
            _clear_pause_state(state)
            yield _build_error_event(
                "Sessão HITL expirada (servidor foi reiniciado). "
                "Por favor reenvie o prompt original."
            )
            return

        runner, inner_sid = runner_handle
        call = state["paused_function_call"]
        allowed = call["args"]["allowed_decisions"]

        try:
            decision, comments = _parse_decision(user_text, allowed)
        except ValueError as exc:
            yield _build_error_event(
                f"Decisão inválida: {exc}. "
                f"Por favor responda com: {', '.join(allowed)}."
            )
            return  # mantém pausa intacta

        function_response = types.Content(
            role="user",
            parts=[types.Part.from_function_response(
                name=call["name"],
                response={
                    "decision": decision,
                    "comments": comments,
                    "reviewer": "usuario",
                    "validated_at": datetime.now(timezone.utc).isoformat(),
                    "checkpoint_id": call["args"]["checkpoint_id"],
                },
                id=call["id"],
            )],
        )

        last_text, new_pause = "", None
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
                        new_pause = (event, part)

        if new_pause:
            # qa_pipeline pausou de novo (improvável, mas possível em
            # iteração código→teste). Persiste novo state e mantém runner.
            _set_pause_state(state, paused, inner_sid, new_pause[1].function_call)
            return

        # qa_pipeline terminou. Cleanup.
        _clear_pause_state(state)
        accumulated = state.get("accumulated_outputs", [])
        accumulated.append((paused, last_text))
        state["accumulated_outputs"] = accumulated
        await runner.close()
        self._live_runners.pop(outer_sid, None)
        return

    # --- Branch FRESH RUN ---
    state["accumulated_outputs"] = []
    accumulated = []

    for pipeline in self._pipelines:
        pipeline_input = _build_input(user_text, accumulated)
        content = types.Content(role="user", parts=[types.Part.from_text(text=pipeline_input)])

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

        last_text, pending_pause = "", None
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

        if pending_pause:
            # Salva estado, MANTÉM runner vivo (não fecha).
            self._live_runners[outer_sid] = (runner, inner_session.id)
            state["paused_pipeline"] = pipeline.name
            state["paused_inner_session_id"] = inner_session.id
            state["paused_function_call"] = {
                "id": pending_pause.id,
                "name": pending_pause.name,
                "args": dict(pending_pause.args or {}),
            }
            state["accumulated_outputs"] = accumulated
            return  # NÃO roda pipelines subsequentes; aguarda T1

        # Pipeline concluiu sem pausa.
        accumulated.append((pipeline.name, last_text))
        await runner.close()

    state["accumulated_outputs"] = accumulated
```

### M2.4 — Helpers

`_extract_user_text(ctx) -> str` — junta `ctx.user_content.parts[*].text` (mesma lógica do atual).

`_build_input(user_text, accumulated) -> str` — mantém formato atual (`"{user_text}\n\n---\nCONTEXTO DAS FASES ANTERIORES:\n..."`).

`_is_pending_long_running_call(part, event) -> bool`:
```python
def _is_pending_long_running_call(part, event) -> bool:
    """True quando o event tem function_call long-running pendente.

    Detecção: event.long_running_tool_ids existe e contém part.function_call.id,
    OU (fallback) event.partial=False E function_call sem function_response
    matching no mesmo turn.
    """
    if not part.function_call:
        return False
    ids = getattr(event, "long_running_tool_ids", None)
    if ids and part.function_call.id in ids:
        return True
    return False
```

Plano vai validar a forma exata do evento ADK contra a versão instalada (`google-adk` pinada em `pyproject.toml`).

`_parse_decision(user_text, allowed) -> tuple[str, str]`:
```python
def _parse_decision(text: str, allowed: list[str]) -> tuple[str, str]:
    """'aprovar com cuidado em X' → ('aprovar', 'com cuidado em X').

    Normaliza: lowercase, strip, primeiro token. Falha levanta ValueError.
    """
    stripped = text.strip()
    if not stripped:
        raise ValueError("texto vazio")
    parts = stripped.split(None, 1)
    first = parts[0].lower().rstrip(",.;:!?")
    rest = parts[1] if len(parts) > 1 else ""

    # Match exato ou prefixo (ex: "aprov" → "aprovar")
    for opt in allowed:
        opt_lower = opt.lower()
        if first == opt_lower or opt_lower.startswith(first):
            return opt_lower, rest
    raise ValueError(f"'{first}' não casa com {allowed}")
```

`_clear_pause_state(state)` e `_set_pause_state(state, name, sid, fc)` — helpers simétricos.

---

## 5. M3 — Manutenção da sessão do pipeline pausado

Já coberto em M2.3 (atributo `_live_runners`). Pontos importantes:

1. **`InMemorySessionService()` é criado por pipeline na FRESH RUN.** Ao pausar, o orchestrator NÃO chama `runner.close()` — mantém a referência em `_live_runners`. O `session_service` interno fica com o histórico completo do turno do `action_planner`.

2. **No RESUME, `runner.run_async` recebe `new_message=function_response`** com o mesmo `session_id` (inner) que estava pausado. ADK reconhece o `function_response` como continuação do `function_call` pendente e injeta no contexto do LLM.

3. **`runner.close()` no fim do RESUME** libera recursos. `_live_runners.pop(outer_sid, None)` limpa a referência.

4. **Pausas encadeadas**: se durante o RESUME o `qa_pipeline` chamar `aguardar_aprovacao_humana` de novo (cenário hipotético — autocorrect ciclo 2 querendo confirmação humana), o mesmo runner permanece vivo, só atualiza `paused_function_call` em state.

---

## 6. Fluxo end-to-end (replay da sessão do fotógrafo)

```
[T0] User envia "Sou fotógrafo profissional (retratos e casamentos)..."
     Orchestrator (FRESH RUN):
       requirements_pipeline roda → accumulated += ("requirements_pipeline", "Resumo...")
       design_pipeline roda → accumulated += ("design_pipeline", "design_architect identificou lacunas...")
       coding_review_pipeline roda (cr_requirements + cr_coder + cr_review)
         → accumulated += ("coding_review_pipeline", "{status: APROVADO, ...}")
       qa_pipeline roda:
         action_planner returns plan with hitl_checkpoint.required=true
         qa LLM chama aguardar_aprovacao_humana(
           checkpoint_id="abc",
           approval_question="Você aprova a execução do plano de QA...",
           allowed_decisions=["aprovar", "rejeitar", "solicitar_ajustes"],
           pause_reason="Pipeline de design bloqueada por Doubt_Artifacts...",
         )
         ADK emite event com function_call long-running pendente
       Orchestrator detecta pending_pause:
         _live_runners[outer_sid] = (qa_runner, qa_inner_sid)
         state.paused_pipeline = "qa_pipeline"
         state.paused_function_call = {id, name, args}
         state.accumulated_outputs = [(req, ...), (design, ...), (cr, ...)]
       Return

[T1] User envia "aprovar"
     Orchestrator (RESUME branch):
       paused_pipeline="qa_pipeline", runner_handle=(qa_runner, qa_inner_sid) ✓
       _parse_decision("aprovar", ["aprovar","rejeitar","solicitar_ajustes"])
         → ("aprovar", "")
       function_response_content = types.Part.from_function_response(
         id="<call_id>",
         name="aguardar_aprovacao_humana",
         response={decision:"aprovar", comments:"", reviewer:"usuario", ...},
       )
       qa_runner.run_async(session_id=qa_inner_sid, new_message=function_response_content)
       qa_pipeline LLM lê resposta da tool:
         decision="aprovar" → prossegue para etapa 2 do _INSTRUCTION
         → receber_requisitos_agent → testes gerados em workspace_output/tests/
         → executar_pytest_tool → relatório
         → (eventualmente) code_fix_agent ou entrega final
       qa_pipeline emite mensagem final
       Orchestrator: pending_pause=None
         accumulated += ("qa_pipeline", "Resumo: {total, sucessos, ...}")
         qa_runner.close()
         _live_runners.pop(outer_sid)
         _clear_pause_state(state)
       Return
```

---

## 7. Testes

### 7.1 Unit (`adk/tests/unit/test_orchestrator_hitl.py`, novo)

Mock dos `Runner`s internos (não roda LLM real):

| # | Caso | Verifica |
|---|---|---|
| U1 | FRESH RUN sem pausa | Todos os 4 pipelines rodam; `accumulated_outputs` tem 4 entradas; state.paused_pipeline is None |
| U2 | FRESH RUN com pausa no qa | Pipelines 1–3 rodam; qa pausa; state.paused_pipeline="qa_pipeline"; `_live_runners[outer_sid]` existe; nenhum pipeline após qa roda |
| U3 | RESUME "aprovar" → conclusão | function_response enviado com `decision="aprovar"`; pipeline conclui; state limpa; `_live_runners` limpa |
| U4 | RESUME "rejeitar com motivo X" | `_parse_decision` → ("rejeitar", "com motivo X"); function_response.response.comments="com motivo X" |
| U5 | RESUME com texto inválido ("oi") | Yield error event; state.paused_pipeline mantido; `_live_runners` mantido |
| U6 | RESUME sem `_live_runners` (servidor reiniciou) | Yield error event "Sessão HITL expirada"; state limpo |
| U7 | RESUME → pausa encadeada | Novo `paused_function_call` salvo; runner mantido vivo |
| U8 | `_parse_decision` exato vs prefixo | "aprovar", "Aprovar", "aprov", "APROVAR." todas casam com "aprovar" |
| U9 | `_is_pending_long_running_call` | Detecta via `event.long_running_tool_ids`; ignora function_call não-long-running |

### 7.2 Integration (`adk/tests/integration/test_hitl_e2e.py`, novo)

Roda orchestrator real via `Runner` com agentes reais (LLM stub via fixture, OU com `gemini-2.5-flash` real marcado `@pytest.mark.live`):

- I1: Envia prompt curto que força HITL → coleta eventos → confirma function_call long-running emitido → verifica `state.paused_pipeline`
- I2: Em seguida envia "aprovar" → confirma que `receber_requisitos_agent` foi invocado depois (pelo nome de evento) → confirma que state foi limpo

### 7.3 Manual E2E

Reproduzir o JSON do fotógrafo:
1. `uvicorn app.main:app --reload --port 8081`
2. Dev-UI → `orchestrator` → prompt do fotógrafo (mesmo texto da sessão exportada)
3. Aguardar a pergunta de HITL aparecer (mesmo evento 42)
4. Responder `aprovar`
5. **Confirmar**: aparece atividade do `receber_requisitos_agent` (não dos `requirements_pipeline` / `design_pipeline` / `cr_*`); `workspace_output/tests/inputs/` é populado.

### 7.4 Regressão

- 128 testes unit existentes permanecem verdes
- E2E healthcheck-prompt (skill `ai4es-e2e`) continua passando

---

## 8. Riscos & mitigação

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| LLM esquece de chamar `aguardar_aprovacao_humana` quando action_planner sinaliza HITL | Média | Alto (regressão para o estado atual) | Prompt explícito com nome literal da tool; teste I1 valida a sequência |
| Versão de `google-adk` não tem `long_running_tool_ids` no evento | Baixa | Alto (detecção falha silenciosamente) | Plano valida shape do evento via teste U9 antes de escrever orchestrator |
| `_live_runners` vaza memória (sessões abandonadas) | Média | Médio | TTL: ao detectar nova FRESH RUN em outer_sid que tem `_live_runners` legado, fecha o runner antigo antes |
| Reinício do servidor entre T0 e T1 | Baixa em dev, alta em prod | Médio | Error event explícito em U6; documentar como follow-up DB-backed |
| `_parse_decision` interpreta mal "aprovar parcial" como "aprovar" | Baixa | Médio | Casos U4/U8 cobrem prefixos; comentários preservados pra revisão humana posterior |
| Pausa durante FRESH RUN dispara antes de qa (p.ex. design chama long-running tool inesperada) | Muito baixa | Médio | Plano só registra `LongRunningFunctionTool` no `workflow_qa` por hora; teste U2 garante que detecção bate em qa especificamente |

---

## 9. Critérios de aceite

1. ✅ Reproduzir o JSON do fotógrafo: após responder "aprovar", o `qa_pipeline` continua para `receber_requisitos_agent` em vez de reiniciar todos os pipelines.
2. ✅ `workspace_output/tests/inputs/` populado ao fim do fluxo (não vazio).
3. ✅ Nova sessão de orchestrator (outer_session diferente) começa do zero, sem contaminação do state anterior.
4. ✅ "rejeitar" e "solicitar_ajustes" param o `qa_pipeline` com Doubt Artifact e devolvem comments ao solicitante.
5. ✅ Texto livre inválido ("ok", "sim", "oi") devolve mensagem de erro mantendo a pausa ativa.
6. ✅ 128 testes unit + healthcheck E2E permanecem verdes.
7. ✅ Novos testes (U1–U9 + I1–I2) verdes.

---

## 10. Follow-ups (fora deste design)

- HITL em `design_pipeline` quando bloqueado por Doubt_Artifacts (hoje só imprime e segue).
- Persistência DB-backed para sobreviver reinício do servidor entre T0 e T1.
- Cap de contexto / sliding window para sessões que ficam vivas em casos extremos (múltiplas pausas encadeadas).
- Generalizar `_PipelineOrchestrator` para um `BaseHITLOrchestrator` reusável (pipeline-agnostic).
- Aposentar `create_hitl_checkpoint` / `register_human_validation` quando o audit trail migrar para o function_response da nova tool.
