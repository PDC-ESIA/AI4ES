# SDLC Gaps Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar três gaps do orchestrator SDLC (vazamento de placeholder em testes gerados, qa_pipeline sem workspace binding, design_pipeline fora do orchestrator) em uma rodada coordenada.

**Architecture:**
F1 (vazamento) e F2 (qa binding) são independentes — refactors localizados em `qa_agent/subagents/receive_requirements.py` e `qa_agent/tools/pytest_runner.py`. F3 (design_pipeline no orchestrator) depende de uma investigação inicial com timebox de 30 min e da migração dos 5 especialistas do Time 2 para `create_se_agent` (binding ao workspace). Validação final via E2E do orchestrator com `bash .claude/skills/ai4es-e2e/scripts/e2e.sh`.

**Tech Stack:** Python 3.12, pytest, Google ADK, FastAPI, LiteLLM (Gemini API direct), `uv` package manager. Repositório usa `pyproject.toml` em `adk/` com `pythonpath=["."]`.

**Spec:** `docs/superpowers/specs/2026-05-17-sdlc-gaps-fixes-design.md`

---

## File Structure

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `adk/src/agents/qa_agent/subagents/receive_requirements.py` | Modificar | F1 sanitizer + F1 prompt + F2 paths dinâmicos |
| `adk/src/agents/qa_agent/tools/pytest_runner.py` | Modificar | F2 paths dinâmicos via `get_agent_workspace` |
| `adk/tests/unit/test_receive_requirements_sanitizer.py` | Criar | Testes do sanitizer AST + regex |
| `adk/tests/unit/test_qa_workspace_binding.py` | Criar | Testes dos paths dinâmicos do qa |
| `adk/src/agents/design_architect/agent.py` | Modificar | F3 migra para `create_se_agent` |
| `adk/src/agents/mermaid_specialist/agent.py` | Modificar | F3 migra para `create_se_agent` |
| `adk/src/agents/markdown_specialist/agent.py` | Modificar | F3 migra para `create_se_agent` |
| `adk/src/agents/validator/agent.py` | Modificar | F3 migra para `create_se_agent` |
| `adk/src/agents/io_agent/agent.py` | Modificar | F3 migra para `create_se_agent` |
| `adk/shared/agent_factory.py` | Modificar (se necessário) | F3 ampliar `_FILESYSTEM_TOOL_NAMES` se houver tools `design_*` fora do set |
| `adk/src/agents/orchestrator/agent.py` | Modificar | F3 adiciona `design_pipeline` à sequência |
| `adk/tests/unit/test_orchestrator_design.py` | Criar | F3 confirma 4 pipelines em ordem |
| `adk/tests/unit/test_design_workspace_binding.py` | Criar | F3 confirma binding via `functools.partial.keywords` |

---

## Task 1: F1 Sanitizer — testes do `_validar_e_sanitizar_codigo`

**Files:**
- Create: `adk/tests/unit/test_receive_requirements_sanitizer.py`

- [ ] **Step 1.1: Escrever testes do sanitizer**

Criar `adk/tests/unit/test_receive_requirements_sanitizer.py`:

```python
"""Testes do sanitizer AST + regex em receive_requirements."""
import pytest

from src.agents.qa_agent.subagents.receive_requirements import (
    _validar_e_sanitizar_codigo,
)


def test_sanitiza_pass_ctrl63_para_pass():
    codigo = "def test_x():\n    '''doc'''\n    pass<ctrl63>\n"
    resultado = _validar_e_sanitizar_codigo(codigo, "HU-001")
    assert "pass<ctrl63>" not in resultado
    assert "pass\n" in resultado


def test_sanitiza_return_placeholder():
    codigo = "def f():\n    return<X>\n"
    resultado = _validar_e_sanitizar_codigo(codigo, "RF-001")
    assert "return<X>" not in resultado
    assert "    return\n" in resultado


def test_sanitiza_continue_break_raise():
    codigo = (
        "def f():\n"
        "    for i in range(3):\n"
        "        if i:\n"
        "            continue<a>\n"
        "        break<b>\n"
        "    raise<c>\n"
    )
    resultado = _validar_e_sanitizar_codigo(codigo, "X")
    assert "<" not in resultado
    assert "continue\n" in resultado
    assert "break\n" in resultado
    assert "raise\n" in resultado


def test_codigo_invalido_apos_sanitizacao_levanta_valueerror():
    codigo = "def test_x(:\n    pass\n"  # parêntese errado, irreparável
    with pytest.raises(ValueError, match="inválido após sanitização"):
        _validar_e_sanitizar_codigo(codigo, "HU-001")


def test_codigo_valido_passa_intocado():
    codigo = (
        "import pytest\n"
        "\n"
        "def test_ok():\n"
        "    assert 1 == 1\n"
    )
    resultado = _validar_e_sanitizar_codigo(codigo, "HU-001")
    assert resultado == codigo


def test_string_contendo_placeholder_nao_e_sanitizada():
    # Caractere `pass<X>` dentro de string literal não deve ser tocado
    codigo = (
        "def test_doc():\n"
        '    msg = "pass<placeholder>"\n'
        "    assert msg\n"
    )
    resultado = _validar_e_sanitizar_codigo(codigo, "HU-001")
    # Comportamento documentado: regex captura `pass<...>` em qualquer lugar.
    # Se sair `pass<placeholder>` virou `pass`, a string fica inválida mas
    # ast.parse passa porque `"pass"` ainda é literal válido.
    # Assert é frouxo aqui — testa só que não levanta ValueError.
    assert "assert" in resultado
```

