# Evolução do Orquestrador SDLC — Resumo por Time

> **Data de consolidação:** 2026-05-20
> **PR alvo:** #267 — `feature/code/1-initial-project-setup` → `develop`
> **Público:** Tech leads dos Times 1 (Requisitos), 2 (Design), 3 (Testes) e 4 (Codificação)

Este documento descreve, **por Time SWEBOK**, as melhorias entregues no orquestrador (`adk/src/agents/orchestrator/`) durante o trabalho desta PR. Cada seção é independente cada tech lead pode ler apenas o bloco correspondente.


---

## Estado atual do orquestrador (TL;DR)

O `orchestrator` é o **ponto único de entrada do SDLC**. Hoje compõe **4 pipelines em sequência**, com sessões isoladas e HITL real no QA:

```
requirements_pipeline → design_pipeline → coding_review_pipeline → qa_pipeline
       (Time 1)             (Time 2)             (Time 4)              (Time 3)
```

| Subpasta de `workspace_output/` | Time responsável | Status |
|---|---|---|
| `requirements/` (HUs, RFs, RNFs, RNs, Glossario) | Time 1 | ✅ populado |
| `design/` + `design/diagrams/` + `design/reports/` + `design/validation/` | Time 2 | ✅ populado |
| `coder/` (backend + tests + requirements.txt) | Time 4 | ✅ populado |
| `review/verificacao_revisao.md` | Time 4 | ✅ populado |
| `tests/inputs/` + `<slug>/test_<slug>.py` | Time 3 | ✅ populado (após resposta a HITL) |

**Cobertura de testes:** 25 arquivos unit + 1 integration em `adk/tests/`. ~128 testes verdes.

---

## Time 1 — Requisitos

### O que o Time entrega hoje no orquestrador

O `requirements_pipeline` (workflow `workflow_requirements`) processa o pedido do usuário e persiste HUs, RFs, RNFs, RNs e Glossário em `workspace_output/requirements/`. Quando bloqueado, emite `Doubt_Artifact` no mesmo workspace. O `requirements_agent` agora delega o glossário ao `glossario_agent` interno.

### Melhorias aplicadas

1. **Workspace isolation real** (antes os artefatos do Time 1 caíam no repo principal em `docs/Time_1_Requisitos/HUs/`, `RFs/` etc.).
   - `tool_salvar_artefato_requisito(tipo, id_req, conteudo_md, base_dir: Optional[str] = None)` em `adk/shared/tools/filesystem.py:266` — assinatura ganhou `base_dir`.
   - `gerar_doubt_artifact(..., base_dir: Optional[str] = None)` em `adk/shared/tools/doubt_generator_analista.py:17` — `caminho_base` renomeado para `base_dir` com default `None`.
   - Ambas adicionadas a `_FILESYSTEM_TOOL_NAMES` em `adk/shared/agent_factory.py` → `_bind_tool_to_workspace` aplica `functools.partial(..., base_dir=...)` automaticamente.
   - Bind manual em `adk/src/agents/requirements/agent.py` e `adk/src/agents/workflow_coding_review/agent.py` (que não usam `create_se_agent`).

2. **Prompts limpos de identificadores de tool** (`requirements/prompt.py` e `glossario_agent`). O LLM agora orienta-se por **verbos de capacidade** (ex.: "persistir o artefato no repositório de requisitos") e a fonte de verdade sobre cada tool é a docstring (`FunctionDeclaration.description`). 

3. **Tratamento de `accumulated_outputs` como read-only** no `cr_requirements_agent`. Antes ele lia o output das fases anteriores ("Output de design_pipeline: ...falhou") e gerava `Doubt_Artifact_D-001` (bloqueante) achando que precisava re-analisar. Agora o prompt instrui: "histórico read-only — NÃO trate como pedido para re-analisar nem gere Doubt_Artifact por falhas de outras fases".

### Cobertura de testes

