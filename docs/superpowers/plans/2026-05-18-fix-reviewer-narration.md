# Fix Reviewer Narration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Quebrar o `cr_review_agent` (atualmente um `LlmAgent` único) em `SequentialAgent[_review_analyzer, _review_persister]` para eliminar o bug onde o LLM (gemini-2.5-flash) narra a chamada de `tool_salvar_relatorio` como texto Python em vez de executá-la. Spec: `docs/superpowers/specs/2026-05-18-fix-reviewer-narration-design.md`.

**Architecture:** Analyzer lê arquivos (1 tool: `tool_ler_arquivo`) e produz markdown em `state['review_analysis']`. Persister recebe esse markdown via placeholder `{review_analysis}` no `instruction` (substituição automática do ADK) e tem 1 tool (`tool_salvar_relatorio`) com 1 instrução de ação única. Sem espaço para narração: o analyzer não tem save tool, o persister não tem análise para narrar.

**Tech Stack:** Python 3.12, Google ADK (`LlmAgent`, `SequentialAgent`, `FunctionTool`), pytest + pytest-asyncio.

---

## File Structure

Arquivos modificados:
- `adk/src/agents/workflow_coding_review/agent.py` — refactor do bloco do `_reviewer` (atualmente linhas ~161-223 após o plano anterior): renomeia template/provider, cria `_review_analyzer` + `_review_persister`, compõe `_reviewer = SequentialAgent([...])`
- `adk/tests/unit/test_review_agent_persistence.py` — refactor de 3 testes existentes (que referenciam `_reviewer.instruction` / `_reviewer.tools`) + add 2 novos (composição do SequentialAgent + persister só tem 1 tool)

Nenhum arquivo novo. Nenhuma mudança em outros pipelines.

Boundaries:
- `_review_analyzer` e `_review_persister` são `LlmAgent`s independentes — cada um com escopo claro: análise vs. persistência
- `_reviewer` continua sendo o símbolo público referenciado pelo pipeline pai (linha ~232 hoje: `agent = SequentialAgent(name="coding_review_pipeline", sub_agents=[_requirements, _coder, _reviewer])`). Agora é `SequentialAgent` em vez de `LlmAgent` — mas transparente para o pipeline pai

---

## Task 1: Atualizar testes (RED) — refactor 3 + add 2

**Files:**
- Modify: `/home/hhiroshi92/github/AI4ES/adk/tests/unit/test_review_agent_persistence.py`

Os 3 testes que validam `_reviewer.instruction` e `_reviewer.tools` precisam ser refatorados — após Task 2, `_reviewer` será `SequentialAgent` (sem `.instruction` ou `.tools` direto). Plus 2 testes novos.

- [ ] **Step 1: Substituir o teste `test_reviewer_instruction_provider_inclui_arquivos_descobertos`**

Localizar o teste existente (atualmente refere a `wcr._reviewer.instruction`) e substituir por:

```python
def test_review_analyzer_instruction_provider_inclui_arquivos_descobertos(tmp_path, monkeypatch):
    """O instruction provider do _review_analyzer chama _discover_coder_files e injeta no template."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    # Cria arquivos APÓS o reload (init_workspace pode resetar o diretório)
    coder_ws = Path(wcr._CODER_WS)
    coder_ws.mkdir(parents=True, exist_ok=True)
    (coder_ws / "app").mkdir(exist_ok=True)
    (coder_ws / "app" / "main.py").write_text("# main")

    instr = wcr._review_analyzer.instruction
    if callable(instr):
        class _FakeCtx:
            pass
        rendered = instr(_FakeCtx())
        if hasattr(rendered, "__await__"):
            import asyncio
            rendered = asyncio.get_event_loop().run_until_complete(rendered)
    else:
        rendered = instr

    assert "- app/main.py" in rendered
```

- [ ] **Step 2: Substituir o teste `test_reviewer_instruction_contem_save_obrigatorio` por `test_review_persister_instruction_referencia_analysis`**

Localizar o teste existente (atualmente assert `OBRIGATÓRIO` + `tool_salvar_relatorio` em `_reviewer.instruction`) e substituir por:

```python
def test_review_persister_instruction_referencia_analysis_e_anti_narracao(tmp_path, monkeypatch):
    """Persister.instruction referencia {review_analysis} e tem texto anti-narração."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    instr = wcr._review_persister.instruction
    # Persister.instruction é string estática com placeholder {review_analysis}
    assert isinstance(instr, str)
    assert "{review_analysis}" in instr
    # Anti-narração explícita
    assert "FAÇA a function call real" in instr or "FAÇA a function call" in instr
    assert "tool_salvar_relatorio" in instr
```

- [ ] **Step 3: Substituir o teste `test_reviewer_tool_ler_arquivo_esta_bound_ao_coder_ws`**

Localizar o teste existente (atualmente itera `wcr._reviewer.tools`) e substituir por:

```python
def test_review_analyzer_tool_ler_arquivo_esta_bound_ao_coder_ws(tmp_path, monkeypatch):
    """tool_ler_arquivo do analyzer resolve paths relativos contra _CODER_WS."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    coder_ws = Path(wcr._CODER_WS)
    coder_ws.mkdir(parents=True, exist_ok=True)
    target_file = coder_ws / "test_file.py"
    target_file.write_text("CONTEUDO_ESPERADO")

    tools = wcr._review_analyzer.tools
    ler_tool = next(t for t in tools if "ler_arquivo" in t.func.__name__)
    result = ler_tool.func(caminho="test_file.py")
    assert isinstance(result, str)
    assert "CONTEUDO_ESPERADO" in result
    assert not result.startswith("Erro:")
```

- [ ] **Step 4: Adicionar 2 testes novos no final do arquivo**

Append:

```python
def test_reviewer_e_sequential_com_2_subagentes(tmp_path, monkeypatch):
    """_reviewer é SequentialAgent com 2 sub_agents: analyzer primeiro, persister depois."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from google.adk.agents import SequentialAgent
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    assert isinstance(wcr._reviewer, SequentialAgent)
    assert wcr._reviewer.name == "cr_review_agent"
    assert len(wcr._reviewer.sub_agents) == 2
    assert wcr._reviewer.sub_agents[0] is wcr._review_analyzer
    assert wcr._reviewer.sub_agents[1] is wcr._review_persister


def test_review_persister_so_tem_tool_salvar_relatorio(tmp_path, monkeypatch):
    """Persister tem exatamente 1 tool e ela é tool_salvar_relatorio."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    tools = wcr._review_persister.tools
    assert len(tools) == 1
    tool_name = tools[0].func.__name__
    assert "salvar_relatorio" in tool_name
```

- [ ] **Step 5: Run tests — 5 should FAIL with AttributeError**

Run:
```
cd /home/hhiroshi92/github/AI4ES/adk && .venv/bin/pytest tests/unit/test_review_agent_persistence.py -v
```

Expected: 3 PASS (`_discover_coder_files` tests do plano anterior, intocados) + 5 FAIL com mensagens como `AttributeError: module ... has no attribute '_review_analyzer'` ou `_review_persister`.

- [ ] **Step 6: Commit (red state — testes falham porque implementação ainda não existe)**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/tests/unit/test_review_agent_persistence.py
git commit -m "$(cat <<'EOF'
test: refactor testes do reviewer para SequentialAgent[analyzer, persister]

Atualiza 3 testes existentes (substituindo referências a _reviewer.instruction
/ _reviewer.tools por _review_analyzer e _review_persister) e adiciona 2 novos
(composição do SequentialAgent + persister só com 1 tool).

Estado RED: 5 testes falham porque _review_analyzer e _review_persister ainda
não existem. Task 2 implementa.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Implementar SequentialAgent[_review_analyzer, _review_persister] (GREEN)

**Files:**
- Modify: `/home/hhiroshi92/github/AI4ES/adk/src/agents/workflow_coding_review/agent.py` — refatorar o bloco do `_reviewer` (linhas ~161-223 após o plano anterior)

- [ ] **Step 1: Ler o estado atual do arquivo**

Antes de editar, ler o arquivo para confirmar localização das linhas:
```
cd /home/hhiroshi92/github/AI4ES/adk && grep -n "_REVIEWER_INSTRUCTION_TEMPLATE\|_reviewer_instruction_provider\|_reviewer = LlmAgent" src/agents/workflow_coding_review/agent.py
```

