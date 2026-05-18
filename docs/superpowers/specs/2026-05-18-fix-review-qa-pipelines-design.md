# Fix Review + QA Pipelines — Design Spec

**Data:** 2026-05-18
**Status:** Proposed
**Escopo:** Duas falhas reproduzidas durante a run E2E do orchestrator com o prompt da Marina Vasconcellos Fotografia (site de organização de fotos + álbuns).
**Princípio:** robustez sem refactor de arquitetura. Não alteramos o shape do `_PipelineOrchestrator` v5, não removemos HITL, não mudamos o contrato dos agentes top-level. Mudanças concentradas em dois arquivos (`workflow_coding_review/agent.py`, `workflow_qa/agent.py`) e um novo módulo (`workflow_qa/tools/planner_wrapper.py`).

---

## 1. Contexto e motivação

A run de 2026-05-18 com o prompt da Marina executou os 4 pipelines do orchestrator. Os artefatos esperados em `workspace_output/` apareceram em 3 das 5 fases pretendidas:

| Fase | Status | `workspace_output/` |
|---|---|---|
| requirements_pipeline | ✓ | `requirements/` populado (HUs, RFs, RNFs, RNs, Glossario) |
| design_pipeline | ✓ | `design/` + `design/diagrams/` + `design/reports/` populados |
| coding_review_pipeline / coder | ✓ | `coder/` com 18 arquivos (backend + 7 templates Jinja2 + 1 test) |
| coding_review_pipeline / **review** | ✗ | `review/` **vazio** — `verificacao_revisao.md` não foi salvo |
| qa_pipeline | ✗ | Bloqueado em HITL falso (`Doubt_Artifact_*.md` em `tests/inputs/doubt_artifacts/`); nenhum teste gerado, nenhum pytest executado |

Resultado prático: o app gerado pelo coder rodou ponta a ponta no golden path da Marina (após 1 fix manual no `main.py` por compatibilidade com `starlette==1.0.0`), mas o SDLC **não fez gate de qualidade**. O reviewer não emitiu veredito persistido e o QA não validou via pytest.

### Falha 1 — `cr_review_agent` não persistiu o relatório

O `cr_review_agent` em `adk/src/agents/workflow_coding_review/agent.py:140-156` está construído assim:

```python
_reviewer = LlmAgent(
    ...
    instruction=(
        reviewer_prompt.instruction
        + f"\n\n# WORKSPACE\n"
        + f"Os arquivos a revisar estão em `{_CODER_WS}/`. "
        + f"Como o ambiente não é git, use tool_ler_arquivo (apontando para `{_CODER_WS}/<file>`) "
        + f"para ler cada arquivo. Salve o relatório em `{_REVIEW_WS}/` via tool_salvar_relatorio."
    ),
    ...
    tools=[
        FunctionTool(tool_ler_arquivo),                              # ⚠ NÃO bound ao _CODER_WS
        _bind(FunctionTool(tool_salvar_relatorio), _REVIEW_WS),       # ✓ bound
    ],
)
```

`reviewer_prompt.instruction` (em `adk/src/agents/reviewer/prompt.py`) instrui o LLM a "consultar o diff acumulado da branch" como Camada 1 do fluxo de verificação. No `workflow_coding_review` **não existe `tool_ler_diff` registrada** — o reviewer foi simplificado para esse pipeline (sem git). O LLM tenta seguir o fluxo de 4 camadas do prompt, falha na primeira ação ("Consulte o diff acumulado") porque não tem a tool, **abandona o fluxo**, e nunca chega na instrução "Salve o relatório" que vem depois das 4 camadas.

Adicionalmente, `tool_ler_arquivo` registrado na linha 153 **não está bound** ao `_CODER_WS`. Mesmo que o LLM decidisse ler arquivos por path relativo (`app/main.py`), eles seriam resolvidos contra o CWD do servidor (`adk/`), não contra `_CODER_WS`. Hoje isso é mascarado pela instrução pedir `{_CODER_WS}/<file>` (absoluto), mas é uma armadilha latente.

