# Design — Workspace binding para `tool_salvar_artefato_requisito` e `gerar_doubt_artifact`

**Data:** 2026-05-17
**Branch alvo:** `feature/code/1-initial-project-setup`
**Escopo:** Fix de dois bugs do orchestrator SDLC que fazem com que artefatos do Time 1 (Requisitos) caiam fora do `workspace_output/`.

---

## 1. Problema

Após uma run completa do `orchestrator` (`requirements_pipeline → coding_review_pipeline → qa_pipeline`), o `inspect-run.sh` reporta:

- `workspace_output/coder/` populado (coder bind correto).
- `workspace_output/review/` populado.
- **`workspace_output/requirements/` vazio** — HUs/RFs/RNFs gerados pelo `requirements_agent` foram escritos em `docs/Time_1_Requisitos/{HUs,RFs,RNFs,RNs}/` no repo principal.
- **Doubt_Artifacts vão para `docs/Time_1_Requisitos/setup-ADK/AgenteAnalista/`** em vez de ficar junto do agente que os gerou.

Causas-raiz:

1. **`shared/tools/filesystem.py:266`** — `tool_salvar_artefato_requisito(tipo, id_req, conteudo_md)` hardcoda um `mapa_pastas` apontando para `docs/Time_1_Requisitos/...` e não aceita parâmetro `base_dir`. Mesmo se o agente fosse bound via `_bind_tool_to_workspace`, não há onde injetar.
2. **`shared/tools/doubt_generator_analista.py:17`** — `gerar_doubt_artifact(...)` tem parâmetro `caminho_base` mas com default `'docs/Time_1_Requisitos/setup-ADK/AgenteAnalista/'`. O LLM raramente passa esse parâmetro, então cai no default.

**Sintoma observável (memória do projeto):** "todas as pastas do workspace_output estão vazias, menos a do coder e a do review, isso precisa melhorar" — citação do usuário. Bloqueia auditoria do que cada Time produziu.

---

## 2. Não-objetivos

- Refatorar `requirements/agent.py` para usar `create_se_agent` (factory pattern). Permanece `LlmAgent` direto.
- Mover `init_workspace()` para um lifespan hook do FastAPI. Continua sendo invocado em import-time pelo `workflow_coding_review`.
- Mexer no `qa_agent` (que tem `gerar_doubt_artifact` própria em `qa_agent/tools/doubt_artifact.py` — outro escopo).
- Mexer no `_gerar_doubt_artifact_sincrono` do `pytest_runner.py` ou no `_gerar_doubt_artifact` do `receive_requirements.py` — internos do Time 3.
- Padronizar `AGENT_DIRS` para incluir `requirements/HUs`, `requirements/RFs` etc. Subdirs são criados on-demand pelo tool.

---

## 3. Mudanças

### 3.1 `shared/tools/filesystem.py` — `tool_salvar_artefato_requisito`

**Assinatura nova:**

```python
def tool_salvar_artefato_requisito(
    tipo: str,
    id_req: str,
    conteudo_md: str,
    base_dir: Optional[str] = None,
) -> str:
```

**Layout de subpastas (relativo ao `base_dir` quando setado, ou ao CWD quando `None`):**

| Tipo | Subdir | Nome do arquivo |
|------|--------|-----------------|
| `HU` | `HUs/` | `<id_req>.md` |
| `RF` | `RFs/` | `<id_req>.md` |
| `RNF` | `RNFs/` | `<id_req>.md` |
| `RN` | `RNs/` | `<id_req>.md` |
| `GLOSSARIO` | (raiz do base_dir) | `Glossario.md` |
| outro | `Outros/` | `<id_req>.md` |

**Resolução de caminho:**

- `base_dir=None` (legado): comportamento atual preservado — `Path("docs/Time_1_Requisitos/HUs").resolve()` (relativo ao CWD do servidor).
- `base_dir=<path>`: usa `_resolver_caminho(<subdir>/<filename>, base_dir)`, herdando proteção anti-traversal já existente (rejeita absolutos e `..`).

**Validações preservadas:**