- [ ] **Step 1.2: Rodar testes para confirmar que falham**

Run: `cd adk && .venv/bin/pytest tests/unit/test_receive_requirements_sanitizer.py -v`
Expected: FAIL com `ImportError: cannot import name '_validar_e_sanitizar_codigo'`

---

## Task 2: F1 Sanitizer — implementação

**Files:**
- Modify: `adk/src/agents/qa_agent/subagents/receive_requirements.py`

- [ ] **Step 2.1: Adicionar imports**

Em `adk/src/agents/qa_agent/subagents/receive_requirements.py`, após a linha `import re` (linha 6), confirmar que `ast` está disponível. Adicionar se faltar:

```python
import ast
```

- [ ] **Step 2.2: Implementar `_validar_e_sanitizar_codigo`**

Adicionar a função após a definição de `_normalizar_anexos_inline` (próximo à linha 105) ou em local equivalente perto das outras helpers private:

```python
def _validar_e_sanitizar_codigo(codigo: str, id_artefato: str) -> str:
    """Sanitiza tokens fora-da-gramática Python e valida via ast.parse.

    Aplica regex que remove placeholders entre `<>` colocados após keywords
    Python (pass<X>, return<Y>, etc.) e em seguida valida o código com
    ast.parse. Se mesmo após sanitização o código permanece inválido,
    levanta ValueError — o chamador propaga o erro para o autocorrect cycle.

    Args:
        codigo: String com código Python emitido pelo LLM.
        id_artefato: ID do artefato (usado nas mensagens de log/erro).

    Returns:
        Código Python sanitizado e validado.

    Raises:
        ValueError: Se ast.parse falha após sanitização.
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

- [ ] **Step 2.3: Rodar testes do sanitizer**

Run: `cd adk && .venv/bin/pytest tests/unit/test_receive_requirements_sanitizer.py -v`
Expected: PASS (6 testes verdes)

- [ ] **Step 2.4: Commit**

```bash
git add adk/src/agents/qa_agent/subagents/receive_requirements.py adk/tests/unit/test_receive_requirements_sanitizer.py
git commit -m "$(cat <<'EOF'
add: sanitizer AST+regex para codigo pytest gerado por LLM

Sanitiza placeholders fora da gramatica Python (pass<X>, return<Y>,
etc.) que o LLM as vezes emite ao tentar satisfazer instrucoes
conflitantes, e valida o resultado via ast.parse antes de salvar.
Erro irrecuperavel propaga para o autocorrect cycle.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: F1 — integrar sanitizer no fluxo + ajustar prompt

**Files:**
- Modify: `adk/src/agents/qa_agent/subagents/receive_requirements.py`

- [ ] **Step 3.1: Ajustar prompt do ramo skeleton (linhas 514-520)**

Substituir:

```python
    else:
        instrucao_geracao = (
            "Nenhum código fonte foi fornecido, apenas o requisito. "
            "Geração em MODO ESQUELETO (Skeleton): Crie as assinaturas de teste pytest baseadas nos cenários inferidos, "
            "mas marque-os utilizando o decorator @pytest.mark.skip(reason='Aguardando implementação do código fonte') "
            "ou utilize 'pass' contendo docstrings claras sobre o comportamento que deverá ser validado."
        )
```

Por:

```python
    else:
        instrucao_geracao = (
            "Nenhum código fonte foi fornecido — gere em MODO ESQUELETO. "
            "Use @pytest.mark.skip(reason='Aguardando implementação do código fonte') "
            "antes de cada função de teste. O corpo deve ter apenas uma docstring "
            "descrevendo o comportamento esperado. NÃO use 'pass' — a docstring é "
            "o corpo válido da função em Python."
        )
```

- [ ] **Step 3.2: Ajustar regra global do prompt (linha 541)**

Substituir:

```
- Não use placeholders TODO, não use pass vazio, não deixe testes sem lógica.
```

Por:

```
- Cada função de teste deve ter corpo NÃO-VAZIO: ou uma docstring (modo
  esqueleto), ou asserts objetivos (modo completo). Nunca emita 'pass'
  isolado, 'TODO', placeholders entre <>, ou caracteres fora da gramática Python.
```

