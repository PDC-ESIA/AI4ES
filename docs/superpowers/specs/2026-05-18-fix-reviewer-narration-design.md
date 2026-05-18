# Fix Reviewer Narration — Design Spec

**Data:** 2026-05-18
**Status:** Proposed
**Escopo:** Bug residual descoberto durante a validação E2E do plano `2026-05-18-fix-review-qa-pipelines`. O `cr_review_agent` (mesmo após o fix de wiring nos commits c20182c..832bdf8) ainda não persiste `verificacao_revisao.md` porque o LLM (gemini-2.5-flash) entra em modo narrador no meio do fluxo e escreve tool calls como texto Python em vez de executá-los.
**Princípio:** quebrar o agente em dois sub-agentes sequenciais com escopos disjuntos. Analyzer pode narrar livremente; persister tem apenas 1 tool e 1 ação — sem espaço para narração.

---

## 1. Contexto e motivação

A run E2E pós-fix (commits c20182c → 832bdf8 + 3b49424) confirmou que:

- ✓ `tool_ler_arquivo` está bound a `_CODER_WS` — o LLM faz chamadas reais (5+ leituras verificadas no log de 2026-05-18 08:30)
- ✓ `InstructionProvider` injeta lista dinâmica de arquivos no instruction (testes unit confirmam)
- ✓ Phantom `tool_ler_diff` foi removido do prompt
- ✗ Mesmo assim, `workspace_output/review/verificacao_revisao.md` permanece vazio

**Reprodução do bug no log da run E2E:**

Após chamar `tool_ler_arquivo` para `requirements.txt`, `conftest.py`, `app/__init__.py`, `app/database.py`, `app/models.py`, o `cr_review_agent` emitiu um evento TEXT com este conteúdo:

```python
issues = []
issues.append({
    "severity": "warning",
    "description": "Hardcoded upload directories...",
    "file": "app/main.py",
    "layer": "arquitetura"
})
issues.append({
    "severity": "critical",
    "description": "No tests provided...",
    "file": "app/main.py",
    "layer": "testes"
})

print(default_api.tool_ler_arquivo(caminho = "app/database.py"))
```

Isso é narração — o LLM escreveu código Python (`issues = []`, `issues.append(...)`, `print(default_api.tool_X(...))`) como TEXTO no output em vez de fazer mais function calls reais. Imediatamente após esse evento, o `cr_review_agent` cedeu controle ao próximo agente do pipeline (`workflow_qa`) sem ter chamado `tool_salvar_relatorio`.

**Causa provável:**

O `cr_review_agent` é um `LlmAgent` único com:
- 2 tools registradas (`tool_ler_arquivo`, `tool_salvar_relatorio`)
- 1 prompt longo descrevendo 4 camadas de análise + JSON de saída + "OBRIGATÓRIO ao fim chame tool_salvar_relatorio"

Em runs longas, o gemini-2.5-flash em certo ponto "decide" que terminou (depois de várias leituras) e começa a montar o JSON de saída — mas o monta como TEXTO (código Python ilustrativo) em vez de chamar a tool de save. O exemplo de saída literal no prompt (`{"status": "APROVADO" | "BLOQUEADO", ...}`) provavelmente é o gatilho — o LLM "completa" o exemplo.

Esse é um problema bem documentado de tool-calling em modelos da família Gemini Flash (e Sonnet em outras situações): quando o output esperado é estruturado E há tools disponíveis, o LLM ocasionalmente escolhe o caminho "produzir texto estruturado" em vez de "fazer tool call". Quanto maior o prompt e mais tools disponíveis, maior a probabilidade.

---

## 2. Section A — Reestruturar `_reviewer` como SequentialAgent

**Arquivo a editar:** `adk/src/agents/workflow_coding_review/agent.py`

### A.1 — Renomeações

Renomear o que hoje é "o reviewer único" para refletir que ele virou apenas a fase de análise:

- `_REVIEWER_INSTRUCTION_TEMPLATE` → `_REVIEW_ANALYZER_INSTRUCTION_TEMPLATE`
- `_reviewer_instruction_provider` → `_review_analyzer_instruction_provider`

O símbolo público `_reviewer` permanece — ele agora é o SequentialAgent que compõe os dois novos sub-agentes.

### A.2 — Novo `_REVIEW_ANALYZER_INSTRUCTION_TEMPLATE`

Versão enxuta do template atual, removendo a seção "FERRAMENTAS DISPONÍVEIS" e a seção "OBRIGATÓRIO ao fim". O analyzer não tem mais `tool_salvar_relatorio`. Seu papel é produzir markdown de análise — nada mais.