- `ID_REQ_PATTERN.fullmatch` continua exigindo `AAAA-999` (exceto `GLOSSARIO`).
- Retorno permanece `str` ("SUCESSO: ..." ou "ERRO ao salvar artefato: ...").

### 3.2 `shared/tools/doubt_generator_analista.py` — `gerar_doubt_artifact`

**Renomear `caminho_base` → `base_dir`** e mudar default para `None`.

**Assinatura nova:**

```python
def gerar_doubt_artifact(
    id_duvida: str,
    id_artefato_afetado: str,
    trecho_contexto: str,
    duvida_descricao: str,
    motivo: str,
    impacto: str,
    bloqueante: bool = False,
    sugestao: Optional[str] = None,
    sessao: str = "001",
    contexto_geral: str = "Documentação de Requisitos",
    base_dir: Optional[str] = None,
) -> str:
```

**Resolução de caminho:**

- `base_dir=None`: fallback para o path legado `docs/Time_1_Requisitos/setup-ADK/AgenteAnalista/`.
- `base_dir=<path>`: escreve em `<base_dir>/Doubt_Artifact_<id>_<timestamp>.md` direto (sem subdir extra).

**Risco da renomeação:** Se algum LLM já estiver passando `caminho_base=...` explicitamente, vira `TypeError`. Mitigação: o `inspect-run.sh` da última run mostra 4 Doubt_Artifacts no path default, evidência empírica de que o parâmetro não é setado pelo LLM hoje.

**Conteúdo do markdown (cabeçalho + seção de dúvida):** intacto.

### 3.3 `shared/agent_factory.py` — `_FILESYSTEM_TOOL_NAMES`

Adicionar as duas tools ao set, para que a factory aplique `partial(..., base_dir=agent_workspace)` automaticamente quando um agente for criado via `create_se_agent(agent_subdir=...)`:

```python
_FILESYSTEM_TOOL_NAMES = {
    "tool_criar_arquivo",
    "tool_ler_arquivo",
    "tool_substituir_trecho",
    "tool_salvar_relatorio",
    "tool_salvar_artefato_requisito",  # novo
    "gerar_doubt_artifact",            # novo
}
```

### 3.4 `workflow_coding_review/agent.py` — bind manual

O `cr_requirements_agent` neste workflow é instanciado direto via `LlmAgent` (não via factory). Bind explícito:

```python
# antes (linhas 73-74):
FunctionTool(gerar_doubt_artifact),
FunctionTool(tool_salvar_artefato_requisito),

# depois:
_bind(FunctionTool(gerar_doubt_artifact), _REQ_WS),
_bind(FunctionTool(tool_salvar_artefato_requisito), _REQ_WS),
```

### 3.5 `requirements/agent.py` — bind manual

Este agente também não usa `create_se_agent`. Adicionar bind manual via `_bind_tool_to_workspace`:

```python
from shared.agent_factory import _bind_tool_to_workspace
from shared.workspace import get_agent_workspace, get_workspace_root

_WS_ROOT = str(get_workspace_root())
_REQ_WS = str(get_agent_workspace("requirements"))
_GLOS_WS = str(get_agent_workspace("glossario_agent"))

def _bind(tool, agent_ws):
    return _bind_tool_to_workspace(tool, agent_ws, _WS_ROOT)

# glossario_agent.tools — apenas gerar_doubt_artifact precisa de bind:
_bind(FunctionTool(gerar_doubt_artifact), _GLOS_WS),

# requirements_agent.tools:
_bind(FunctionTool(gerar_doubt_artifact), _REQ_WS),
_bind(FunctionTool(tool_salvar_artefato_requisito), _REQ_WS),
```

**Caveat conhecido:** `init_workspace()` só é invocado em import-time pelo `workflow_coding_review` e em testes. Como o `orchestrator` importa o `coding_review_pipeline`, o workspace é inicializado antes do `requirements_pipeline` rodar. Não é um bug novo introduzido por este fix; é uma fragilidade pré-existente fora do escopo.

---

## 4. Testes

Adicionar a `adk/tests/unit/` (arquivo novo `test_workspace_binding_tools.py` ou estender `test_filesystem_tools.py`):

**`tool_salvar_artefato_requisito`:**