- `adk/tests/unit/test_filesystem_base_dir.py` — `tool_salvar_artefato_requisito` com/sem `base_dir`, validação anti-traversal.
- `adk/tests/unit/test_doubt_generator_base_dir.py` — `gerar_doubt_artifact` com/sem `base_dir`, fallback legado.
- `adk/tests/unit/test_agent_factory_workspace.py` — `_FILESYSTEM_TOOL_NAMES` reconhece as novas tools.

### Pendências do Time 1

- `tool_salvar_artefato_requisito` ainda hardcoda subpastas (`HUs/`, `RFs/`, `RNFs/`, `RNs/`). Padronizar com `AGENT_DIRS` (`adk/shared/workspace.py`) fica para spec futuro.
- Few-shots em `adk/src/agents/requirements/few_shot.py` podem ainda citar nomes de tool — auditar e migrar para vocabulário de capacidade.

---

## Time 2 — Design

### O que o Time entrega hoje no orquestrador

O `design_pipeline` (workflow `workflow_design_pipeline`) é um `LlmAgent` orquestrador que delega aos 5 especialistas (`design_architect`, `mermaid_specialist`, `markdown_specialist`, `validator`, `io_agent`). Persiste em `workspace_output/design/` (análise), `design/diagrams/` (.mmd), `design/reports/` (relatórios .md) e `design/validation/`. O pipeline foi **adicionado ao orquestrador** entre `requirements_pipeline` e `coding_review_pipeline` — antes estava de fora por causa de um "bug interno conhecido" nunca investigado.

### Melhorias aplicadas

1. **Diagnóstico do bug que mantinha o Time 2 fora do orquestrador.** Investigação em `docs/superpowers/research/2026-05-17-design-pipeline-bug.md` — classificação: **token overflow no sub-agente por inline_content**. O `markdown_specialist` passava o relatório COMPLETO como string inline em `request=` ao `io_agent` via `AgentTool`. Resultado: `gemini-2.5-flash` retornava `{"result": ""}` silenciosamente (não emite `MALFORMED_FUNCTION_CALL` porque não há JSON parcial). O pipeline detectava como falha do passo 3, pulava `validator` e encerrava com `"falha"`.

2. **Fix do bug do `design_pipeline`** — abordagem conservadora (bypass do `io_agent` intermediário):
   - Adicionar `save_artifact`, `list_staging_files`, `current_date` (de `shared/tools/design_*`) DIRETAMENTE ao `tools=[...]` dos 3 especialistas (`design_architect`, `mermaid_specialist`, `markdown_specialist`).
   - Reescrever o `PASSO 4 — PERSISTÊNCIA E ENCAMINHAMENTO` em cada prompt para chamar `save_artifact(filename=, conteudo=)` direto, em vez de proxiar via `io_agent`.
   - Resultado: elimina um salto de LLM e metade da pressão de output token. O `io_agent` permanece útil para leituras (`read_file`).

3. **Workspace binding dos 5 especialistas.** Migração de `LlmAgent` direto → `create_se_agent(..., agent_subdir=...)` para cada um, com o subdiretório certo em `AGENT_DIRS`:

   | Especialista | `agent_subdir` | Subpasta resultante |
   |---|---|---|
   | `design_architect` | `"design"` | `workspace_output/design/` |
   | `mermaid_specialist` | `"mermaid_specialist"` | `workspace_output/design/diagrams/` |
   | `markdown_specialist` | `"markdown_specialist"` | `workspace_output/design/reports/` |
   | `validator` | `"validator"` | `workspace_output/design/validation/` |
   | `io_agent` | `"io_agent"` | `workspace_output/design/staging/` |

4. **`design_pipeline` adicionado ao orquestrador.** `adk/src/agents/orchestrator/agent.py:57-62`:
   ```python
   _pipelines: ClassVar[List[BaseAgent]] = [
       requirements_pipeline,
       design_pipeline,         # NOVO — entre requirements e coding_review
       coding_review_pipeline,
       qa_pipeline,
   ]
   ```