Expected: três matches mostrando a constante template, o provider function e o `_reviewer = LlmAgent(...)`.

- [ ] **Step 2: Renomear `_REVIEWER_INSTRUCTION_TEMPLATE` → `_REVIEW_ANALYZER_INSTRUCTION_TEMPLATE` e atualizar o conteúdo**

Localizar o bloco atual:

```python
_REVIEWER_INSTRUCTION_TEMPLATE = """
# PERFIL
Você é um Engenheiro de Software Sênior responsável por revisar código produzido por outro agente.
...
# FLUXO OBRIGATÓRIO
1. Para cada arquivo da lista acima, chame tool_ler_arquivo(caminho).
2. Avalie em 4 dimensões: COMPLETUDE, ARQUITETURA, CORRETUDE, TESTES.
   ...
3. **OBRIGATÓRIO ao fim**: chame tool_salvar_relatorio(nome_arquivo='verificacao_revisao.md', conteudo=<markdown>).
   Sem essa chamada, sua revisão NÃO é entregue — o pipeline falha mesmo que você produza texto.
...
# SAÍDA FINAL (texto retornado pelo agente, depois de salvar)
JSON único:
{
  "status": "APROVADO" | "BLOQUEADO",
  ...
}
"""
```

Substituir TODO o bloco por:

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

- [ ] **Step 3: Renomear `_reviewer_instruction_provider` → `_review_analyzer_instruction_provider`**

Localizar:

```python
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
```

Substituir por:

```python
def _review_analyzer_instruction_provider(_ctx) -> str:
    """InstructionProvider do ADK: resolve no momento da invocação.

    Garante que a lista de arquivos do coder esteja atualizada quando o
    analyzer é chamado (após o coder rodar, não no import do módulo).
    """
    return (
        _REVIEW_ANALYZER_INSTRUCTION_TEMPLATE
        .replace("__CODER_WS__", _CODER_WS)
        .replace("__FILES__", _discover_coder_files())
    )
```

- [ ] **Step 4: Substituir o bloco `_reviewer = LlmAgent(...)` por analyzer + persister + SequentialAgent**

Localizar o bloco atual:

```python
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

Substituir TODO o bloco por:

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


_reviewer = SequentialAgent(
    name="cr_review_agent",
    description="Pipeline de revisão em 2 fases: análise + persistência.",
    sub_agents=[_review_analyzer, _review_persister],
)
```

- [ ] **Step 5: Run tests — 8 should pass**

```
cd /home/hhiroshi92/github/AI4ES/adk && .venv/bin/pytest tests/unit/test_review_agent_persistence.py -v
```

Expected: 8 PASS (3 do plano anterior intocados + 5 que foram refatorados/adicionados na Task 1).

- [ ] **Step 6: Smoke-test do import do pipeline**

```
cd /home/hhiroshi92/github/AI4ES/adk && .venv/bin/python -c "
from src.agents.workflow_coding_review.agent import agent
from google.adk.agents import SequentialAgent
print('pipeline:', agent.name)
print('sub_agents:', [sa.name for sa in agent.sub_agents])
reviewer = next(sa for sa in agent.sub_agents if sa.name == 'cr_review_agent')
assert isinstance(reviewer, SequentialAgent), f'reviewer não é SequentialAgent: {type(reviewer)}'
print('reviewer sub_agents:', [sa.name for sa in reviewer.sub_agents])
print('analyzer tools:', [t.func.__name__ for t in reviewer.sub_agents[0].tools])
print('persister tools:', [t.func.__name__ for t in reviewer.sub_agents[1].tools])
"
```

Expected output:
```
pipeline: coding_review_pipeline
sub_agents: ['cr_requirements_agent', 'cr_coder_agent', 'cr_review_agent']
reviewer sub_agents: ['cr_review_analyzer', 'cr_review_persister']
analyzer tools: ['tool_ler_arquivo']
persister tools: ['tool_salvar_relatorio']
```

- [ ] **Step 7: Run full unit suite (regression check)**

```
cd /home/hhiroshi92/github/AI4ES/adk && .venv/bin/pytest tests/unit -q --tb=line 2>&1 | tail -10
```

Expected: All tests pass (195 + delta de novos testes ≥ 195). Sem regressões.

