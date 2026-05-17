# Design — Fechamento dos gaps conhecidos do orchestrator SDLC

**Data:** 2026-05-17
**Status:** Proposta
**Autor:** Hugo Hiroshi (via brainstorming)
**Branch alvo:** `feature/code/1-initial-project-setup`
**Relacionado:**
- `docs/superpowers/specs/2026-05-16-orchestrator-sdlc-design.md` (orchestrator v3)
- `docs/superpowers/specs/2026-05-17-workspace-binding-requisitos-doubts-design.md` (binding Time 1)
- `CLAUDE.md` — seção "Gotchas e lições do orchestrator E2E"

---

## 1. Contexto

O orchestrator SDLC v3 (`adk/src/agents/orchestrator/agent.py`) roda em ponta-a-ponta hoje, mas três gaps documentados produzem entregas parciais:

1. **Vazamento de placeholder `pass<ctrl63>`** em testes gerados pelo `receber_requisitos`. Causa `SyntaxError` na coleta do pytest, dispara autocorrect, falha em 2 ciclos, encerra com Doubt Artifact.
2. **`workspace_output/tests/` vazio** após cada run. O `workflow_qa` escreve em `adk/src/agents/qa_agent/artefactsTests/` (path hardcoded module-level).
3. **Time 2 (design) fora do orchestrator**. `_pipelines` cobre só `requirements → coding_review → qa`. `workspace_output/design/` fica vazio. Comentário no orchestrator marca o `design_pipeline` como tendo "bug interno conhecido" — nunca investigado.

Este design fecha os três gaps em uma rodada coordenada.

### Não-escopo
- `architect`, `test_planner`, `finalizer` continuam fora do orchestrator. São agentes **schema-only** (`LlmAgent` com `output_schema` Pydantic, sem tools) — não persistem arquivos por design.
- `init_workspace()` em import-time do `workflow_coding_review` (gotcha conhecido: apaga `workspace_output` a cada run). Sai deste design.
- Substituir `litellm.completion()` raw por `LlmAgent` em `receive_requirements.py`. Refactor maior, sem retorno proporcional para os gaps acima.

---

## 2. F1 — Vazamento de placeholder `pass<ctrl63>`

### Causa-raiz

Prompt **contraditório** em `adk/src/agents/qa_agent/subagents/receive_requirements.py`:

- Linha 515-519 (ramo skeleton, sem código fonte): manda usar `pass` com docstring.
- Linha 541 (regra global): proíbe `pass` vazio.

O LLM, tentando satisfazer ambos, emite `pass<ctrl63>` (literalmente os 12 bytes ASCII `pass<ctrl63>`, code 63 = `?`). `ast.parse` rejeita, pytest collection falha.

### Mudanças

**Arquivo único:** `adk/src/agents/qa_agent/subagents/receive_requirements.py`

#### M1.1 — Prompt consistente

Linhas 515-520 (ramo skeleton):

```python
instrucao_geracao = (
    "Nenhum código fonte foi fornecido — gere em MODO ESQUELETO. "
    "Use @pytest.mark.skip(reason='Aguardando implementação do código fonte') "
    "antes de cada função de teste. O corpo deve ter apenas uma docstring "
    "descrevendo o comportamento esperado. NÃO use 'pass' — a docstring é "
    "o corpo válido da função em Python."
)
```

Linhas 540-541 (regra global):

```
- Cada função de teste deve ter corpo NÃO-VAZIO: ou uma docstring (modo
  esqueleto), ou asserts objetivos (modo completo). Nunca emita 'pass'
  isolado, 'TODO', placeholders entre <>, ou caracteres fora da
  gramática Python.
```

#### M1.2 — Validação AST + sanitização (defesa em profundidade)

Nova função em `receive_requirements.py`:

```python
import ast
import re

def _validar_e_sanitizar_codigo(codigo: str, id_artefato: str) -> str:
    """Sanitiza tokens fora-da-gramática e valida via ast.parse.

    Raises:
        ValueError: Se ast.parse falhar após sanitização. O chamador
                   propaga para o autocorrect cycle.
    """
    padrao = re.compile(r'\b(pass|return|continue|break|raise)<[^>\n]*>')
    sanitizado = padrao.sub(r'\1', codigo)

    if sanitizado != codigo:
        logger.warning(
            f"[QA] Sanitização aplicada em {id_artefato}: "
            f"removidos placeholders fora da gramática Python."
        )

    try:
        ast.parse(sanitizado)
    except SyntaxError as e:
        raise ValueError(
            f"Código gerado para {id_artefato} é inválido após sanitização: "
            f"{e.msg} (linha {e.lineno}). Será reciclado via autocorrect."
        ) from e

    return sanitizado
```

Substitui linha 293:

```python
codigo_valido = _validar_e_sanitizar_codigo(codigo, id_artefato)
caminho.write_text(codigo_valido, encoding="utf-8")
```

**Política**: sanitizer só repara sintaxe (`pass<X>` → `pass`). Validação semântica ("`pass` isolado viola guideline") fica com pytest collection — não é responsabilidade desta camada.

### Testes (TDD)

`adk/tests/unit/test_receive_requirements_sanitizer.py`:

- `test_sanitiza_pass_ctrl63_para_pass`: input `pass<ctrl63>` → output contém `pass` válido.
- `test_sanitiza_return_placeholder`: `return<X>` → `return`.
- `test_codigo_invalido_apos_sanitizacao_levanta_valueerror`: input com syntax error real → `ValueError`.
- `test_codigo_valido_passa_intocado`: input válido → output idêntico.

---

## 3. F2 — Workspace binding do qa_pipeline

### Causa-raiz

Dois pontos de hardcode:

1. `adk/src/agents/qa_agent/subagents/receive_requirements.py:17-19`:
   ```python
   _BASE_DIR = Path(__file__).parent.parent
   TESTS_DIR = _BASE_DIR / "artefactsTests"
   DOUBT_DIR = _BASE_DIR / "doubt_artifacts"
   ```
2. `adk/src/agents/qa_agent/tools/pytest_runner.py:82-88`: `base_dir = Path(__file__).parent.parent` dentro de `_normalizar_caminho_arquivo`.

Como são paths **module-level**, `_bind_tool_to_workspace` (que injeta `base_dir` via `functools.partial` nas tools registradas) não tem efeito.

### Mudanças

#### M2.1 — `receive_requirements.py`

Substituir linhas 16-19:

```python
from shared.workspace import get_agent_workspace

def _tests_dir() -> Path:
    """workspace_output/tests/inputs/ resolvido em runtime."""
    return get_agent_workspace("receive_requirements")

def _doubt_dir() -> Path:
    """Sibling 'doubt_artifacts' dentro do diretório de testes."""
    return _tests_dir() / "doubt_artifacts"
```

Substituições internas:
- linha 269: `artefato_dir = TESTS_DIR / slug` → `artefato_dir = _tests_dir() / slug`
- linha 356: `DOUBT_DIR.mkdir(...)` → `_doubt_dir().mkdir(...)`
- linha 359: `caminho = DOUBT_DIR / nome` → `caminho = _doubt_dir() / nome`

#### M2.2 — `pytest_runner.py`

Substituir dentro de `_normalizar_caminho_arquivo` (linha 82):

```python
# Antes
base_dir = Path(__file__).parent.parent

# Depois
from shared.workspace import get_agent_workspace
base_dir = get_agent_workspace("receive_requirements")
```

`cwd` do `subprocess.run` (linha 149) é derivado do path normalizado — segue automaticamente.

#### M2.3 — Confirmar `AGENT_DIRS`

`shared/workspace.py:45` já mapeia `"receive_requirements": "tests/inputs"`. Sem mudança.

### Resultado esperado

| Antes | Depois |
|---|---|
| `adk/src/agents/qa_agent/artefactsTests/hu_001/test_hu_001.py` | `workspace_output/tests/inputs/hu_001/test_hu_001.py` |
| `adk/src/agents/qa_agent/doubt_artifacts/Doubt_*.md` | `workspace_output/tests/inputs/doubt_artifacts/Doubt_*.md` |
| `pytest` rodando com `cwd=adk/src/agents/qa_agent/` | `pytest` rodando com `cwd=workspace_output/tests/inputs/` |