5. **Guardrail anti-empty no `markdown_specialist`.** Prompt instrui: "PROIBIDO devolver resposta vazia. Se não conseguir gerar o relatório, gere um artefato `_BLOCKED.md` via `save_artifact`. NUNCA devolva string vazia — quebra o protocolo de filename passing do `workflow_design_pipeline`".

6. **Prompt do `io_agent`** limpo de identificadores literais de tool.

### Cobertura de testes

- `adk/tests/unit/test_orchestrator_design.py` — confirma 4 pipelines na ordem correta.
- `adk/tests/unit/test_design_workspace_binding.py` — `functools.partial.keywords` dos 5 especialistas.

### Pendências do Time 2

- Convenção "prompts não citam tools" parcialmente violada em `design_architect`, `mermaid_specialist`, `markdown_specialist` — `save_artifact`, `list_staging_files`, `io_agent.read_file` aparecem nominalmente. Foi necessário no diagnóstico imperativo do token overflow. **Decisão pendente**: reescrever em capacidade ou documentar exceção formal.
- Relatórios muito grandes (>50 HUs) ainda podem reincidir o token overflow. Solução definitiva exige streaming de SAVE incremental ou `append_artifact` no `io_agent` — fora desta entrega.
- HITL real ainda não existe no `design_pipeline` (hoje só imprime mensagem e segue). Generalizar HITL para os 3 pipelines não-QA é spec futuro.

---

## Time 3 — Testes

### O que o Time entrega hoje no orquestrador

O `qa_pipeline` (workflow `workflow_qa`) recebe os artefatos do Time 4 e gera/executa testes pytest. Persiste JSONs de input em `workspace_output/tests/inputs/<slug>.json` e código de testes em `workspace_output/tests/<slug>/test_<slug>.py`. Pausa de verdade via **HITL real** antes de gerar testes (quando o `action_planner` sinaliza `hitl_checkpoint.required=true`).

### Melhorias aplicadas

1. **HITL real (`LongRunningFunctionTool`).** Antes o HITL era prosa: `create_hitl_checkpoint` retornava `{"status":"awaiting_human_validation"}` mas não pausava — o LLM imprimia "responda com aprovar/rejeitar" e ADK encerrava a sessão. Quando o usuário respondia `aprovar`, os 4 pipelines reiniciavam do zero.
   - Nova tool `aguardar_aprovacao_humana` em `adk/src/agents/qa_agent/tools/hitl_tool.py`, registrada como `LongRunningFunctionTool` em `adk/src/agents/workflow_qa/agent.py`. ADK marca o `function_call` como long-running e devolve controle ao runner sem auto-resposta.
   - Instrução do `qa_pipeline` atualizada: se `action_planner` retornar plano com `hitl_checkpoint.required=true`, OBRIGATORIAMENTE chamar `aguardar_aprovacao_humana` (única exceção registrada à convenção "prompts não citam tools" — o LLM precisa identificar a tool exata).
   - `create_hitl_checkpoint` / `register_human_validation` ficam como audit trail; não dirigem mais o controle.

2. **Sanitização do vazamento `pass<ctrl63>`.** O prompt do `receive_requirements.py` era contraditório (ramo skeleton mandava `pass`, regra global proibia). LLM emitia `pass<ctrl63>` (ASCII 63 = `?`), `ast.parse` rejeitava, pytest collection falhava.
   - Prompt consistente: docstring é corpo válido em Python, `@pytest.mark.skip` em vez de `pass`.
   - Nova função `_validar_e_sanitizar_codigo(codigo, id_artefato)` com regex `\b(pass|return|continue|break|raise)<[^>\n]*>` + `ast.parse`. Sanitização aplicada antes de escrever o arquivo; código inválido após sanitização propaga `ValueError` para o autocorrect cycle.