1. Com `base_dir=<tmp>`: salva `HU-001` em `<tmp>/HUs/HU-001.md`.
2. Com `base_dir=<tmp>` e `tipo="GLOSSARIO"`: salva em `<tmp>/Glossario.md` (sem subdir extra).
3. Com `base_dir=<tmp>` e `tipo="DESCONHECIDO"`: salva em `<tmp>/Outros/<id>.md`.
4. Com `base_dir=None`: comportamento legado, escreve relativo ao CWD (em `tmp_path` via `monkeypatch.chdir`).
5. Com `base_dir=<tmp>` e `id_req="../etc/passwd"`: erro de validação (rejeitado por `ID_REQ_PATTERN` antes do path).
6. Com `base_dir=<tmp>` e `tipo` que mapeia para subdir contendo `..` (não há hoje, mas defensivo): cobertura pelo `_resolver_caminho`.

**`gerar_doubt_artifact`:**

7. Com `base_dir=<tmp>`: escreve em `<tmp>/Doubt_Artifact_<id>_<ts>.md`.
8. Com `base_dir=None`: fallback escreve em `docs/Time_1_Requisitos/setup-ADK/AgenteAnalista/` relativo ao CWD (validar via `monkeypatch.chdir` em tmp).
9. Conteúdo do markdown preserva cabeçalho + seção de dúvida formatados.

**Sanity contra Gemini API (manual, não automatizado):** rodar o snippet de inspeção de schema do `CLAUDE.md` ("Verificação rápida de schemas de tool") sobre o `coding_review` e `requirements_pipeline` antes de subir o servidor. Confirmar que `Optional[str]` em `base_dir` serializa como `nullable: true` (não vira `anyOf`).

---

## 5. Verificação E2E

Não-automatizada. Após apply:

1. `bash .claude/skills/ai4es-e2e/scripts/diagnose.sh` — pré-flight.
2. Subir o servidor e disparar o `orchestrator` com o prompt de teste do skill (`examples/fotografo-album-prompt.md`).
3. `bash .claude/skills/ai4es-e2e/scripts/inspect-run.sh` — esperar ver:
   - `workspace_output/requirements/HUs/*.md`, `RFs/*.md` etc. populados.
   - Doubt_Artifacts (se gerados) em `workspace_output/requirements/` (ou `workspace_output/requirements/glossario/` para os do sub-agente), **não** em `docs/Time_1_Requisitos/setup-ADK/AgenteAnalista/`.
   - `docs/Time_1_Requisitos/` no repo intocado por essa run.

---

## 6. Compatibilidade

- **Retrocompatível por construção:** `base_dir=None` mantém comportamento atual exato em ambas as tools. Qualquer agente/script externo que importe e chame essas tools sem passar `base_dir` continua escrevendo nos mesmos paths.
- **Breaking só em um caso:** se um LLM ou script passar `caminho_base=...` explicitamente como kwarg para `gerar_doubt_artifact` — evidência empírica diz que isso não acontece hoje. Documentar no commit.

---

## 7. Arquivos tocados

- `adk/shared/tools/filesystem.py` (assinatura + lógica de `tool_salvar_artefato_requisito`)
- `adk/shared/tools/doubt_generator_analista.py` (assinatura + rename)
- `adk/shared/agent_factory.py` (`_FILESYSTEM_TOOL_NAMES`)
- `adk/src/agents/workflow_coding_review/agent.py` (`_bind` nas duas tools)
- `adk/src/agents/requirements/agent.py` (import factory + `_bind` nas duas tools)
- `adk/tests/unit/test_workspace_binding_tools.py` (novo)

---

## 8. Ordem sugerida de commits

1. `update: tool_salvar_artefato_requisito aceita base_dir opcional`
2. `update: gerar_doubt_artifact renomeia caminho_base para base_dir`
3. `update: factory de agentes registra duas tools como filesystem-bound`
4. `fix: bind workspace nas tools de requisitos do workflow_coding_review`
5. `fix: bind workspace nas tools de requisitos do requirements_agent`
6. `test: cobertura de base_dir em tool_salvar_artefato_requisito e gerar_doubt_artifact`

Atômicos para permitir bisect se algo regredir em E2E.