### Testes (TDD)

`adk/tests/unit/test_qa_workspace_binding.py`:

- `test_tests_dir_resolve_via_workspace`: `monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", tmp_path)` → `_tests_dir()` retorna `tmp_path / "tests/inputs"`.
- `test_artefato_escrito_no_workspace`: chama `_processar_artefato_async` com workspace mockado → confirma `.py` aparece sob `tmp_path/tests/inputs/`.
- `test_pytest_runner_resolve_dynamic_base`: workspace mockado → `_normalizar_caminho_arquivo("test_x.py")` retorna path absoluto sob `tmp_path`.

---

## 4. F3 — `design_pipeline` no orchestrator

### Mudança 1 — Inclusão na sequência

`adk/src/agents/orchestrator/agent.py`:

```python
from src.agents.workflow_design_pipeline.agent import agent as design_pipeline

_pipelines: ClassVar[List[BaseAgent]] = [
    requirements_pipeline,
    design_pipeline,         # NOVO — entre requirements e coding_review
    coding_review_pipeline,
    qa_pipeline,
]
```

Remover comentário "Sequência fixa (sem design — o design_pipeline tem bug interno conhecido)" no docstring do módulo (linha 18).

### Mudança 2 — Investigação obrigatória do "bug interno"

Antes de ativar `design_pipeline` no orchestrator, isolar o failure mode.

**Procedimento** (timebox 30 min):

```bash
bash .claude/skills/ai4es-e2e/scripts/start-server.sh
echo "Construa um endpoint /healthcheck simples..." | \
  bash .claude/skills/ai4es-e2e/scripts/run-agent.sh workflow_design_pipeline | \
  python3 .claude/skills/ai4es-e2e/scripts/pretty-response.py
```

Classificar o sintoma e aplicar o fix correspondente:

| Sintoma observado | Fix |
|---|---|
| Sub-agente devolve conteúdo inline em vez de filename, pipeline rejeita | Reforçar prompt do sub-agente afetado |
| Erro de filesystem em `io_agent` (path inválido) | Fix coberto pela Mudança 3 (binding) |
| Resposta truncada / `MALFORMED_FUNCTION_CALL` | Token overflow no pipeline LLM-orchestrated — **escalar**: pausar este design, replanejar para BaseAgent custom como o orchestrator atual |
| `validator` reprova em loop | Ajustar critérios do validator no prompt |

**Critério de escalada**: se o sintoma for token overflow ou `MALFORMED`, o fix infla o escopo (refactor de pipeline). Pausar e replanejar antes de prosseguir com F3.

### Mudança 3 — Binding dos 5 especialistas de design ao workspace

`design_pipeline` instancia `LlmAgent` direto (linha 79) com `AgentTool(agent=X)` para 5 especialistas. `AgentTool` não recebe binding — o binding tem que ir nos especialistas.

Cada um migra de `LlmAgent` direto → `create_se_agent(..., agent_subdir="<sub>")`:

| Agente | `agent_subdir` | Subpasta resultante |
|---|---|---|
| `design_architect` | `"design"` | `workspace_output/design/` |
| `mermaid_specialist` | `"mermaid_specialist"` | `workspace_output/design/diagrams/` |
| `markdown_specialist` | `"markdown_specialist"` | `workspace_output/design/reports/` |
| `validator` | `"validator"` | `workspace_output/design/validation/` |
| `io_agent` | `"io_agent"` | `workspace_output/design/staging/` |

Todos esses já estão em `AGENT_DIRS` (`shared/workspace.py:35-40`).

**Risco específico**: alguns agentes do Time 2 podem usar tools em `shared/tools/design_*` (`design_filesystem.py`, `design_validate/*`) que **não estão** em `_FILESYSTEM_TOOL_NAMES` (`shared/agent_factory.py:36-43`). Nesse caso `_bind_tool_to_workspace` passa por elas sem efeito.