3. **Workspace binding do `qa_pipeline`** (antes `workspace_output/tests/` ficava vazio — qa escrevia em `adk/src/agents/qa_agent/artefactsTests/`).
   - `_BASE_DIR`/`TESTS_DIR`/`DOUBT_DIR` (module-level em `receive_requirements.py:17-19`) substituídos por funções `_tests_dir()` e `_doubt_dir()` que chamam `get_agent_workspace("receive_requirements")` em runtime.
   - `_normalizar_caminho_arquivo` em `qa_agent/tools/pytest_runner.py:82` usa a mesma resolução dinâmica.
   - Tools legacy de doubt do `qa_agent` (`DoubtArtifactGenerator.generate`, `gerar_doubt_artifact` em `qa_agent/tools/`) também migradas.

4. **Guardrail anti-empty no `action_planner`.** Prompt instrui: "PROIBIDO devolver resposta vazia. O retorno DEVE ser JSON válido com `tipo_entrada` e `lifecycle.status`. Se não conseguir planejar, devolva JSON de bloqueio estruturado".

5. **Wrapper de retry programático para o `action_planner`.** Guardrail no prompt depende do LLM obedecer; o wrapper adiciona segunda chance independente.
   - Novo módulo `adk/src/agents/workflow_qa/tools/planner_wrapper.py` com `invocar_planejamento_qa(request)`.
   - Roda `action_planner` em runner isolado; se retornar empty, faz 1 retry com prompt suffix anti-empty; se ambas vierem empty, retorna `_FALLBACK_BLOCKED_JSON` determinístico.
   - Substitui `AgentTool(action_planner_agent)` por `FunctionTool(invocar_planejamento_qa)` em `workflow_qa/agent.py`. Garantia: o `qa_pipeline` LLM caller sempre recebe JSON estruturado, nunca empty.

6. **Compat com Gemini API.** Padronização de `Optional[str]` (do `typing`) em vez de `str | None` (PEP 604) em parâmetros de tool — o Gemini API rejeita `anyOf` gerado pelo PEP 604 com `400 INVALID_ARGUMENT`. Aplicado em `executar_pytest_tool` e demais tools do Time 3.

### Cobertura de testes

- `adk/tests/unit/test_hitl_tool.py` — registro como `LongRunningFunctionTool`.
- `adk/tests/unit/test_workflow_qa_hitl.py` — instrução obrigatória + tool registrada.
- `adk/tests/integration/test_hitl_e2e.py` — replay end-to-end (FRESH RUN → pausa → RESUME).
- `adk/tests/unit/test_receive_requirements_sanitizer.py` — 4 casos de sanitização.
- `adk/tests/unit/test_qa_workspace_binding.py` — resolução dinâmica via `monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", ...)`.
- `adk/tests/unit/test_planner_wrapper.py` — `_is_empty`, retry, fallback determinístico.

### Pendências do Time 3

- `_normalizar_caminho_arquivo` em `pytest_runner.py` aceita `dict` internamente mas a tool pública foi estreitada para `str` — **dead code path** a limpar.
- HITL gate do `action_planner` (criar checkpoint pedindo aprovação humana antes de gerar testes) pode ser desejado ou bug — investigar se for o objetivo ter SDLC totalmente automático.
- Limitação conhecida do `_live_runners`: in-process. Reinício de servidor entre pausa e resposta perde o runner; orchestrator retorna "Sessão HITL expirada". Persistência DB-backed fica para spec futuro.

---

## Time 4 — Codificação

### O que o Time entrega hoje no orquestrador

O `coding_review_pipeline` (workflow `workflow_coding_review`) é um `SequentialAgent` `requirements → coder → reviewer`. O `cr_coder_agent` gera código completo (backend FastAPI, templates Jinja2 com CSS, testes pytest) em `workspace_output/coder/`. O `cr_review_agent` lê tudo, avalia em 4 dimensões e persiste `workspace_output/review/verificacao_revisao.md`.

### Melhorias aplicadas