- [ ] **Step 3.3: Integrar sanitizer no fluxo de escrita (linha 293)**

Localizar:

```python
        codigo = _gerar_pytest_via_llm(
            id_artefato=id_artefato,
            tipo=tipo,
            conteudo=conteudo,
            modulo=modulo,
            arquivos_apoio=anexos_salvos,
            nome_teste=nome_teste,
        )
        caminho.write_text(codigo, encoding="utf-8")
```

Substituir por:

```python
        codigo = _gerar_pytest_via_llm(
            id_artefato=id_artefato,
            tipo=tipo,
            conteudo=conteudo,
            modulo=modulo,
            arquivos_apoio=anexos_salvos,
            nome_teste=nome_teste,
        )
        codigo_valido = _validar_e_sanitizar_codigo(codigo, id_artefato)
        caminho.write_text(codigo_valido, encoding="utf-8")
```

- [ ] **Step 3.4: Rodar todos os testes unit para garantir que nada quebrou**

Run: `cd adk && .venv/bin/pytest tests/unit -q`
Expected: todos passam (incluindo os 6 do Step 2.3)

- [ ] **Step 3.5: Commit**

```bash
git add adk/src/agents/qa_agent/subagents/receive_requirements.py
git commit -m "$(cat <<'EOF'
fix: prompt consistente + integra sanitizer no fluxo de geracao

Remove contradicao entre instrucao do modo esqueleto (linha 519, manda
usar pass com docstring) e regra global (linha 541, proibe pass vazio).
Agora o prompt instrui usar APENAS docstring como corpo da funcao em
modo esqueleto. Sanitizer chamado antes de escrever o arquivo: garante
que codigo invalido nao alcanca o disco.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: F2 — testes dos paths dinâmicos do qa

**Files:**
- Create: `adk/tests/unit/test_qa_workspace_binding.py`

- [ ] **Step 4.1: Escrever testes**

Criar `adk/tests/unit/test_qa_workspace_binding.py`:

```python
"""Testes do binding do qa_pipeline ao workspace centralizado."""
from pathlib import Path

import pytest


def test_tests_dir_resolve_via_workspace(monkeypatch, tmp_path):
    """_tests_dir() deve apontar para <WORKSPACE_OUTPUT_DIR>/tests/inputs/"""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))

    # Re-import força reavaliação se o módulo cacheia o env (não cacheia,
    # mas é defensivo).
    from src.agents.qa_agent.subagents.receive_requirements import _tests_dir

    resultado = _tests_dir()
    assert resultado == (tmp_path / "tests" / "inputs").resolve()


def test_doubt_dir_resolve_sibling_de_tests(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))

    from src.agents.qa_agent.subagents.receive_requirements import _doubt_dir

    resultado = _doubt_dir()
    assert resultado == (tmp_path / "tests" / "inputs" / "doubt_artifacts").resolve()