```python
_REVIEW_ANALYZER_INSTRUCTION_TEMPLATE = """
# PERFIL
Você é um Engenheiro de Software Sênior responsável por analisar código produzido por outro agente.
Você é a FASE 1 de um pipeline de revisão de 2 fases. Sua única responsabilidade é PRODUZIR
A ANÁLISE — outro agente vai persistir o relatório no próximo passo.

# WORKSPACE
Os arquivos a revisar estão em `__CODER_WS__/`.
Use caminhos RELATIVOS — tool_ler_arquivo resolve automaticamente.

# ARQUIVOS A REVISAR
__FILES__

# FLUXO
1. Para cada arquivo da lista, chame tool_ler_arquivo(caminho).
2. Avalie em 4 dimensões: COMPLETUDE, ARQUITETURA, CORRETUDE, TESTES.
   - Completude: arquivos esperados foram criados? tests/ existe? requirements.txt?
   - Arquitetura: SRP, separação de concerns, acoplamento.
   - Corretude: bugs visíveis, edge cases, segurança.
   - Testes: existem? cobrem cenários relevantes? assertions significativas?

# REGRAS DE DECISÃO
- Qualquer issue critical → status BLOQUEADO
- Apenas warning/info → status APROVADO com ressalvas
- Sem issues → status APROVADO

# SAÍDA
Produza markdown com seções "## Status: APROVADO|BLOQUEADO", "## Issues" (lista por severidade
com arquivo/camada/descrição), e "## Resumo" (1 parágrafo). NÃO produza JSON literal —
o próximo agente parseia seu markdown e gera o JSON final. NÃO tente salvar nada — você
não tem essa capacidade nesta fase.
"""
```

Pontos-chave:
- Sem menção a `tool_salvar_relatorio` (não é tool dele)
- Saída em **markdown**, não JSON — quebra o gatilho de narração (LLM não completa JSON literal)
- Texto explícito sobre "FASE 1 de 2" — sinaliza que persistência é responsabilidade de outro agente

### A.3 — Novo `_review_analyzer_instruction_provider`

Mantém o padrão `InstructionProvider` que já validamos (callable que ADK aceita como `instruction=`):

```python
def _review_analyzer_instruction_provider(_ctx) -> str:
    return (
        _REVIEW_ANALYZER_INSTRUCTION_TEMPLATE
        .replace("__CODER_WS__", _CODER_WS)
        .replace("__FILES__", _discover_coder_files())
    )
```

### A.4 — Novo `_review_analyzer` LlmAgent

```python
_review_analyzer = LlmAgent(
    model=_model,
    name="cr_review_analyzer",
    description="Fase 1 de revisão: lê código do coder e produz análise em markdown.",
    instruction=_review_analyzer_instruction_provider,
    output_key="review_analysis",
    tools=[
        _bind(FunctionTool(tool_ler_arquivo), _CODER_WS),
    ],
)
```

Notas:
- `output_key="review_analysis"` — o markdown da análise vai para `state['review_analysis']`
- Sem `tool_salvar_relatorio` registrada — analyzer **não pode** persistir mesmo se quisesse

### A.5 — Novo `_review_persister` LlmAgent

```python
_REVIEW_PERSISTER_INSTRUCTION = """
Você é a FASE 2 de um pipeline de revisão de código.

A análise foi produzida pela fase anterior e está disponível abaixo:

---ANALISE---
{review_analysis}
---FIM ANALISE---

AÇÃO ÚNICA E OBRIGATÓRIA:
Chame tool_salvar_relatorio com:
  - nome_arquivo: "verificacao_revisao.md"
  - conteudo: o texto entre ---ANALISE--- e ---FIM ANALISE--- acima, EXATAMENTE como recebido.

NÃO responda com texto além da chamada da tool.
NÃO escreva a chamada como código Python descritivo (ex: NÃO escreva
`default_api.tool_salvar_relatorio(...)` como texto). FAÇA a function call real.
NÃO modifique o conteúdo da análise — apenas persista.
"""

_review_persister = LlmAgent(
    model=_model,
    name="cr_review_persister",
    description="Fase 2 de revisão: persiste o relatório produzido pelo analyzer.",
    instruction=_REVIEW_PERSISTER_INSTRUCTION,
    output_key="review",
    tools=[
        _bind(FunctionTool(tool_salvar_relatorio), _REVIEW_WS),
    ],
)
```