1. **Contrato de estrutura obrigatória de projeto Python no `cr_coder_agent`.** Antes a estrutura variava entre runs (`coder/main.py` vs `coder/app/main.py`) e o app não rodava como pacote (`ModuleNotFoundError: No module named 'app'`).
   - Prompt em `adk/src/agents/workflow_coding_review/coder/prompt.py` e `workflow_coding_review/agent.py` agora exige: `app/__init__.py` (vazio), `app/main.py`, `tests/__init__.py` (vazio), `tests/test_main.py`, `conftest.py` (vazio basta), `requirements.txt`. Imports de teste sempre absolutos (`from app.main import app`).
   - Justificativa explícita no prompt: "OBRIGATÓRIOS mesmo que vazios — sem eles, pytest falha em coletar testes".

2. **Workspace binding do `cr_coder_agent`.** O coder rodando sem binding sobrescreveu `adk/app/main.py` do repositório principal e criou branches git aleatórias na primeira run. Fix em `workflow_coding_review/agent.py`:
   ```python
   _bind(FunctionTool(tool_criar_arquivo), _CODER_WS)
   ```
   Removidas também as `tool_git_*` (não fazem sentido sem ambiente git no pipeline) e substituído o `instruction` herdado de `coder/prompt.py` por uma versão enxuta sem ordens de git (LLM senão alucina `git_checkout` mesmo sem a tool registrada).

3. **`cr_review_agent` persiste `verificacao_revisao.md`** (antes ficava vazio).
   - `tool_ler_arquivo` agora bound a `_CODER_WS` — paths relativos do prompt resolvem corretamente.
   - Instruction enxuto próprio em vez do herdado de `reviewer/prompt.py` (que falava em "consultar diff acumulado", mas `tool_ler_diff` não está registrada neste workflow). LLM antes falhava na Camada 1, abandonava o fluxo e nunca chegava no save.
   - Helper `_discover_coder_files()` + `InstructionProvider` (callable que ADK aceita como `instruction=`) injetam a lista dinâmica de arquivos do coder no momento da invocação (porque no import o `_CODER_WS` ainda está vazio).

4. **`cr_review_agent` quebrado em `SequentialAgent[analyzer, persister]`** contra LLM narrador.
   - Sintoma residual após o fix do item 3: gemini-2.5-flash, depois de ler ~5 arquivos, entrava em "modo narrador" e escrevia código Python como texto (`issues = []`, `issues.append(...)`, `print(default_api.tool_ler_arquivo(...))`) em vez de fazer function calls reais. Nunca chamava `tool_salvar_relatorio`.
   - Solução arquitetural: separar análise de persistência. Cada sub-agente tem 1 tool e 1 responsabilidade — sem espaço para narração.

   ```python
   _review_analyzer = LlmAgent(
       name="cr_review_analyzer",
       tools=[_bind(FunctionTool(tool_ler_arquivo), _CODER_WS)],
       output_key="review_analysis",  # markdown vai para state['review_analysis']
       # prompt pede markdown (não JSON literal — quebra o gatilho de narração)
   )

   _review_persister = LlmAgent(
       name="cr_review_persister",
       tools=[_bind(FunctionTool(tool_salvar_relatorio), _REVIEW_WS)],
       output_key="review",
       # prompt curto com placeholder {review_analysis} + anti-narração explícita
       # ("FAÇA a function call real, NÃO escreva como código Python descritivo")
   )

   _reviewer = SequentialAgent(
       name="cr_review_agent",
       sub_agents=[_review_analyzer, _review_persister],
   )
   ```

5. **Prompts do `coder` e `reviewer`** limpos de identificadores literais de tool. Vocabulário de capacidade: "escrever os arquivos necessários", "preparar a mudança para versionamento", "apresentar resumo de commit ao supervisor e aguardar `sim` explícito". Gate `require_confirmation=True` no `FunctionTool` permanece intocado.

### Cobertura de testes