### Falha 2 — `action_planner` retorna empty, qa trava em HITL falso

O `qa_pipeline` é um `LlmAgent` (em `adk/src/agents/workflow_qa/agent.py:95-112`) que tem como tool um `AgentTool(action_planner_agent)`. O fluxo previsto na `_INSTRUCTION`:

1. qa_pipeline (LLM) recebe o request
2. Chama `action_planner(request=...)` via AgentTool
3. action_planner produz um JSON de plano (com 90+ campos no schema, ver `qa_agent/subagents/action_planner/prompt.py`)
4. qa_pipeline lê o JSON, decide próximos passos

Na run da Marina, passo 3 retornou `{"result": ""}`. O LLM do qa_pipeline interpretou como "planejamento falhou irrecuperável" e disparou imediatamente `DoubtArtifactGenerator.generate(trigger_type="planning_failure")`, criando `Doubt_Artifact_*.md` e encerrando o pipeline com `bloqueados=1`.

**Causa provável do empty:** O `action_planner` precisa emitir um JSON com ~90 campos seguindo o schema completo (`tipo_entrada`, `modo`, `lifecycle`, `hitl_checkpoint`, `analise_inicial`, `analise_progressiva`, `criterios_verificaveis`, `objetivo_qa`, `estrategia`, `checklist_inicial`, `handoff_context`, `relatorio_conformidade_esperado`, etc.). O prompt tem 220 linhas. O modelo `gemini-2.5-flash` ocasionalmente trunca ou falha silenciosamente nessa geração. Embora o prompt declare um "PROTOCOLO ANTI-EMPTY" exigindo um JSON de bloqueio quando não conseguir planejar, na prática o LLM ainda retorna string vazia.

O orchestrator v5 tem retry para empty no **topo do pipeline** (linhas 238-262 do `orchestrator/agent.py`), mas esse retry só dispara quando o qa_pipeline INTEIRO retorna empty — não quando a chamada nested `qa_pipeline → AgentTool(action_planner)` retorna empty. O qa_pipeline (LlmAgent) **devolve texto** ao orchestrator (a mensagem "Não foi possível concluir o pipeline de QA"), então o retry do orchestrator não aciona.

---

## 2. Section A — Fix do `cr_review_agent` (Falha 1)

**Arquivo a editar:** `adk/src/agents/workflow_coding_review/agent.py`

Três mudanças cirúrgicas, sem alterar `reviewer/prompt.py` (que ainda é usado pelo agente `reviewer` top-level e pelo `workflow_coding` legado).

### A.1 — Bind `tool_ler_arquivo` ao `_CODER_WS`

```python
# antes (linha 152-155)
tools=[
    FunctionTool(tool_ler_arquivo),
    _bind(FunctionTool(tool_salvar_relatorio), _REVIEW_WS),
],

# depois
tools=[
    _bind(FunctionTool(tool_ler_arquivo), _CODER_WS),
    _bind(FunctionTool(tool_salvar_relatorio), _REVIEW_WS),
],
```

**Por que resolve:** o LLM agora pode chamar `tool_ler_arquivo(caminho="app/main.py")` com path relativo e o `_bind_tool_to_workspace` resolve para `_CODER_WS/app/main.py`. Sem isso, mesmo o caminho absoluto que o prompt sugere é frágil — depende do LLM concatenar corretamente.

### A.2 — Substituir o `instruction` herdado por um fluxo enxuto

O prompt herdado (`reviewer_prompt.instruction`) tem 4 camadas (completude, arquitetura, corretude, testes) e fala em "diff acumulado". Não funciona neste workflow porque não há git. Em vez de tentar acrescentar overrides ao prompt longo, criar uma `instruction` própria para o `cr_review_agent`:

```python
_REVIEWER_INSTRUCTION = f"""
# PERFIL
Você é um Engenheiro de Software Sênior responsável por revisar código produzido por outro agente.
Não há ambiente git neste pipeline. Você revisa arquivos diretamente no workspace.

# WORKSPACE
Os arquivos a revisar estão em `{_CODER_WS}/` (caminho absoluto do disco).
Para você, use caminhos RELATIVOS — `tool_ler_arquivo` resolve automaticamente.

# ARQUIVOS A REVISAR
{{_AUTO_DISCOVERED_FILES}}

# FERRAMENTAS DISPONÍVEIS
- `tool_ler_arquivo(caminho)`: lê arquivo do workspace do coder (path relativo).
- `tool_salvar_relatorio(nome_arquivo, conteudo)`: salva o relatório no workspace de review.

# FLUXO OBRIGATÓRIO
1. Para cada arquivo da lista acima, chame `tool_ler_arquivo(caminho)`.
2. Avalie em 4 dimensões: COMPLETUDE, ARQUITETURA, CORRETUDE, TESTES.
   - Completude: arquivos esperados foram criados? tests/ existe? requirements.txt?
   - Arquitetura: SRP, separação de concerns, acoplamento.
   - Corretude: bugs visíveis, edge cases, segurança.
   - Testes: existem? cobrem cenários relevantes? assertions significativas?
3. **OBRIGATÓRIO ao fim**: chame `tool_salvar_relatorio(nome_arquivo='verificacao_revisao.md', conteudo=<markdown>)`.
   Sem essa chamada, sua revisão NÃO é entregue — o pipeline falha mesmo que você produza texto.

# REGRAS DE DECISÃO
- Qualquer issue `critical` → status="BLOQUEADO"
- Apenas `warning`/`info` → status="APROVADO" com ressalvas
- Sem issues → status="APROVADO"

# SAÍDA FINAL (texto retornado pelo agente, depois de salvar)
JSON único:
{{{{
  "status": "APROVADO" | "BLOQUEADO",
  "issues": [{{{{"severity": "critical|warning|info", "description": "...", "file": "...", "layer": "completude|arquitetura|corretude|testes"}}}}],
  "report_path": "verificacao_revisao.md"
}}}}
"""
```

### A.3 — Descobrir arquivos do coder no momento da invocação

Reviewer não tem como listar arquivos (não tem `os.walk` ou tool equivalente). O glob precisa rodar **no momento em que o reviewer é invocado** — não no import do módulo — porque no import o `_CODER_WS` está vazio (coder ainda não rodou).

**Abordagem principal:** usar `before_agent_callback` do ADK (`google.adk.agents.LlmAgent`) que recompõe o `instruction` dinamicamente a cada invocação. A função do callback faz o glob e substitui o placeholder `{_AUTO_DISCOVERED_FILES}` na instruction antes da chamada ao modelo.

```python
from pathlib import Path

def _discover_coder_files() -> str:
    """Lista arquivos no _CODER_WS (relativo), formato bullet, pra injetar no prompt."""
    coder_dir = Path(_CODER_WS)
    if not coder_dir.exists():
        return "- (nenhum arquivo ainda — coder será executado antes de você)"
    files = sorted(
        str(p.relative_to(coder_dir))
        for p in coder_dir.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )
    return "\n".join(f"- {f}" for f in files) if files else "- (workspace vazio)"


def _reviewer_before_callback(callback_context):
    """Injeta a lista atualizada de arquivos do coder no instruction antes da invocação."""
    listing = _discover_coder_files()
    # Aplicar via agent.instruction direto, ou via callback_context.agent.instruction
    # — confirmar API exata no ADK durante implementação.
    ...

_reviewer = LlmAgent(
    ...,
    instruction=_REVIEWER_INSTRUCTION,  # contém o placeholder {_AUTO_DISCOVERED_FILES}
    before_agent_callback=_reviewer_before_callback,
    ...
)
```

**Fallback (se ADK não suportar mutação de instruction via callback):** registrar `instruction` como callable em vez de string. ADK aceita `instruction: Callable[[ReadonlyContext], str]` em alguns níveis. Documentar a decisão na fase de planejamento (verificação na doc oficial do ADK).