Pontos-chave:
- `{review_analysis}` no instruction — ADK substitui automaticamente pelo valor de `state['review_analysis']` produzido pelo analyzer (suportado pela API; ver `llm_agent.py:218` "These instructions can contain placeholders like {variable_name} that will be resolved at runtime using session state and context")
- Single tool — `tool_salvar_relatorio`. Sem `tool_ler_arquivo`, sem `gerar_doubt_artifact`. O LLM não tem o que fazer além de chamar essa tool
- Anti-narração explícita no prompt — instrução literal de que escrever Python como texto não conta
- `output_key="review"` — preserva o nome que possíveis downstream consumers esperavam do `cr_review_agent` original

### A.6 — Compor `_reviewer` como SequentialAgent

```python
_reviewer = SequentialAgent(
    name="cr_review_agent",
    description="Pipeline de revisão em 2 fases: análise + persistência.",
    sub_agents=[_review_analyzer, _review_persister],
)
```

O símbolo `_reviewer` continua sendo referenciado em `agent = SequentialAgent(name="coding_review_pipeline", sub_agents=[_requirements, _coder, _reviewer])` (linha ~232). Nada muda no pipeline pai — apenas o `_reviewer` agora é um SequentialAgent transparente.

---

## 3. Section B — Por que isso resolve o bug

**Antes:** um único `LlmAgent` com 2 tools + prompt longo descrevendo análise + JSON literal de saída + "OBRIGATÓRIO ao fim chame tool_salvar_relatorio". O LLM tinha 3 caminhos plausíveis ao terminar de ler arquivos: (a) chamar `tool_salvar_relatorio`, (b) escrever JSON como texto, (c) escrever código Python descritivo. Em runs reais, escolheu (b) ou (c).

**Depois:**

- **Analyzer:** tem **apenas 1 tool** (`tool_ler_arquivo`). Prompt pede markdown, não JSON literal — não há "exemplo de saída" para o LLM completar como texto. Saída textual é o caminho esperado. Output via `output_key`.

- **Persister:** tem **apenas 1 tool** (`tool_salvar_relatorio`). Prompt tem 15 linhas. Não há análise pra produzir — a análise já está pronta, embutida no prompt via `{review_analysis}`. O LLM tem dois caminhos: (a) chamar `tool_salvar_relatorio`, (b) emitir texto vazio. Caminho (b) é trivialmente improvável quando há uma instrução clara + tool registrada + sem outro output esperado.

A separação de responsabilidades elimina o ambiente onde o LLM se "confunde" entre produzir-análise-em-texto e chamar-tool-de-save.

---

## 4. Section C — Comportamento E2E pós-fix

`workspace_output/review/verificacao_revisao.md` deve aparecer após cada run E2E que chegue até o pipeline de revisão. O conteúdo é o markdown produzido pelo analyzer, persistido literalmente.

O state final do `coding_review_pipeline` inclui:
- `state['requirements']` — output do analyzer de requisitos
- `state['implementation']` — output do coder
- `state['review_analysis']` — output do analyzer de revisão (novo)
- `state['review']` — output do persister (o conteúdo salvo + qualquer texto residual)

Pipelines downstream (qa_pipeline) que liam `state['review']` continuam funcionando.

---

## 5. Section D — Testes

### D.1 — Tests unit

**Reaproveitar** os 3 testes existentes em `adk/tests/unit/test_review_agent_persistence.py` que validam `_discover_coder_files` (Tasks 1 do plano anterior) — sem mudança.

**Refatorar** os 3 testes existentes que validam `_reviewer.instruction` e `_reviewer.tools`:
- `test_reviewer_instruction_provider_inclui_arquivos_descobertos` → agora valida `_review_analyzer.instruction` (callable que injeta lista de arquivos)
- `test_reviewer_instruction_contem_save_obrigatorio` → renomeia para `test_review_persister_instruction_referencia_analysis` e valida que o persister.instruction contém `{review_analysis}` + a string anti-narração `"FAÇA a function call real"`
- `test_reviewer_tool_ler_arquivo_esta_bound_ao_coder_ws` → agora valida `_review_analyzer.tools[0]` (tool_ler_arquivo) bound

**Adicionar 2 testes novos:**
- `test_reviewer_e_sequential_com_2_subagentes`: `isinstance(_reviewer, SequentialAgent)`, `len(_reviewer.sub_agents) == 2`, ordem correta (analyzer primeiro, persister depois)
- `test_review_persister_so_tem_tool_salvar_relatorio`: `len(_review_persister.tools) == 1`, e o único tool tem name contendo "salvar_relatorio". Garante que persister não tem `tool_ler_arquivo` (que poderia tentá-lo a re-ler arquivos)