- `adk/tests/unit/test_review_agent_persistence.py` — 8 casos: `_discover_coder_files`, analyzer instruction com arquivos descobertos, persister referencia `{review_analysis}` + anti-narração, `tool_ler_arquivo` bound em analyzer, `_reviewer` é `SequentialAgent` com 2 sub-agents, persister tem **apenas** `tool_salvar_relatorio` (não pode tentar re-ler arquivos).
- `adk/tests/unit/test_reviewer_schemas.py` — schemas de tool sem `anyOf` (compat Gemini).
- `adk/tests/unit/test_geracao_condicional.py` — geração condicional de arquivos pelo coder.

### Pendências do Time 4

- **API obsoleta de `TemplateResponse`**: o coder gera `templates.TemplateResponse("X.html", {"request": request, ...})` (API antiga). Como `requirements.txt` não pina `starlette`, `uv pip install` resolve para `starlette==1.0.0` que mudou a assinatura. Resultado: rotas com template retornam HTTP 500 (`TypeError: unhashable type: 'dict'`). Workaround atual é `sed`/Edit manual. **Próximo passo**: pinar `starlette<1.0` no `requirements.txt` gerado OU treinar o coder na API nova.
- Persister também pode entrar em modo narrador em casos extremos. **Fallback documentado**: substituir o `_review_persister` LlmAgent por `before_agent_callback` que chama `tool_salvar_relatorio` programaticamente (zero LLM no save).
- `workflow_coding` (SDLC completo: requirements → architect → test_planner → coder → reviewer → qa → finalizer) ainda fora do orchestrator — só roda standalone. Refatorar para isolamento por etapa exige BaseAgent custom como o orchestrator.

---

## Orquestrador & Infra (cross-cutting)

Mudanças que não pertencem a um Time específico — são da plumbing que faz os 4 pipelines coexistirem.

### Melhorias aplicadas

1. **Orchestrator reescrito como `_PipelineOrchestrator` (BaseAgent custom)** em `adk/src/agents/orchestrator/agent.py`.
   - Antes: `LlmAgent` com `AgentTool(workflow)` — LLM pai decidia quando chamar. Em runs longas com HITL, "esquecia" de chamar a próxima fase.
   - Agora: BaseAgent custom itera explicitamente `_pipelines` em `_run_async_impl`. Cada pipeline roda em runner próprio (`InMemorySessionService` isolado). Outputs acumulam em `state['accumulated_outputs']`.

2. **`Doubt Inbox` unificado** em `adk/shared/tools/doubt_inbox.py` (`coletar_doubts_pendentes`, `responder_doubt`).
   - Parser tolerante para os 4 formatos vigentes (Time 1 versionado, `doubt_handler` centralizado, `clarification`, QA `DoubtArtifactGenerator`).
   - Ordenação por bloqueante + severidade (Crítica > Alta > Média > Baixa).
   - Best-effort: campos faltantes viram string vazia, nunca lança exceção.

3. **HITL real (v5) com state persistido via `EventActions.state_delta`.**
   - Chaves novas em `ctx.session.state`: `accumulated_outputs`, `paused_pipeline`, `paused_inner_session_id`, `paused_function_call`.
   - **Descoberta crítica**: mutação direta em `ctx.session.state` no `_run_async_impl` **não persiste** no ADK. Precisa ser emitida via `Event(actions=EventActions(state_delta={...}))`. Padrão obrigatório para qualquer `BaseAgent` que mantenha estado entre invocações.
   - `_live_runners: dict[str, tuple[Runner, str]]` — atributo de instância (não persistido) que mantém o runner do pipeline pausado vivo entre T0 e T1.
   - Helpers em `adk/src/agents/orchestrator/_helpers.py`: `_extract_user_text`, `_build_input`, `_is_pending_long_running_call`, `_parse_decision` (texto livre → tupla `(decision, comments)`), `_clear_pause_state`, `_set_pause_state`.

4. **Empty-response retry no `_handle_fresh_run`.** Helper `_is_empty_response` + `EMPTY_RETRY_PROMPT`. Se um pipeline devolve empty (e não é pausa HITL), faz 1 retry com prompt suffix. Após 2 empties, anexa string sintética em `accumulated_outputs` para o próximo pipeline ter sinal claro de falha em vez de string fantasma.