**Fallback do fallback:** glob no import + nota no instruction explicando que a lista pode estar desatualizada. Reviewer ainda funciona usando paths que o LLM deduz dos requisitos da fase anterior — só perde a precisão da lista canônica.

---

## 3. Section B — Wrapper de retry para `action_planner` (Falha 2)

### B.1 — Novo módulo `workflow_qa/tools/planner_wrapper.py`

Arquivo novo, ~70 linhas:

```python
"""Wrapper de retry para invocações do action_planner no qa_pipeline.

Motivação: action_planner via AgentTool retorna ocasionalmente {"result": ""},
travando o qa_pipeline em HITL falso. Este wrapper roda o action_planner em
runner isolado, faz retry programático em caso de empty, e garante que o
caller (qa_pipeline) sempre receba JSON estruturado.
"""

from typing import Optional

from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.genai import types

from src.agents.qa_agent.subagents.action_planner.agent import agent as action_planner_agent

_EMPTY_THRESHOLD = 8  # heurística: <8 chars úteis = empty
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
_FALLBACK_BLOCKED_JSON = (
    '{"tipo_entrada":"indefinido","modo":"indefinido","tools":[],'
    '"casos_de_teste_propostos":[],"lifecycle":{"status":"bloqueado",'
    '"execution_allowed":false,"next_step":"aguardar_resolucao_humana"},'
    '"erro":"action_planner não respondeu após 2 tentativas — falha de modelo"}'
)


def _is_empty(text: Optional[str]) -> bool:
    if text is None:
        return True
    stripped = text.strip().strip("`").strip()
    return len(stripped) < _EMPTY_THRESHOLD


async def _invoke_once(request: str, user_id: str = "qa-pipeline") -> str:
    """Roda action_planner uma vez em runner isolado, retorna last_text."""
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
        user_id=session.user_id, session_id=session.id, new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    last_text = part.text
    await runner.close()
    return last_text


async def invocar_planejamento_qa(request: str) -> str:
    """Invoca action_planner com retry programático.

    Garantia: sempre devolve string não-vazia com JSON estruturado.
    Caller (qa_pipeline) pode parsear sem se preocupar com empty.

    Args:
        request: texto do request original (requisitos + código se houver).
    Returns:
        JSON string com plano (válido) ou JSON de bloqueio estruturado.
    """
    first = await _invoke_once(request)
    if not _is_empty(first):
        return first

    second = await _invoke_once(request + _RETRY_PROMPT_SUFFIX)
    if not _is_empty(second):
        return second

    return _FALLBACK_BLOCKED_JSON
```

### B.2 — Mudar `workflow_qa/agent.py` para usar o wrapper

```python
# antes (linhas 12-19)
from google.adk.tools.agent_tool import AgentTool
from src.agents.qa_agent.subagents.action_planner.agent import agent as action_planner_agent
...

# depois
from google.adk.tools.agent_tool import AgentTool
from src.agents.qa_agent.subagents.action_planner.agent import agent as action_planner_agent
from src.agents.workflow_qa.tools.planner_wrapper import invocar_planejamento_qa
...

# antes (linhas 104-111)
tools=[
    AgentTool(agent=action_planner_agent),
    AgentTool(agent=receber_requisitos_agent),
    AgentTool(agent=code_fix_agent),
    FunctionTool(executar_pytest_tool),
    FunctionTool(DoubtArtifactGenerator.generate),
    LongRunningFunctionTool(aguardar_aprovacao_humana),
],

# depois
tools=[
    FunctionTool(invocar_planejamento_qa),
    AgentTool(agent=receber_requisitos_agent),
    AgentTool(agent=code_fix_agent),
    FunctionTool(executar_pytest_tool),
    FunctionTool(DoubtArtifactGenerator.generate),
    LongRunningFunctionTool(aguardar_aprovacao_humana),
],
```

### B.3 — Ajustar `_INSTRUCTION` do qa_pipeline

Trocar referências a `action_planner_agent` por `invocar_planejamento_qa`:

```diff
 1. PLANEJAMENTO