Total final em `test_review_agent_persistence.py`: 8 testes (3 mantidos + 3 refatorados + 2 novos).

### D.2 — Validação E2E

```bash
bash .claude/skills/ai4es-e2e/scripts/diagnose.sh  # confirmar sem regressão de schema/tool
bash .claude/skills/ai4es-e2e/scripts/e2e.sh /tmp/photographer-prompt.md
bash .claude/skills/ai4es-e2e/scripts/inspect-run.sh
```

**Expected:**
- `workspace_output/review/verificacao_revisao.md` existe e tem markdown válido com seções `## Status`, `## Issues`, `## Resumo`
- `inspect-run.sh` lista `review (1)` em "Subpastas com conteúdo"

---

## 6. Não-objetivos

- **Não fazer com que o reviewer execute novas leituras durante a fase de persistência.** A análise já está pronta no `{review_analysis}` — persister só salva.
- **Não tocar `workflow_qa`.** Já foi corrigido no plano anterior; QA fica com o mesmo padrão `_PipelineOrchestrator` v5 + `invocar_planejamento_qa` wrapper.
- **Não generalizar o padrão "analyzer + persister" para outros agentes** (ex: coder, requirements). Avaliar caso a caso. Coder hoje não tem o mesmo problema — ele chama `tool_criar_arquivo` várias vezes sem narrar.
- **Não substituir o modelo (`ADK_LLM_MODEL`)** para resolver o problema. O fix arquitetural deve funcionar com `gemini-2.5-flash`; se não funcionar, próximo passo seria trocar de modelo (registrado como follow-up).
- **Não mudar `reviewer/prompt.py`** (top-level). Esse prompt ainda é usado pelo agente `reviewer` solto e pelo `workflow_coding` legado. Nosso fix é local ao `workflow_coding_review`.

---

## 7. Riscos e mitigações

| Risco | Probabilidade | Mitigação |
|---|---|---|
| ADK não substitui `{review_analysis}` automaticamente no instruction string | Baixa | Confirmado via grep em `llm_agent.py:218`: "These instructions can contain placeholders like {variable_name} that will be resolved at runtime using session state and context". Se falhar em runtime: fallback com `before_agent_callback` que lê `callback_context.state['review_analysis']` e re-monta o instruction |
| Persister também entra em modo narrador (escreve `default_api.tool_salvar_relatorio(...)` como texto) | Baixa | Prompt extremamente curto (15 linhas), única tool registrada, anti-narração explícita. Se falhar: fallback é substituir persister LlmAgent por um `before_agent_callback` direto no fim do analyzer que chama `tool_salvar_relatorio` programaticamente (zero LLM no save) |
| Markdown produzido pelo analyzer é gigantesco e estoura context window do persister | Baixa | Análise típica tem ~2-5KB de markdown. Janela do gemini-2.5-flash é 1M tokens. Mesmo análises de 100 arquivos cabem |
| Nested `SequentialAgent` dentro de `coding_review_pipeline` (outro SequentialAgent) cria conflito de parent | Baixa | ADK suporta. Cada `LlmAgent` continua tendo 1 parent (o `_reviewer` SequentialAgent). O `_reviewer` tem 1 parent (o `coding_review_pipeline`). Sem conflito |
| Output_key `review_analysis` colide com algum state existente em outros pipelines | Muito baixa | grep confirma que `review_analysis` não é usado em nenhum outro lugar do código |
| Latência dobra (2 LLM calls em vez de 1) | Certa quando dispara | Aceitável. Analyzer é call pesada (lê N arquivos, ~30-60s); persister é call trivial (1 tool call, ~3-5s). Total <70s. |

---

## 8. Resumo das mudanças

| Arquivo | Tipo | LOC |
|---|---|---|
| `adk/src/agents/workflow_coding_review/agent.py` | Edit | ~40 modificadas (renomeações + novo bloco persister + SequentialAgent compose) |
| `adk/tests/unit/test_review_agent_persistence.py` | Edit | ~30 modificadas (refactor 3 + add 2) |
| **Total** | | **~70 LOC** |

Nenhum schema mudou. Nenhum contrato público entre pipelines mudou (`cr_review_agent` continua existindo, ainda como agente que recebe entrada e produz `state['review']`). Wrapper de QA do plano anterior não é tocado.