**Mitigação**: o plano inclui uma sub-task de auditoria — inspecionar `tools=[...]` de cada um dos 5 agentes, identificar tools fora do set, e:
- (a) se a tool aceita `base_dir`/`cwd`: adicionar nome ao set apropriado em `agent_factory.py`.
- (b) se não aceita: adicionar parâmetro `base_dir: Optional[str] = None` à tool e default para `os.getcwd()`.

### Testes

`adk/tests/unit/test_orchestrator_design.py`:

- `test_orchestrator_includes_design_pipeline`: importa `root_agent`, confirma 4 pipelines em ordem (`requirements`, `design_pipeline`, `coding_review_pipeline`, `qa_pipeline`).

`adk/tests/unit/test_design_workspace_binding.py`:

- `test_design_specialists_use_create_se_agent`: importa cada um dos 5 especialistas, confirma que tools registradas têm `base_dir` pré-bindado (inspecionando `functools.partial.keywords`).

**Manual E2E**: rodar `bash .claude/skills/ai4es-e2e/scripts/e2e.sh examples/healthcheck-prompt.md` após os 3 fixes. Esperado:
- `workspace_output/requirements/` ✅ populado
- `workspace_output/design/` ✅ populado (era ❌)
- `workspace_output/coder/` ✅ populado
- `workspace_output/review/` ✅ populado
- `workspace_output/tests/inputs/` ✅ populado (era ❌)

---

## 5. Ordem de implementação e dependências

```
F1 (vazamento) ─┐
                ├──► F1+F2 destravam qa_pipeline ──► run E2E parcial
F2 (qa bind) ───┘                                       │
                                                        ▼
F3 mudança 2 (investigar bug design)              decisão escalada?
            │                                           │ não
            ▼                                           ▼
F3 mudança 3 (bind especialistas) ──► F3 mudança 1 (orchestrator) ──► run E2E completo
```

F1 e F2 são independentes — podem rodar em paralelo. F3 depende da investigação inicial e do binding dos especialistas. Ativação do `design_pipeline` no orchestrator é a última etapa.

## 6. Critérios de aceitação

1. Rodando `bash .claude/skills/ai4es-e2e/scripts/diagnose.sh` antes do E2E: ✅ verde.
2. `pytest adk/tests/` na branch: todos os testes novos passam.
3. Rodando `bash .claude/skills/ai4es-e2e/scripts/e2e.sh examples/healthcheck-prompt.md`:
   - Nenhum `SyntaxError` ou `MALFORMED_FUNCTION_CALL` nos logs.
   - 5 das subpastas de `workspace_output/` populadas: `requirements/`, `design/`, `coder/`, `review/`, `tests/inputs/`.
   - Nenhum arquivo novo gerado em `adk/src/agents/qa_agent/artefactsTests/` ou `adk/src/agents/qa_agent/doubt_artifacts/`.
4. Código gerado por `coder/` continua validável: `pytest` passa e `curl /healthcheck` retorna `HTTP 200 + {"status":"ok"}`.

## 7. Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Bug interno do `design_pipeline` é token overflow | Média | Alto (infla escopo) | Timebox 30 min + critério de escalada explícito (pausa o design) |
| Tools de `shared/tools/design_*` fora de `_FILESYSTEM_TOOL_NAMES` | Alta | Médio (binding incompleto) | Sub-task de auditoria no plano; padrão de fix definido |
| Sanitizer regex captura falsos-positivos em código válido | Baixa | Baixo (string em comentário) | Regex específico para `<...>` após keywords Python; testes cobrem casos |
| `get_agent_workspace` chamado antes de `init_workspace` | Baixa | Médio (path não existe ainda) | `init_workspace()` é chamado no import do `workflow_coding_review` antes do qa_pipeline rodar |

---

## 8. Não-implementado neste design (referências para próximos ciclos)

- Mover `init_workspace()` para FastAPI lifespan hook com flag `--keep`.
- Substituir `litellm.completion()` raw em `receive_requirements.py` por `LlmAgent`.
- Adicionar `architect`/`test_planner`/`finalizer` ao orchestrator (requer pipelines wrapper que persistam JSONs).
- Refatorar `workflow_coding` para isolamento por etapa (BaseAgent custom como o orchestrator).