5. **Convenção "prompts não citam tools"**. Verificação:
   ```bash
   cd adk && rg -nP '\b(tool_[a-z_]+|run_slicer|ler_chunk|extract_text|run_search)\b' src/agents/*/prompt.py
   ```
   Resultado esperado: zero matches. Exceção registrada: `aguardar_aprovacao_humana` no `workflow_qa/agent.py`.

6. **Docstrings GOOD para ~22 tools.** Padrão canônico: propósito + Quando usar + Args + Returns ≥ 80 chars. Fonte de verdade sobre cada tool é a docstring (`FunctionDeclaration.description`).

7. **HITL lifecycle** .
   - `KEEP_UP=1` default — antes matava uvicorn e `_live_runners` morria junto.
   - Detecção automática de pausa pós-run via parsing de `state_delta.paused_pipeline`. Mensagem `🔶 [HITL]` instrui como retomar.
   - `SESSION_ID`/`USER_ID` persistidos em `/tmp/ai4es-current-session.env` entre invocações de `run-agent.sh` (a segunda invocação precisa do mesmo `outer_session_id` que está em `_live_runners`).
   - `stop-server.sh` limpa o arquivo no fim.
   - Novo `verify-coder-output.sh` para validar o app gerado (snapshot + `uv venv` + `pytest` + `curl /healthcheck`).

8. **Compat Gemini API**: padrão `Optional[str]` em parâmetros de tool. Padrão de inspeção pré-execução:
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

### Pendências cross-cutting

- **HITL apenas em `qa_pipeline`** — generalizar para `requirements_pipeline`, `design_pipeline`, `coding_review_pipeline` exige spec próprio (`BaseHITLOrchestrator` pipeline-agnostic).
- **`_live_runners` é in-process** — sobreviver a restart do servidor exige persistência DB-backed (Redis/SQLite).
- **`init_workspace()` chamado em import-time** pelo `workflow_coding_review` — apaga `workspace_output/` a cada nova execução do pipeline na mesma sessão. Mover para lifespan hook do FastAPI em `adk/app/main.py` com flag `--keep`.
- **`classificar_doubt` heurístico (auto-routing v2)** excluído do MVP. Hoje todo doubt escala para o usuário. Próxima iteração: heurística por `origem_agente` + `categoria` + snapshot comparison para detectar novos doubts.
- **`architect`, `test_planner`, `finalizer`** continuam fora do orquestrador. São schema-only (`LlmAgent` com `output_schema`, sem tools) — não persistem arquivos por design. Criar pipelines wrapper que persistam o JSON da saída fica para próximo ciclo.

---

## Apêndice — Mapeamento melhoria ↔ planos (referência interna)

A documentação detalhada por plano fica em `docs/superpowers/` (não rastreada no Git, mantida localmente). Sumário do mapeamento:

| Plano (data) | Times afetados |
|---|---|
| `orchestrator-sdlc-mvp` (05-16) | Cross-cutting (orchestrator + doubt_inbox) |
| `workspace-binding-requisitos-doubts` (05-17) | Time 1 |
| `prompt-tool-decoupling` (05-17) | Times 1, 4 + Cross-cutting (docstrings) |
| `hitl-orchestrator` (05-17) | Time 3 + Cross-cutting (orchestrator v5) |
| `sdlc-gaps-fixes` (05-17) | Time 2 (F3), Time 3 (F1+F2) + Cross-cutting |
| `fix-orchestrator-bugs` (05-17) | Time 2 (bug 1), Time 3 (bug 2), Time 1 (bug 3), Time 4 (bugs 4-5), Infra (bug 6) |
| `fix-review-qa-pipelines` (05-18) | Time 4 (Section A), Time 3 (Section B) |
| `fix-reviewer-narration` (05-18) | Time 4 |