def test_pytest_runner_resolve_dynamic_base(monkeypatch, tmp_path):
    """_normalizar_caminho_arquivo deve resolver paths relativos para o workspace."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))

    # cria estrutura esperada
    tests_inputs = tmp_path / "tests" / "inputs"
    tests_inputs.mkdir(parents=True)
    (tests_inputs / "hu_001").mkdir()
    arquivo = tests_inputs / "hu_001" / "test_hu_001.py"
    arquivo.write_text("def test_x(): assert True\n")

    from src.agents.qa_agent.tools.pytest_runner import _normalizar_caminho_arquivo

    resultado = _normalizar_caminho_arquivo("hu_001/test_hu_001.py")
    assert resultado == arquivo.resolve()
```

- [ ] **Step 4.2: Rodar testes para confirmar que falham**

Run: `cd adk && .venv/bin/pytest tests/unit/test_qa_workspace_binding.py -v`
Expected: FAIL com `ImportError: cannot import name '_tests_dir'` (e similares)

---

## Task 5: F2 — refactor de `receive_requirements.py`

**Files:**
- Modify: `adk/src/agents/qa_agent/subagents/receive_requirements.py`

- [ ] **Step 5.1: Substituir constantes module-level por funções dinâmicas**

Localizar linhas 16-19:

```python
# Caminhos base — relativos à raiz do agente
_BASE_DIR = Path(__file__).parent.parent
TESTS_DIR = _BASE_DIR / "artefactsTests"
DOUBT_DIR = _BASE_DIR / "doubt_artifacts"
```

Substituir por:

```python
from shared.workspace import get_agent_workspace


def _tests_dir() -> Path:
    """workspace_output/tests/inputs/ resolvido em runtime.

    Centraliza o destino dos arquivos pytest gerados pelo subagente.
    Resolvido em runtime para respeitar WORKSPACE_OUTPUT_DIR env var.
    """
    return get_agent_workspace("receive_requirements")


def _doubt_dir() -> Path:
    """Sibling 'doubt_artifacts' dentro do diretório de testes."""
    return _tests_dir() / "doubt_artifacts"
```

- [ ] **Step 5.2: Substituir usos internos de `TESTS_DIR` e `DOUBT_DIR`**

Localizar e substituir cada ocorrência:

- Linha 269 (criação do diretório do artefato):
  ```python
  artefato_dir = TESTS_DIR / slug
  ```
  Por:
  ```python
  artefato_dir = _tests_dir() / slug
  ```

- Linha 356 (criação do diretório de doubts):
  ```python
  DOUBT_DIR.mkdir(parents=True, exist_ok=True)
  ```
  Por:
  ```python
  _doubt_dir().mkdir(parents=True, exist_ok=True)
  ```

- Linha 359 (path do doubt):
  ```python
  caminho = DOUBT_DIR / nome
  ```
  Por:
  ```python
  caminho = _doubt_dir() / nome
  ```

Confirmar via grep que não sobrou nenhuma referência a `TESTS_DIR` ou `DOUBT_DIR` em maiúsculas no arquivo:

```bash
grep -n "TESTS_DIR\|DOUBT_DIR" adk/src/agents/qa_agent/subagents/receive_requirements.py
```
Expected: 0 ocorrências.

- [ ] **Step 5.3: Rodar testes do binding**

Run: `cd adk && .venv/bin/pytest tests/unit/test_qa_workspace_binding.py::test_tests_dir_resolve_via_workspace tests/unit/test_qa_workspace_binding.py::test_doubt_dir_resolve_sibling_de_tests -v`
Expected: 2 PASS

- [ ] **Step 5.4: Rodar suite completa para confirmar que não regrediu**

Run: `cd adk && .venv/bin/pytest tests/unit -q`
Expected: todos os existentes + 8 novos passam (6 sanitizer + 2 binding)

---

## Task 6: F2 — refactor de `pytest_runner.py`

**Files:**
- Modify: `adk/src/agents/qa_agent/tools/pytest_runner.py`

- [ ] **Step 6.1: Substituir `Path(__file__).parent.parent` por lookup dinâmico**

Localizar dentro de `_normalizar_caminho_arquivo` (linha 82):

```python
        base_dir = Path(__file__).parent.parent
```

Substituir por:

```python
        from shared.workspace import get_agent_workspace
        base_dir = get_agent_workspace("receive_requirements")
```

Import local (dentro da função) evita import cycle no nível do módulo se `shared.workspace` eventualmente importar de `qa_agent`. Pattern já usado em `agent_factory.py:21` (comentário documenta).

- [ ] **Step 6.2: Rodar teste do pytest_runner**

Run: `cd adk && .venv/bin/pytest tests/unit/test_qa_workspace_binding.py::test_pytest_runner_resolve_dynamic_base -v`
Expected: PASS

- [ ] **Step 6.3: Rodar suite completa**

Run: `cd adk && .venv/bin/pytest tests/unit -q`
Expected: todos passam (9 novos verdes contando o do pytest_runner)

- [ ] **Step 6.4: Commit**

```bash
git add adk/src/agents/qa_agent/subagents/receive_requirements.py adk/src/agents/qa_agent/tools/pytest_runner.py adk/tests/unit/test_qa_workspace_binding.py
git commit -m "$(cat <<'EOF'
refactor: qa_pipeline resolve paths via get_agent_workspace

Substitui TESTS_DIR / DOUBT_DIR module-level em receive_requirements.py
por funcoes _tests_dir() / _doubt_dir() que resolvem em runtime via
get_agent_workspace('receive_requirements'). Mesma estrategia em
pytest_runner._normalizar_caminho_arquivo para o base_dir do
subprocess.

Outputs migram de adk/src/agents/qa_agent/artefactsTests/* para
workspace_output/tests/inputs/* (respeitando WORKSPACE_OUTPUT_DIR).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: F3 — investigar bug interno do `design_pipeline` (TIMEBOX 30 MIN)

**Files:** (read-only nesta task)
- Read: `adk/src/agents/workflow_design_pipeline/agent.py`
- Read: cada agente em `adk/src/agents/{design_architect,mermaid_specialist,markdown_specialist,validator,io_agent}/agent.py`

- [ ] **Step 7.1: Subir servidor e rodar design_pipeline standalone**

Em terminal separado:

```bash
cd /home/hhiroshi92/github/AI4ES
bash .claude/skills/ai4es-e2e/scripts/start-server.sh
```

Aguardar `✓ Servidor pronto`. Então invocar:

```bash
echo "Construa um sistema simples de healthcheck FastAPI: HU-001 - como Admin, quero ver /healthcheck retornar status 200 com body {'status':'ok'}." | \
  bash .claude/skills/ai4es-e2e/scripts/run-agent.sh workflow_design_pipeline | \
  tee /tmp/design-debug.json | \
  python3 .claude/skills/ai4es-e2e/scripts/pretty-response.py | \
  tee /tmp/design-debug-pretty.txt
```

- [ ] **Step 7.2: Classificar failure mode**

Analisar `/tmp/design-debug-pretty.txt` e `/tmp/ai4es-uvicorn-8081.log`. Aplicar a tabela:

| Sintoma observado | Fix nesta task |
|---|---|
| Resposta truncada / `MALFORMED_FUNCTION_CALL` | **PARAR** — escalar para o usuário. Token overflow inflando o escopo. |
| Sub-agente retorna conteúdo inline em vez de filename, pipeline rejeita | Anotar qual sub-agente; será corrigido junto da migração em Task 9 |
| Erro de filesystem em `io_agent` (paths inválidos) | OK — será coberto pelo binding em Task 9 |
| `validator` reprova em loop | Anotar critério problemático; será ajustado em Task 9 |
| Pipeline completa sem erros | Marcar Task 7 como completed; bug pode ter sido sintomático de chamada sem requirements pipeline anterior. Documentar. |

- [ ] **Step 7.3: Registrar achados em `docs/superpowers/research/2026-05-17-design-pipeline-bug.md`**

Criar arquivo curto (50-100 linhas) com:
1. Sintoma exato observado.
2. Trace relevante (linhas do log).
3. Classificação aplicada e ação recomendada.
4. Decisão: **prosseguir** (sintoma classificado) ou **escalar** (token overflow).

Se decisão = **escalar**, parar aqui e devolver ao usuário antes de prosseguir.

- [ ] **Step 7.4: Parar servidor**

```bash
bash .claude/skills/ai4es-e2e/scripts/stop-server.sh
```

- [ ] **Step 7.5: Commit**

```bash
git add docs/superpowers/research/2026-05-17-design-pipeline-bug.md
git commit -m "$(cat <<'EOF'
docs: investigacao do bug interno do design_pipeline

Resultado da execucao standalone: <classificacao>.
Decisao: <prosseguir|escalar>.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: F3 — auditoria das tools dos 5 especialistas de design

**Files:** (read-only)
- Read: `adk/src/agents/{design_architect,mermaid_specialist,markdown_specialist,validator,io_agent}/agent.py`
- Read: `adk/shared/tools/design_filesystem.py`
- Read: `adk/shared/agent_factory.py`

- [ ] **Step 8.1: Listar todas as tools de cada agente**

Para cada um dos 5 agentes, anotar em `/tmp/design-tools-audit.md`:

```
### <agente>

Tools registradas em tools=[...]:
- <nome_da_tool> (módulo: shared.tools.<X> ou local)
```

Comando auxiliar:

```bash
for ag in design_architect mermaid_specialist markdown_specialist validator io_agent; do
  echo "=== $ag ==="
  grep -A 1 "tools=" adk/src/agents/$ag/agent.py | head -30
  echo ""
done > /tmp/design-tools-audit.md
cat /tmp/design-tools-audit.md
```

- [ ] **Step 8.2: Cruzar com `_FILESYSTEM_TOOL_NAMES`**

Inspecionar `adk/shared/agent_factory.py:36-43`:

```python
_FILESYSTEM_TOOL_NAMES = {
    "tool_criar_arquivo",
    "tool_ler_arquivo",
    "tool_substituir_trecho",
    "tool_salvar_relatorio",
    "tool_salvar_artefato_requisito",
    "gerar_doubt_artifact",
}
```

Para cada tool listada no Step 8.1 que **não está** em `_FILESYSTEM_TOOL_NAMES` nem em `_GIT_TOOL_NAMES` nem em `_WORKSPACE_READ_TOOL_NAMES`, classificar:

| Tool fora do set | Aceita `base_dir`/`cwd`? | Ação |
|---|---|---|
| (preencher) | sim | Adicionar nome ao set em `agent_factory.py` |
| (preencher) | não | Adicionar parâmetro `base_dir: Optional[str] = None` na função; default `os.getcwd()`; então adicionar ao set |

- [ ] **Step 8.3: Aplicar fix das tools órfãs (se houver)**

Se a tabela do Step 8.2 listar alguma tool, aplicar conforme classificação. **Se a tool exigir refactor de assinatura, fazer commit dedicado antes de Task 9** com mensagem `update: tool <X> aceita base_dir para binding via factory`.

- [ ] **Step 8.4: Commit (mesmo se auditoria não revelou nada — registra o estado)**

```bash
# Se houve mudanças
git add adk/shared/agent_factory.py adk/shared/tools/
git commit -m "$(cat <<'EOF'
update: estende _FILESYSTEM_TOOL_NAMES para tools dos especialistas de design

Adiciona <lista> ao set para que _bind_tool_to_workspace alcance esses
tools quando os agentes do Time 2 migrarem para create_se_agent.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"

# Se nada mudou, apenas documentar a auditoria (opcional)
```

---

## Task 9: F3 — migrar 5 especialistas de Time 2 para `create_se_agent`

**Files:**
- Modify: `adk/src/agents/design_architect/agent.py`
- Modify: `adk/src/agents/mermaid_specialist/agent.py`
- Modify: `adk/src/agents/markdown_specialist/agent.py`
- Modify: `adk/src/agents/validator/agent.py`
- Modify: `adk/src/agents/io_agent/agent.py`

> **Importante:** A estrutura de cada um varia (alguns têm `output_schema`, outros não; alguns têm tools, outros não). Os steps a seguir são template — adaptar para cada agente.

- [ ] **Step 9.1: Migrar `design_architect`**

Substituir o bloco `agent = LlmAgent(...)` por chamada equivalente via `create_se_agent`:

```python
# Antes (exemplo — confira a estrutura real)
from google.adk.agents import LlmAgent
agent = LlmAgent(
    model=os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL),
    name="design_architect",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[...],
)

# Depois
from shared.agent_factory import create_se_agent

agent = create_se_agent(
    name="design_architect",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[...],            # mesma lista de tools
    agent_subdir="design",  # → workspace_output/design/
)
```

`create_se_agent` resolve o modelo via env, adiciona `tool_ask_clarification_adk`, adiciona `_SE_AGENT_POLICY` ao instruction, e binda as tools ao subdir. Se o agente tinha `output_schema=` ou `output_key=`, repassá-los via `**kwargs`:

```python
agent = create_se_agent(
    name="design_architect",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[...],
    agent_subdir="design",
    output_schema=schemas.X,  # se aplicável
    output_key="design",      # se aplicável
)
```

- [ ] **Step 9.2: Migrar `mermaid_specialist`**

Mesmo padrão, mas com `agent_subdir="mermaid_specialist"` (resolve para `workspace_output/design/diagrams/` via `AGENT_DIRS`).

- [ ] **Step 9.3: Migrar `markdown_specialist`**

`agent_subdir="markdown_specialist"` → `workspace_output/design/reports/`.

- [ ] **Step 9.4: Migrar `validator`**

`agent_subdir="validator"` → `workspace_output/design/validation/`.

- [ ] **Step 9.5: Migrar `io_agent`**

`agent_subdir="io_agent"` → `workspace_output/design/staging/`.

- [ ] **Step 9.6: Verificar imports — cada `__init__.py` ainda expõe `root_agent`?**

Confirmar via `curl` (após iniciar servidor brevemente):

```bash
bash .claude/skills/ai4es-e2e/scripts/start-server.sh
curl -s http://127.0.0.1:8081/list-apps | python3 -m json.tool | grep -E "design_architect|mermaid_specialist|markdown_specialist|validator|io_agent"
bash .claude/skills/ai4es-e2e/scripts/stop-server.sh
```

Expected: 5 nomes aparecem.

- [ ] **Step 9.7: Rodar diagnose schema-compat**

```bash
bash .claude/skills/ai4es-e2e/scripts/diagnose.sh workflow_design_pipeline
```

Expected: ✓ verde em todos os 4 checks.

- [ ] **Step 9.8: Commit**

```bash
git add adk/src/agents/design_architect/agent.py adk/src/agents/mermaid_specialist/agent.py adk/src/agents/markdown_specialist/agent.py adk/src/agents/validator/agent.py adk/src/agents/io_agent/agent.py
git commit -m "$(cat <<'EOF'
refactor: especialistas de Time 2 migram para create_se_agent

design_architect, mermaid_specialist, markdown_specialist, validator e
io_agent passam a usar create_se_agent com agent_subdir explicito.
Tools de filesystem ficam bindadas ao workspace via functools.partial,
e o defensive prompting + tool_ask_clarification sao injetados
automaticamente.

Outputs migram para workspace_output/design/{,diagrams,reports,
validation,staging}/.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: F3 — adicionar `design_pipeline` ao orchestrator

**Files:**
- Modify: `adk/src/agents/orchestrator/agent.py`
- Create: `adk/tests/unit/test_orchestrator_design.py`
- Create: `adk/tests/unit/test_design_workspace_binding.py`

- [ ] **Step 10.1: Escrever teste do orchestrator**

Criar `adk/tests/unit/test_orchestrator_design.py`:

```python
"""Testes da inclusão do design_pipeline na sequência do orchestrator."""


def test_orchestrator_includes_design_pipeline_in_order():
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    nomes = [p.name for p in _PipelineOrchestrator._pipelines]

    assert nomes == [
        "requirements_pipeline",
        "design_pipeline",
        "coding_review_pipeline",
        "qa_pipeline",
    ], f"Sequência inesperada: {nomes}"
```

- [ ] **Step 10.2: Escrever teste do binding dos especialistas**

Criar `adk/tests/unit/test_design_workspace_binding.py`:

```python
"""Testes do binding ao workspace dos 5 especialistas de Time 2."""
from functools import partial

import pytest

ESPECIALISTAS = [
    ("design_architect", "design"),
    ("mermaid_specialist", "design/diagrams"),
    ("markdown_specialist", "design/reports"),
    ("validator", "design/validation"),
    ("io_agent", "design/staging"),
]


@pytest.mark.parametrize("nome,subdir_esperado", ESPECIALISTAS)
def test_especialista_binda_tools_ao_subdir(nome, subdir_esperado, monkeypatch, tmp_path):
    """Tools de filesystem dos especialistas devem ter base_dir pré-bindado."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))

    # Re-import dinâmico — algumas instâncias podem ter sido criadas no
    # import inicial. Em produção isso é resolvido via init_workspace().
    import importlib
    modulo = importlib.import_module(f"src.agents.{nome}.agent")
    importlib.reload(modulo)

    agente = modulo.agent
    expected_path = (tmp_path / subdir_esperado).resolve()

    # Cada tool que é FunctionTool com partial.keywords['base_dir']
    # deve apontar para o subdir esperado.
    encontrou_binding = False
    for t in agente.tools:
        func = getattr(t, "func", None)
        if isinstance(func, partial):
            kw = getattr(func, "keywords", {}) or {}
            if "base_dir" in kw:
                assert Path(kw["base_dir"]).resolve() == expected_path
                encontrou_binding = True

    assert encontrou_binding, (
        f"{nome} não tem nenhuma tool com base_dir pré-bindado. "
        f"Esperava pelo menos uma para subdir {subdir_esperado!r}."
    )