- [ ] **Step 8: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/src/agents/workflow_coding_review/agent.py
git commit -m "$(cat <<'EOF'
fix: quebra cr_review_agent em SequentialAgent[analyzer, persister]

Resolve o bug residual onde o LLM (gemini-2.5-flash) escrevia tool calls
como texto Python em vez de executá-los, nunca chamando tool_salvar_relatorio.

Analyzer (1 tool: tool_ler_arquivo) produz markdown de análise em
state['review_analysis']. Persister (1 tool: tool_salvar_relatorio) recebe
o markdown via placeholder {review_analysis} no instruction (substituição
automática do ADK) e tem instrução curta com anti-narração explícita.

Sem espaço para narração: analyzer não tem save tool, persister não tem
análise para produzir.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Validação E2E (sem commit)

**Files:** apenas execução — sem mudanças de código.

- [ ] **Step 1: Pre-flight diagnose**

```
bash /home/hhiroshi92/github/AI4ES/.claude/skills/ai4es-e2e/scripts/diagnose.sh
```

Expected: `✓ DIAGNOSE OK`. Se aparecer tools fantasmas (ex: prompt do persister cita `tool_salvar_relatorio` que ESTÁ registrada — OK) ou schemas problemáticos, reabrir Task 2.

- [ ] **Step 2: Confirmar que o prompt da Marina existe**

```
test -s /tmp/photographer-prompt.md && wc -l /tmp/photographer-prompt.md || echo "FALTA"
```

Expected: contém o prompt da Marina (criado em sessões anteriores).

- [ ] **Step 3: Reset do uvicorn (porta limpa) e rodar E2E**

```
lsof -ti:8081 | xargs -r kill -9 2>/dev/null; sleep 1
KEEP_UP=1 timeout 1500 bash /home/hhiroshi92/github/AI4ES/.claude/skills/ai4es-e2e/scripts/e2e.sh /tmp/photographer-prompt.md 2>&1 | tee /tmp/e2e-postfix-narration.log | tail -60
```

Expected: pipeline completa. `cr_review_analyzer` é invocado, faz chamadas reais a `tool_ler_arquivo`, produz markdown. `cr_review_persister` é invocado em seguida, chama `tool_salvar_relatorio`.

- [ ] **Step 4: Verificar que verificacao_revisao.md existe**

```
ls -la /home/hhiroshi92/github/AI4ES/adk/workspace_output/review/
```

Expected: `verificacao_revisao.md` listado, tamanho > 0.

- [ ] **Step 5: Verificar conteúdo do relatório**

```
head -30 /home/hhiroshi92/github/AI4ES/adk/workspace_output/review/verificacao_revisao.md
```

Expected: markdown com seções `## Status:`, `## Issues`, `## Resumo` (do template do analyzer).

- [ ] **Step 6: Confirmar via inspect-run.sh**

```
bash /home/hhiroshi92/github/AI4ES/.claude/skills/ai4es-e2e/scripts/inspect-run.sh
```

Expected: `review (1)` ou maior em "Subpastas com conteúdo".

- [ ] **Step 7: Parar o servidor**

```
bash /home/hhiroshi92/github/AI4ES/.claude/skills/ai4es-e2e/scripts/stop-server.sh
```

Expected: `Uvicorn na porta 8081 foi finalizado.`

- [ ] **Step 8: Sem commit nesta task — validação apenas**

Se o relatório NÃO aparecer:
- Procurar no log `/tmp/e2e-postfix-narration.log` por eventos com author `cr_review_persister` — confirma se o persister foi invocado
- Se ainda houver narração no persister: fallback do spec — substituir o LLM persister por um `before_agent_callback` programático que chama `tool_salvar_relatorio` direto (zero LLM no save). Esse fallback é tema de novo spec se necessário.

---

## Self-Review checklist (após execução)

- [ ] 8 testes em `test_review_agent_persistence.py` passam
- [ ] Suite unit inteira passa (regressão)
- [ ] Smoke-test do import retorna a estrutura esperada (SequentialAgent com 2 sub_agents nomeados)
- [ ] E2E gera `workspace_output/review/verificacao_revisao.md`
- [ ] Conteúdo do relatório tem markdown válido (não JSON literal, não código Python)
- [ ] Memória `project_review_agent_hallucination` pode ser atualizada para refletir resolução