-   Encaminhe a entrada ao action_planner_agent.
-   Aguarde o plano de ação: tipos de teste, dependências, pontos de
-   validação humana (HITL) e relatório de compliance preliminar.
+   Chame `invocar_planejamento_qa(request=<entrada original>)`.
+   Essa função roda o planner com retry automático e GARANTE retorno
+   de JSON estruturado (nunca empty). O JSON contém: tipos de teste,
+   dependências, pontos de validação humana (HITL) e relatório de
+   compliance preliminar.

    → Se o plano retornar com `hitl_checkpoint.required=true`:
+   → Se `lifecycle.status == "bloqueado"` no JSON retornado:
+        Encerre com Doubt_Artifact citando `erro` do JSON.
+        Esse caminho só é acionado quando o action_planner não
+        conseguiu produzir plano nem com retry — bloqueio legítimo.
```

---

## 4. Section C — Comportamento E2E pós-fix

Re-rodando `bash .claude/skills/ai4es-e2e/scripts/e2e.sh /tmp/photographer-prompt.md`:

**workspace_output/ esperado:**

```
workspace_output/
├── requirements/             ✓ HUs, RFs, RNFs, RNs, Glossario
├── design/                   ✓ analise + diagrams + reports
├── coder/                    ✓ backend + templates + tests
├── review/
│   └── verificacao_revisao.md  ← NOVO (Section A entrega)
└── tests/
    ├── inputs/<slug>.json    ← NOVO (qa.geração via receber_requisitos)
    └── <slug>/test_<slug>.py ← NOVO (qa.geração)