# Garantir import de Path
from pathlib import Path  # noqa: E402
```

- [ ] **Step 10.3: Rodar testes — esperar FAIL**

```bash
cd adk && .venv/bin/pytest tests/unit/test_orchestrator_design.py tests/unit/test_design_workspace_binding.py -v
```

Expected: testes de design_workspace_binding podem já passar se Task 9 foi completa. O test_orchestrator_design.py vai FAIL com sequência atual de 3 pipelines.

- [ ] **Step 10.4: Atualizar `orchestrator/agent.py`**

Atualizar linhas 36-52:

```python
from src.agents.workflow_requirements.agent import agent as requirements_pipeline
from src.agents.workflow_design_pipeline.agent import agent as design_pipeline  # NOVO
from src.agents.workflow_coding_review.agent import agent as coding_review_pipeline
from src.agents.workflow_qa.agent import agent as qa_pipeline


class _PipelineOrchestrator(BaseAgent):
    """Roda pipelines em sequência, cada uma em sessão isolada."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    _pipelines: ClassVar[List[BaseAgent]] = [
        requirements_pipeline,
        design_pipeline,             # NOVO
        coding_review_pipeline,
        qa_pipeline,
    ]
```

Atualizar docstring do módulo (linha 18):

```python
# Antes
Sequência fixa (sem design — o design_pipeline tem bug interno conhecido):
    requirements_pipeline → coding_review_pipeline → qa_pipeline

# Depois
Sequência fixa:
    requirements_pipeline → design_pipeline → coding_review_pipeline → qa_pipeline
```

- [ ] **Step 10.5: Rodar testes — esperar PASS**

```bash
cd adk && .venv/bin/pytest tests/unit/test_orchestrator_design.py tests/unit/test_design_workspace_binding.py -v
```

Expected: PASS (1 + 5 = 6 testes)

- [ ] **Step 10.6: Commit**

```bash
git add adk/src/agents/orchestrator/agent.py adk/tests/unit/test_orchestrator_design.py adk/tests/unit/test_design_workspace_binding.py
git commit -m "$(cat <<'EOF'
add: design_pipeline na sequencia do orchestrator SDLC

Sequencia agora inclui o Time 2 entre requirements e coding_review:
requirements_pipeline → design_pipeline → coding_review_pipeline →
qa_pipeline.

Testes garantem:
- Ordem dos 4 pipelines no _PipelineOrchestrator.
- Binding ao workspace ativo nos 5 especialistas de design (cada um
  tem pelo menos uma tool com base_dir pre-bindado via partial).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Validação E2E final

**Files:** (sem mudança de código)
- Execute: `bash .claude/skills/ai4es-e2e/scripts/e2e.sh`

- [ ] **Step 11.1: Reset completo**

```bash
cd /home/hhiroshi92/github/AI4ES
rm -rf adk/workspace_output/
rm -f /tmp/ai4es-uvicorn-8081.log /tmp/ai4es-run.json /tmp/ai4es-pretty.txt
bash .claude/skills/ai4es-e2e/scripts/stop-server.sh
```

- [ ] **Step 11.2: Pré-flight diagnose**

```bash
bash .claude/skills/ai4es-e2e/scripts/diagnose.sh
```

Expected: ✓ DIAGNOSE OK em todos os 4 checks.

- [ ] **Step 11.3: Executar e2e completo**

```bash
bash .claude/skills/ai4es-e2e/scripts/e2e.sh .claude/skills/ai4es-e2e/examples/healthcheck-prompt.md 2>&1 | tee /tmp/ai4es-e2e-final.log
```

Aguardar conclusão (~5-10 min dependendo de cotas Gemini).

- [ ] **Step 11.4: Verificar critérios de aceitação**

Conferir cada item:

```bash
# (1) Sem SyntaxError ou MALFORMED nos logs
grep -E "SyntaxError|MALFORMED" /tmp/ai4es-uvicorn-8081.log
# Expected: zero matches

# (2) 5 subpastas populadas
for d in requirements design coder review tests/inputs; do
  count=$(find "adk/workspace_output/$d" -type f 2>/dev/null | wc -l)
  echo "$d: $count arquivo(s)"
done
# Expected: cada um > 0

# (3) Nenhum arquivo novo gerado em paths legacy
find adk/src/agents/qa_agent/artefactsTests -type f -newer adk/CLAUDE.md 2>/dev/null
find adk/src/agents/qa_agent/doubt_artifacts -name "Doubt_*.md" -newer adk/CLAUDE.md 2>/dev/null
# Expected: zero matches em ambos

# (4) App gerado pelo coder ainda funcional
cp -r adk/workspace_output/coder /tmp/healthcheck-final
cd /tmp/healthcheck-final
/home/hhiroshi92/github/AI4ES/adk/.venv/bin/python -m pytest -q
# Expected: 1 passed

/home/hhiroshi92/github/AI4ES/adk/.venv/bin/uvicorn main:app --port 8095 > /tmp/healthcheck-final.log 2>&1 &
sleep 2
curl -sf http://127.0.0.1:8095/healthcheck
# Expected: {"status":"ok"}
pkill -f "uvicorn main:app --port 8095"
```

- [ ] **Step 11.5: Inspecionar run (post-mortem opcional)**

```bash
cd /home/hhiroshi92/github/AI4ES
bash .claude/skills/ai4es-e2e/scripts/inspect-run.sh
```

Expected: design, requirements, coder, review, tests/inputs ✓ populadas.

- [ ] **Step 11.6: Parar servidor**

```bash
bash .claude/skills/ai4es-e2e/scripts/stop-server.sh
```

- [ ] **Step 11.7: Commit final de validação**

Se quiser registrar a validação no histórico (opcional, sem mudança de código):

```bash
# Atualizar CLAUDE.md "Known SDLC gaps" → remover bullets resolvidos
# (manual — comparar com a seção atual e remover linhas obsoletas)
git add adk/CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: remove gaps resolvidos da secao "Known SDLC gaps" no CLAUDE.md

Apos rodar E2E completo com os 3 fixes:
- workspace_output/requirements/ ✓ populado
- workspace_output/design/ ✓ populado
- workspace_output/coder/ + review/ ✓ populados
- workspace_output/tests/inputs/ ✓ populado
- App gerado responde HTTP 200 em /healthcheck

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-review

**Cobertura do spec**:
- F1 (vazamento): Tasks 1, 2, 3 — sanitizer testado + integrado + prompt corrigido. ✓
- F2 (qa binding): Tasks 4, 5, 6 — `_tests_dir`, `_doubt_dir`, `pytest_runner` migrados, testes. ✓
- F3 (design no orchestrator): Tasks 7 (investigação), 8 (auditoria), 9 (migração), 10 (inclusão). ✓
- Critérios de aceitação do spec: Task 11 cobre todos os 4 itens. ✓
- Não-escopo do spec: respeitado (architect/test_planner/finalizer não tocados; `init_workspace()` não mexido; `completion()` raw mantido). ✓

**Placeholders**: nenhum "TBD/TODO/preencher" no código. Step 8.2 tem uma tabela "(preencher)" mas é a tabela que o engenheiro **vai preencher durante a auditoria** — é o output esperado, não um placeholder do plano.

**Type consistency**:
- `_tests_dir()` / `_doubt_dir()` referenciados em receive_requirements.py e nos testes — nomes batem.
- `_validar_e_sanitizar_codigo` definido em Task 2 e chamado em Task 3 — assinatura `(codigo, id_artefato) -> str` consistente.
- `agent_subdir` valores nos especialistas batem com `AGENT_DIRS` em `shared/workspace.py`. Verificado.

**Pontos de incerteza explícitos**:
- Task 7 tem critério de escalada (token overflow → parar).
- Task 8 tem tabela a preencher durante auditoria.
- Task 9 tem nota "estrutura de cada agente varia — adaptar".