```

**Output textual do qa_pipeline (esperado):**
- `total: N artefatos processados`
- `sucessos: N` (ou parcial)
- Caminhos dos testes gerados
- Saída do pytest (cobertura, asserts passados/falhos)
- Doubt_Artifacts vazio (a menos que action_planner falhe legitimamente — fallback determinístico)

**Falsos-positivos eliminados:**
- "QA-PLANNING-BLOCK-001" só aparece se o `_FALLBACK_BLOCKED_JSON` for retornado (depois de 2 tentativas falhas) — é um sinal real de problema, não ruído

---

## 5. Section D — Testes (validação)

### D.1 — Testes unit novos

**`adk/tests/unit/test_review_agent_persistence.py`** (~3 testes, ~40 linhas)

- Verifica que `_reviewer` tem `tool_ler_arquivo` bound a `_CODER_WS` (introspecção do tool wrapper)
- Verifica que `_reviewer.instruction` contém a substring obrigatória "OBRIGATÓRIO ao fim: chame `tool_salvar_relatorio`"
- Verifica que `_discover_coder_files()` (ou seu equivalente em callback) é chamado quando o reviewer é invocado, e o instruction final contém a lista

**`adk/tests/unit/test_planner_wrapper.py`** (~4 testes, ~80 linhas)

- `_is_empty("")` → True; `_is_empty(None)` → True; `_is_empty("   ")` → True
- `_is_empty('{"tipo_entrada":"requisito",...}')` → False (~50 chars)
- `invocar_planejamento_qa` mockando `_invoke_once`:
  - Primeira chamada devolve JSON válido → retorna esse JSON, segunda call não acontece
  - Primeira call empty + segunda call JSON válido → retorna o JSON da segunda
  - Ambas as calls empty → retorna `_FALLBACK_BLOCKED_JSON`
- Verifica que `_FALLBACK_BLOCKED_JSON` é JSON parseável e tem `lifecycle.status == "bloqueado"`

### D.2 — Teste de integração E2E

**Reaproveita o teste E2E já existente** (`adk/tests/integration/`):
- Spawnar runner com prompt simples ("Crie um endpoint /healthcheck"), confirmar que `workspace_output/review/verificacao_revisao.md` é criado
- Mock do `action_planner_agent` retornando `""` na primeira call e JSON válido na segunda — confirmar que qa_pipeline prossegue (chama `receber_requisitos`)

### D.3 — Validação manual

Após implementação:
```bash
cd adk && .venv/bin/pytest tests/unit/test_review_agent_persistence.py tests/unit/test_planner_wrapper.py -v
bash .claude/skills/ai4es-e2e/scripts/diagnose.sh
bash .claude/skills/ai4es-e2e/scripts/e2e.sh /tmp/photographer-prompt.md
bash .claude/skills/ai4es-e2e/scripts/inspect-run.sh
# Verificar manualmente:
# - workspace_output/review/verificacao_revisao.md existe
# - workspace_output/tests/inputs/ tem JSONs
# - workspace_output/tests/<slug>/test_*.py existem
# - output do qa_pipeline mostra "sucessos: N" e relatório pytest
```

---

## 6. Não-objetivos (out of scope deste spec)

- **Generalizar HITL para outros pipelines** (requirements/design/coding_review). HITL real existe apenas no qa_pipeline (`LongRunningFunctionTool`). Generalização fica como follow-up.
- **Persistência de `_live_runners`** para sobreviver reinício de servidor entre pausa HITL e resposta. Limitação já documentada no `CLAUDE.md`.
- **Refactor do prompt do `action_planner`** para reduzir o JSON schema. Tentado em proposta anterior; descartado pelo risco de regressão em `plan_validator` e `compliance_report`. Wrapper de retry é mais cirúrgico.
- **Fix do `cr_coder_agent` para gerar código compatível com `starlette` 1.0+.** Fix manual aplicado na run da Marina é trackado em `project-orchestrator-app-completeness` (memória). Pode virar spec separado se virar regressão recorrente.
- **`workspace_output/test_plans/`, `architecture/`, `finalizer/`, `orchestrator/`.** São schema-only por design (não persistem) ou pertencem a agentes não compostos no orchestrator atual (architect, test_planner, finalizer).

---

## 7. Riscos e mitigações

| Risco | Probabilidade | Mitigação |
|---|---|---|
| `instruction_provider` / `before_agent_callback` não suportado pelo ADK para mutação dinâmica de `instruction` no `cr_review_agent` | Média | Fallback: glob no import do módulo + nota no prompt explicando que a lista pode estar vazia se o coder ainda não rodou. Reviewer ainda pode usar `tool_ler_arquivo` com paths que o LLM deduzir dos requisitos da fase anterior. |
| `_invoke_once` no wrapper falhar com erro de `Runner` em vez de retornar empty | Baixa | `_invoke_once` envolto em `try/except Exception`; em caso de erro, propaga uma string `"ERROR: <msg>"` que `_is_empty` trata como empty (force retry/fallback). |
| Retry duplica latência do qa_pipeline | Certa quando dispara | Aceitável — é o trade-off por ter SDLC completo. Latência adicional só em ~10% das runs (quando primeira call falha). |
| Wrapper bypassa `plan_validator` que o action_planner deveria chamar | Baixa | `action_planner` continua chamando `plan_validator` internamente (suas tools não mudam). O wrapper só envolve a invocação top-level. |
| Mock no teste E2E não captura todos os edge cases | Média | Validação manual com `e2e.sh` + `inspect-run.sh` é gate adicional. Testes unit cobrem a lógica do wrapper. |

---

## 8. Resumo das mudanças

| Arquivo | Tipo | LOC |
|---|---|---|
| `adk/src/agents/workflow_coding_review/agent.py` | Edit | ~50 modificadas (bind + instruction novo + glob) |
| `adk/src/agents/workflow_qa/agent.py` | Edit | ~10 modificadas (import + tools + instruction diff) |
| `adk/src/agents/workflow_qa/tools/__init__.py` | New | 1 (export) |
| `adk/src/agents/workflow_qa/tools/planner_wrapper.py` | New | ~70 |
| `adk/tests/unit/test_review_agent_persistence.py` | New | ~40 |
| `adk/tests/unit/test_planner_wrapper.py` | New | ~80 |
| **Total** | | **~250 LOC** |

Nenhum schema mudou, nenhum contrato público entre pipelines mudou, `_PipelineOrchestrator` v5 não foi tocado. O fix é local ao `workflow_coding_review` e `workflow_qa`.
