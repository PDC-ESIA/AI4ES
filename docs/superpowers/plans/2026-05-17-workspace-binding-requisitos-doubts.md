# Workspace Binding — Requisitos & Doubt Artifacts (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer com que `tool_salvar_artefato_requisito` e `gerar_doubt_artifact` respeitem o workspace centralizado quando bound via factory, de modo que rodadas do `orchestrator` populem `workspace_output/requirements/` em vez de poluir `docs/Time_1_Requisitos/`.

**Architecture:** Adicionar parâmetro `base_dir: Optional[str] = None` em ambas as tools com fallback ao path legado quando `None`. Registrar as duas em `_FILESYSTEM_TOOL_NAMES` para auto-bind via factory, e fazer bind manual nos dois agentes que instanciam `LlmAgent` direto (`workflow_coding_review` e `requirements/agent.py`). Comportamento legado preservado por construção.

**Tech Stack:** Python 3.12, pytest, Google ADK 1.20.0, Gemini 2.5 Flash. `pyproject.toml` define `pythonpath=["."]`, `asyncio_mode=auto`, `testpaths=tests`.

**Spec:** `docs/superpowers/specs/2026-05-17-workspace-binding-requisitos-doubts-design.md`

---

## File Structure

**Modify:**
- `adk/shared/tools/filesystem.py` — `tool_salvar_artefato_requisito(...)` aceita `base_dir`, novo mapa de subpastas relativo
- `adk/shared/tools/doubt_generator_analista.py` — `gerar_doubt_artifact(...)` renomeia `caminho_base` → `base_dir`, default `None`, fallback legado
- `adk/shared/agent_factory.py` — duas entradas novas no `_FILESYSTEM_TOOL_NAMES`
- `adk/src/agents/workflow_coding_review/agent.py` — `_bind` em `gerar_doubt_artifact` e `tool_salvar_artefato_requisito`
- `adk/src/agents/requirements/agent.py` — import workspace + `_bind` nas tools dos dois agentes (requirements + glossario)
- `adk/tests/unit/test_filesystem_base_dir.py` — append tests para `tool_salvar_artefato_requisito` com `base_dir`
- `adk/tests/unit/test_agent_factory_workspace.py` — append teste cobrindo o bind das duas tools novas
- `adk/tests/unit/test_filesystem_tools.py` — apagar marcador de merge órfão na linha 145 (unblocker do pytest collect)

**Create:**
- `adk/tests/unit/test_doubt_generator_base_dir.py` — testes para `gerar_doubt_artifact` com `base_dir`

**Convention:** Todos os comandos `pytest` rodam de `adk/` com `.venv/bin/pytest`. `pyproject.toml` já tem `pythonpath=["."]`, então imports `shared.X` funcionam direto.

---

## Task 0: Desbloquear pytest collection (orphan merge marker)

Pre-existe no repo desde o merge `7928834` — uma linha `<<<<<<< HEAD` órfã em `tests/unit/test_filesystem_tools.py:145` que impede o pytest de coletar testes. Sem isso, não conseguimos verificar nada.

**Files:**
- Modify: `adk/tests/unit/test_filesystem_tools.py:145`

- [ ] **Step 1: Verificar o sintoma**

```bash
cd adk
.venv/bin/pytest tests/unit/test_filesystem_tools.py --collect-only 2>&1 | tail -5
```

Expected output (confirma o bug):
```
E   SyntaxError: invalid syntax
ERROR tests/unit/test_filesystem_tools.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```

- [ ] **Step 2: Remover a linha órfã**

Edit `adk/tests/unit/test_filesystem_tools.py` removendo APENAS a linha 145 (a string literal `<<<<<<< HEAD`). Não tocar nada acima ou abaixo. Use o Edit tool:

```
old_string:
    def test_retorna_chaves_corretas_falha(self, diretorio):
        """Verifica contrato do dict em caso de falha."""
        result = tool_criar_arquivo("script.sh", "conteudo")
        assert {"sucesso", "erro", "caminho"}.issubset(result)
        assert result["sucesso"] is False
<<<<<<< HEAD


class TestSalvarArtefatoRequisitoSeguranca:

new_string:
    def test_retorna_chaves_corretas_falha(self, diretorio):
        """Verifica contrato do dict em caso de falha."""
        result = tool_criar_arquivo("script.sh", "conteudo")
        assert {"sucesso", "erro", "caminho"}.issubset(result)
        assert result["sucesso"] is False


class TestSalvarArtefatoRequisitoSeguranca:
```

- [ ] **Step 3: Verificar que pytest coleta o arquivo**

```bash
cd adk && .venv/bin/pytest tests/unit/test_filesystem_tools.py --collect-only 2>&1 | tail -5
```

Expected: lista de testes coletados, **sem** SyntaxError. Deve incluir ao menos `TestSalvarArtefatoRequisitoSeguranca::test_salva_artefato_com_id_valido`.

- [ ] **Step 4: Rodar a suite existente**

```bash
cd adk && .venv/bin/pytest tests/unit/test_filesystem_tools.py -v 2>&1 | tail -20
```

Expected: todos passam (essa suite estava broken por coleta, não por lógica).

- [ ] **Step 5: Commit**

```bash
git add adk/tests/unit/test_filesystem_tools.py
git commit -m "fix: remove marcador de merge orfao em test_filesystem_tools"
```

---

## Task 1: `tool_salvar_artefato_requisito` aceita `base_dir`

TDD — escrever testes primeiro mostrando o comportamento esperado.

**Files:**
- Modify: `adk/tests/unit/test_filesystem_base_dir.py` (append)
- Modify: `adk/shared/tools/filesystem.py` (função `tool_salvar_artefato_requisito` linhas 266-307)

- [ ] **Step 1: Escrever os testes falhando**

Anexar ao final de `adk/tests/unit/test_filesystem_base_dir.py`:

```python


# ============================================================================
# tool_salvar_artefato_requisito — base_dir opcional
# ============================================================================

from shared.tools.filesystem import tool_salvar_artefato_requisito


def test_salvar_artefato_sem_base_dir_mantem_path_legado(tmp_path, monkeypatch):
    """Retro-compat: sem base_dir, escreve em docs/Time_1_Requisitos/HUs/."""
    monkeypatch.chdir(tmp_path)
    result = tool_salvar_artefato_requisito("HU", "HU-001", "# HU-001\n")
    assert result.startswith("SUCESSO:")
    assert (tmp_path / "docs/Time_1_Requisitos/HUs/HU-001.md").is_file()


def test_salvar_artefato_com_base_dir_escreve_em_subpasta_HUs(tmp_path):
    """Com base_dir, HU vai em <base_dir>/HUs/<id>.md."""
    base = tmp_path / "ws_req"
    base.mkdir()
    result = tool_salvar_artefato_requisito(
        "HU", "HU-001", "# HU-001\n", base_dir=str(base)
    )
    assert result.startswith("SUCESSO:")
    assert (base / "HUs" / "HU-001.md").is_file()
    # NÃO escreveu em docs/Time_1_Requisitos
    assert not (tmp_path / "docs").exists()


def test_salvar_artefato_com_base_dir_para_RF_RNF_RN(tmp_path):
    """Cada tipo vai em sua subpasta dentro de base_dir."""
    base = tmp_path / "ws_req"
    base.mkdir()
    tool_salvar_artefato_requisito("RF", "RF-001", "x", base_dir=str(base))
    tool_salvar_artefato_requisito("RNF", "RNF-001", "x", base_dir=str(base))
    tool_salvar_artefato_requisito("RN", "RN-001", "x", base_dir=str(base))
    assert (base / "RFs" / "RF-001.md").is_file()
    assert (base / "RNFs" / "RNF-001.md").is_file()
    assert (base / "RNs" / "RN-001.md").is_file()


def test_salvar_glossario_com_base_dir_escreve_na_raiz(tmp_path):
    """GLOSSARIO vai direto em <base_dir>/Glossario.md, sem subdir."""
    base = tmp_path / "ws_glos"
    base.mkdir()
    result = tool_salvar_artefato_requisito(
        "GLOSSARIO", "IGNORADO", "# Glossário\n", base_dir=str(base)
    )
    assert result.startswith("SUCESSO:")
    assert (base / "Glossario.md").is_file()


def test_salvar_artefato_tipo_desconhecido_com_base_dir(tmp_path):
    """Tipo fora do mapa cai em <base_dir>/Outros/."""
    base = tmp_path / "ws"
    base.mkdir()
    result = tool_salvar_artefato_requisito(
        "DESCONHECIDO", "XX-001", "x", base_dir=str(base)
    )
    assert result.startswith("SUCESSO:")
    assert (base / "Outros" / "XX-001.md").is_file()


def test_salvar_artefato_com_base_dir_rejeita_id_traversal(tmp_path):
    """id_req com '..' continua bloqueado pelo ID_REQ_PATTERN."""
    base = tmp_path / "ws"
    base.mkdir()
    result = tool_salvar_artefato_requisito(
        "HU", "../../escape", "x", base_dir=str(base)
    )
    assert result.startswith("ERRO ao salvar artefato:")
    # Nada escapou
    assert not (tmp_path.parent / "escape.md").exists()
```

- [ ] **Step 2: Rodar os testes para confirmar que falham**

```bash
cd adk && .venv/bin/pytest tests/unit/test_filesystem_base_dir.py -v -k "salvar_artefato or glossario" 2>&1 | tail -20
```

Expected:
- `test_salvar_artefato_sem_base_dir_mantem_path_legado` — PASS (legado já funciona)
- `test_salvar_artefato_com_base_dir_*` — FAIL com `TypeError: tool_salvar_artefato_requisito() got an unexpected keyword argument 'base_dir'`

- [ ] **Step 3: Implementar a nova assinatura**

Substituir a função inteira em `adk/shared/tools/filesystem.py` (linhas 266-307). Use Edit:

```
old_string:
def tool_salvar_artefato_requisito(tipo: str, id_req: str, conteudo_md: str) -> str:
    """Salva um artefato de requisito (HU, RF, RNF, RN, Glossario).

    Args:
        tipo: Tipo do artefato (HU, RF, RNF, RN, Glossario)
        id_req: Identificador único do requisito (ex: HU-001, RF-002)
        conteudo_md: Conteúdo do artefato em formato Markdown
    """
    mapa_pastas = {
        "HU": "docs/Time_1_Requisitos/HUs",
        "RF": "docs/Time_1_Requisitos/RFs",
        "RNF": "docs/Time_1_Requisitos/RNFs",
        "RN": "docs/Time_1_Requisitos/RNs",
        "GLOSSARIO": "docs/Time_1_Requisitos",
    }

    tipo_normalizado = (tipo or "").strip().upper()
    id_req_normalizado = (id_req or "").strip()
    pasta_base = mapa_pastas.get(tipo_normalizado, "docs/Time_1_Requisitos/Outros")

    try:
        if tipo_normalizado != "GLOSSARIO":
            if not ID_REQ_PATTERN.fullmatch(id_req_normalizado):
                return "ERRO ao salvar artefato: id_req inválido. Use o padrão AAAA-999."

        nome_arquivo = f"{id_req_normalizado}.md" if tipo_normalizado != "GLOSSARIO" else "Glossario.md"

        pasta_base_path = Path(pasta_base).resolve()
        pasta_base_path.mkdir(parents=True, exist_ok=True)
        caminho_completo = (pasta_base_path / nome_arquivo).resolve()

        if (
            caminho_completo.parent != pasta_base_path
            and pasta_base_path not in caminho_completo.parents
        ):
            return "ERRO ao salvar artefato: caminho de saída inválido."

        caminho_completo.write_text(conteudo_md, encoding="utf-8")

        return f"SUCESSO: {tipo} {id_req} salvo em {caminho_completo}"
    except Exception as e:
        return f"ERRO ao salvar artefato: {str(e)}"

new_string:
# Layout legado: paths absolutos baseados no CWD.
_PASTAS_LEGADO = {
    "HU": "docs/Time_1_Requisitos/HUs",
    "RF": "docs/Time_1_Requisitos/RFs",
    "RNF": "docs/Time_1_Requisitos/RNFs",
    "RN": "docs/Time_1_Requisitos/RNs",
    "GLOSSARIO": "docs/Time_1_Requisitos",
}

# Layout relativo a base_dir (workspace-bound): apenas o subdir.
_SUBPASTAS_BASE_DIR = {
    "HU": "HUs",
    "RF": "RFs",
    "RNF": "RNFs",
    "RN": "RNs",
    "GLOSSARIO": "",  # vai direto na raiz do base_dir
}


def tool_salvar_artefato_requisito(
    tipo: str,
    id_req: str,
    conteudo_md: str,
    base_dir: Optional[str] = None,
) -> str:
    """Salva um artefato de requisito (HU, RF, RNF, RN, Glossario).

    Args:
        tipo: Tipo do artefato (HU, RF, RNF, RN, Glossario).
        id_req: Identificador único do requisito (ex: HU-001, RF-002).
        conteudo_md: Conteúdo do artefato em formato Markdown.
        base_dir: Diretório base do agente. Quando informado, escreve em
            ``<base_dir>/<subdir>/<id_req>.md`` (subdir varia por tipo).
            Quando None, mantém comportamento legado (escreve relativo ao
            CWD em ``docs/Time_1_Requisitos/...``).
    """
    tipo_normalizado = (tipo or "").strip().upper()
    id_req_normalizado = (id_req or "").strip()

    if tipo_normalizado != "GLOSSARIO":
        if not ID_REQ_PATTERN.fullmatch(id_req_normalizado):
            return "ERRO ao salvar artefato: id_req inválido. Use o padrão AAAA-999."

    nome_arquivo = (
        f"{id_req_normalizado}.md"
        if tipo_normalizado != "GLOSSARIO"
        else "Glossario.md"
    )

    try:
        if base_dir is None:
            # Caminho legado (CWD-relativo)
            pasta_base = _PASTAS_LEGADO.get(
                tipo_normalizado, "docs/Time_1_Requisitos/Outros"
            )
            pasta_base_path = Path(pasta_base).resolve()
            pasta_base_path.mkdir(parents=True, exist_ok=True)
            caminho_completo = (pasta_base_path / nome_arquivo).resolve()

            if (
                caminho_completo.parent != pasta_base_path
                and pasta_base_path not in caminho_completo.parents
            ):
                return "ERRO ao salvar artefato: caminho de saída inválido."
        else:
            # Caminho workspace-bound
            subdir = _SUBPASTAS_BASE_DIR.get(tipo_normalizado, "Outros")
            caminho_rel = f"{subdir}/{nome_arquivo}" if subdir else nome_arquivo
            caminho_completo = _resolver_caminho(caminho_rel, base_dir)
            caminho_completo.parent.mkdir(parents=True, exist_ok=True)

        caminho_completo.write_text(conteudo_md, encoding="utf-8")
        return f"SUCESSO: {tipo} {id_req} salvo em {caminho_completo}"
    except ValueError as e:
        return f"ERRO ao salvar artefato: {str(e)}"
    except Exception as e:
        return f"ERRO ao salvar artefato: {str(e)}"
```

- [ ] **Step 4: Rodar os novos testes (devem passar)**

```bash
cd adk && .venv/bin/pytest tests/unit/test_filesystem_base_dir.py -v -k "salvar_artefato or glossario" 2>&1 | tail -20
```

Expected: todos PASS (incluindo o de retrocompat).

- [ ] **Step 5: Rodar a suite inteira de filesystem para garantir zero regressão**

```bash
cd adk && .venv/bin/pytest tests/unit/test_filesystem_tools.py tests/unit/test_filesystem_base_dir.py -v 2>&1 | tail -30
```

Expected: todos PASS — inclusive os 4 testes existentes em `TestSalvarArtefatoRequisitoSeguranca`.

- [ ] **Step 6: Commit**

```bash
git add adk/shared/tools/filesystem.py adk/tests/unit/test_filesystem_base_dir.py
git commit -m "update: tool_salvar_artefato_requisito aceita base_dir opcional"
```

---

## Task 2: `gerar_doubt_artifact` renomeia `caminho_base` → `base_dir`

**Files:**
- Create: `adk/tests/unit/test_doubt_generator_base_dir.py`
- Modify: `adk/shared/tools/doubt_generator_analista.py` (função inteira)

- [ ] **Step 1: Escrever os testes**

Criar `adk/tests/unit/test_doubt_generator_base_dir.py`:

```python
"""Tests para gerar_doubt_artifact — base_dir opcional + fallback legado."""

from pathlib import Path

import pytest

from shared.tools.doubt_generator_analista import gerar_doubt_artifact


def _kwargs(**overrides):
    """Args mínimos para gerar_doubt_artifact."""
    base = dict(
        id_duvida="D-001",
        id_artefato_afetado="HU-001",
        trecho_contexto="trecho qualquer",
        duvida_descricao="dúvida X",
        motivo="motivo X",
        impacto="impacto X",
    )
    base.update(overrides)
    return base


def test_gerar_doubt_sem_base_dir_usa_path_legado(tmp_path, monkeypatch):
    """Sem base_dir, escreve em docs/Time_1_Requisitos/setup-ADK/AgenteAnalista/."""
    monkeypatch.chdir(tmp_path)
    caminho = gerar_doubt_artifact(**_kwargs())
    p = Path(caminho)
    assert p.is_file()
    # path absoluto, mas o subdir esperado está no meio
    assert "docs/Time_1_Requisitos/setup-ADK/AgenteAnalista" in str(p)
    assert p.name.startswith("Doubt_Artifact_D-001_")


def test_gerar_doubt_com_base_dir_escreve_no_workspace(tmp_path):
    """Com base_dir setado, escreve direto em <base_dir>/Doubt_Artifact_*.md."""
    base = tmp_path / "ws" / "requirements"
    base.mkdir(parents=True)
    caminho = gerar_doubt_artifact(**_kwargs(base_dir=str(base)))
    p = Path(caminho)
    assert p.is_file()
    assert p.parent == base
    assert p.name.startswith("Doubt_Artifact_D-001_")
    # Conteúdo preserva cabeçalho do template
    content = p.read_text(encoding="utf-8")
    assert "# Doubt_Artifact — Registro de Dúvida do Agente" in content
    assert "### D-001" in content
    assert "HU-001" in content


def test_gerar_doubt_sanitiza_id_duvida(tmp_path):
    """Caracteres não-alfanuméricos em id_duvida são sanitizados no nome do arquivo."""
    base = tmp_path / "ws"
    base.mkdir()
    caminho = gerar_doubt_artifact(**_kwargs(id_duvida="D/001 with spaces", base_dir=str(base)))
    p = Path(caminho)
    assert p.is_file()
    assert " " not in p.name
    assert "/" not in p.name.replace("/", "_")  # já está em diretório, então no name não há
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
cd adk && .venv/bin/pytest tests/unit/test_doubt_generator_base_dir.py -v 2>&1 | tail -20
```

Expected:
- `test_gerar_doubt_sem_base_dir_usa_path_legado` — PASS (legado já funciona)
- `test_gerar_doubt_com_base_dir_escreve_no_workspace` — FAIL com `TypeError: gerar_doubt_artifact() got an unexpected keyword argument 'base_dir'`
- `test_gerar_doubt_sanitiza_id_duvida` — FAIL (mesmo motivo)

- [ ] **Step 3: Implementar a rename**

Substituir o corpo de `gerar_doubt_artifact` em `adk/shared/tools/doubt_generator_analista.py`. Use Edit:

```
old_string:
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
    caminho_base: str = "docs/Time_1_Requisitos/setup-ADK/AgenteAnalista/"
) -> str:
    """
    Gera um arquivo versionado Doubt_Artifact_<ID>_<TS>.md baseado no template oficial do Agente Analista.
    
    Args:
        id_duvida: Identificador sequencial da dúvida (ex: D-001).
        id_artefato_afetado: ID do artefato impactado (ex: HU-001, RF-002).
        trecho_contexto: Citação literal ou referência do documento original.
        duvida_descricao: Descrição clara da incerteza.
        motivo: Por que a dúvida surgiu.
        impacto: O que o agente assumiu como padrão caso não seja resolvida.
        bloqueante: Se a dúvida impede a continuação do fluxo.
        sugestao: Proposta do agente para resolução.
        sessao: Número da sessão/rodada atual.
        contexto_geral: Nome do arquivo ou resumo do contexto lido.
        caminho_base: Diretório onde o arquivo Doubt_Artifact_<ID>_<TS>.md será salvo.
        
    Returns:
        Caminho completo do arquivo gerado.
    """
    diretorio = Path(caminho_base)

new_string:
_DOUBT_LEGADO_BASE = "docs/Time_1_Requisitos/setup-ADK/AgenteAnalista/"


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
    """
    Gera um arquivo versionado Doubt_Artifact_<ID>_<TS>.md baseado no template oficial do Agente Analista.

    Args:
        id_duvida: Identificador sequencial da dúvida (ex: D-001).
        id_artefato_afetado: ID do artefato impactado (ex: HU-001, RF-002).
        trecho_contexto: Citação literal ou referência do documento original.
        duvida_descricao: Descrição clara da incerteza.
        motivo: Por que a dúvida surgiu.
        impacto: O que o agente assumiu como padrão caso não seja resolvida.
        bloqueante: Se a dúvida impede a continuação do fluxo.
        sugestao: Proposta do agente para resolução.
        sessao: Número da sessão/rodada atual.
        contexto_geral: Nome do arquivo ou resumo do contexto lido.
        base_dir: Diretório onde o arquivo Doubt_Artifact_<ID>_<TS>.md será salvo.
            Quando None, fallback para o caminho legado
            ``docs/Time_1_Requisitos/setup-ADK/AgenteAnalista/`` relativo ao CWD.

    Returns:
        Caminho completo do arquivo gerado.
    """
    diretorio = Path(base_dir) if base_dir is not None else Path(_DOUBT_LEGADO_BASE)
```

- [ ] **Step 4: Rodar os testes (devem passar)**

```bash
cd adk && .venv/bin/pytest tests/unit/test_doubt_generator_base_dir.py -v 2>&1 | tail -15
```

Expected: 3 PASS.

- [ ] **Step 5: Confirmar zero regressão no `doubt_inbox` que parsa esses doubts**

```bash
cd adk && .venv/bin/pytest tests/unit/test_doubt_inbox.py -v 2>&1 | tail -15
```

Expected: todos PASS (o conteúdo do markdown não mudou, só o destino).

- [ ] **Step 6: Commit**

```bash
git add adk/shared/tools/doubt_generator_analista.py adk/tests/unit/test_doubt_generator_base_dir.py
git commit -m "update: gerar_doubt_artifact renomeia caminho_base para base_dir"
```

---

## Task 3: Registrar as duas tools em `_FILESYSTEM_TOOL_NAMES`

**Files:**
- Modify: `adk/shared/agent_factory.py:36-41`
- Modify: `adk/tests/unit/test_agent_factory_workspace.py` (append)

- [ ] **Step 1: Escrever o teste**

Anexar ao final de `adk/tests/unit/test_agent_factory_workspace.py`:

```python


def test_filesystem_tool_names_inclui_artefato_requisito_e_doubt():
    """Garante que as duas tools de Time 1 são reconhecidas pelo factory binding."""
    from shared.agent_factory import _FILESYSTEM_TOOL_NAMES
    assert "tool_salvar_artefato_requisito" in _FILESYSTEM_TOOL_NAMES
    assert "gerar_doubt_artifact" in _FILESYSTEM_TOOL_NAMES


def test_bind_tool_salvar_artefato_requisito_injeta_base_dir(tmp_path):
    """_bind_tool_to_workspace deve aplicar partial(base_dir=...) em tool_salvar_artefato_requisito."""
    from google.adk.tools import FunctionTool
    from shared.agent_factory import _bind_tool_to_workspace
    from shared.tools import tool_salvar_artefato_requisito

    base = tmp_path / "agente"
    base.mkdir()
    bound = _bind_tool_to_workspace(
        FunctionTool(tool_salvar_artefato_requisito),
        agent_workspace=str(base),
        workspace_root=str(tmp_path),
    )
    # Chama via func subjacente
    result = bound.func("HU", "HU-007", "# bound\n")
    assert result.startswith("SUCESSO:")
    assert (base / "HUs" / "HU-007.md").is_file()


def test_bind_gerar_doubt_artifact_injeta_base_dir(tmp_path):
    """_bind_tool_to_workspace deve aplicar partial(base_dir=...) em gerar_doubt_artifact."""
    from google.adk.tools import FunctionTool
    from shared.agent_factory import _bind_tool_to_workspace
    from shared.tools import gerar_doubt_artifact

    base = tmp_path / "agente"
    base.mkdir()
    bound = _bind_tool_to_workspace(
        FunctionTool(gerar_doubt_artifact),
        agent_workspace=str(base),
        workspace_root=str(tmp_path),
    )
    caminho = bound.func(
        id_duvida="D-001",
        id_artefato_afetado="HU-001",
        trecho_contexto="x",
        duvida_descricao="x",
        motivo="x",
        impacto="x",
    )
    p = Path(caminho)
    assert p.is_file()
    assert p.parent == base
```

- [ ] **Step 2: Rodar (deve falhar)**

```bash
cd adk && .venv/bin/pytest tests/unit/test_agent_factory_workspace.py -v -k "artefato_requisito or doubt" 2>&1 | tail -20
```

Expected:
- `test_filesystem_tool_names_inclui_artefato_requisito_e_doubt` — FAIL (assertion error).
- `test_bind_*_injeta_base_dir` — FAIL: o `_bind_tool_to_workspace` retorna a tool intacta sem binding, então a chamada `bound.func(...)` escreve no path legado (não em `base`).

- [ ] **Step 3: Adicionar ao set**

Edit em `adk/shared/agent_factory.py`:

```
old_string:
# Tools que aceitam base_dir (filesystem — escopo do agente)
_FILESYSTEM_TOOL_NAMES = {
    "tool_criar_arquivo",
    "tool_ler_arquivo",
    "tool_substituir_trecho",
    "tool_salvar_relatorio",
}

new_string:
# Tools que aceitam base_dir (filesystem — escopo do agente)
_FILESYSTEM_TOOL_NAMES = {
    "tool_criar_arquivo",
    "tool_ler_arquivo",
    "tool_substituir_trecho",
    "tool_salvar_relatorio",
    "tool_salvar_artefato_requisito",
    "gerar_doubt_artifact",
}
```

- [ ] **Step 4: Rodar (deve passar)**

```bash
cd adk && .venv/bin/pytest tests/unit/test_agent_factory_workspace.py -v 2>&1 | tail -20
```

Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add adk/shared/agent_factory.py adk/tests/unit/test_agent_factory_workspace.py
git commit -m "update: factory de agentes registra tool_salvar_artefato_requisito e gerar_doubt_artifact como filesystem-bound"
```

---

## Task 4: Bind manual no `workflow_coding_review/agent.py`

**Files:**
- Modify: `adk/src/agents/workflow_coding_review/agent.py:71-78`

- [ ] **Step 1: Aplicar bind**

Edit em `adk/src/agents/workflow_coding_review/agent.py`:

```
old_string:
    tools=[
        _bind(FunctionTool(tool_ler_arquivo), _REQ_WS),
        FunctionTool(gerar_doubt_artifact),
        FunctionTool(tool_salvar_artefato_requisito),
        FunctionTool(run_slicer),
        FunctionTool(ler_chunk),
    ],
)

new_string:
    tools=[
        _bind(FunctionTool(tool_ler_arquivo), _REQ_WS),
        _bind(FunctionTool(gerar_doubt_artifact), _REQ_WS),
        _bind(FunctionTool(tool_salvar_artefato_requisito), _REQ_WS),
        FunctionTool(run_slicer),
        FunctionTool(ler_chunk),
    ],
)
```

- [ ] **Step 2: Smoke import test**

```bash
cd adk && .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from src.agents.workflow_coding_review.agent import agent
print('OK', agent.name, len(agent.sub_agents))
"
```

Expected: `OK coding_review_pipeline 3` — import sem erro.

- [ ] **Step 3: Schema check (Gemini compatibility)**

```bash
cd adk && .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from src.agents.workflow_coding_review.agent import agent
def walk(a, d=0):
    if hasattr(a, 'tools'):
        for i, t in enumerate(a.tools):
            j = t._get_declaration().model_dump_json(exclude_none=True, by_alias=True)
            tag = 'PROBLEM' if 'any_of' in j or 'additionalProperties' in j else 'ok'
            print('  '*d, f'[{i}]', t._get_declaration().name, tag)
    if hasattr(a, 'sub_agents'):
        for sa in a.sub_agents: walk(sa, d+1)
walk(agent)
"
```

Expected: todas as tools marcadas `ok`. Nenhum `PROBLEM` (que indicaria `Optional[str]` mal serializado para Gemini).

- [ ] **Step 4: Commit**

```bash
git add adk/src/agents/workflow_coding_review/agent.py
git commit -m "fix: bind workspace nas tools de requisitos do workflow_coding_review"
```

---

## Task 5: Bind manual no `requirements/agent.py`

**Files:**
- Modify: `adk/src/agents/requirements/agent.py` (imports + tools dos dois agentes)

- [ ] **Step 1: Adicionar imports e helpers no topo**

Edit em `adk/src/agents/requirements/agent.py`:

```
old_string:
import os
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool

from shared.tools import (
    run_slicer,
    ler_chunk,
    extract_text,
    gerar_doubt_artifact,
    listar_duvidas_pendentes,
    tool_salvar_artefato_requisito,
    run_search,
    check_glossary,
    add_to_glossary,
)
from . import prompt, schemas

_DEFAULT_MODEL = os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash")

new_string:
import os
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool

from shared.agent_factory import _bind_tool_to_workspace
from shared.tools import (
    run_slicer,
    ler_chunk,
    extract_text,
    gerar_doubt_artifact,
    listar_duvidas_pendentes,
    tool_salvar_artefato_requisito,
    run_search,
    check_glossary,
    add_to_glossary,
)
from shared.workspace import get_agent_workspace, get_workspace_root
from . import prompt, schemas

_DEFAULT_MODEL = os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash")

# Workspace binding (resolvido no import-time, igual ao workflow_coding_review).
_WS_ROOT = str(get_workspace_root())
_REQ_WS = str(get_agent_workspace("requirements_agent"))
_GLOS_WS = str(get_agent_workspace("glossario_agent"))


def _bind(tool, agent_ws):
    return _bind_tool_to_workspace(tool, agent_ws, _WS_ROOT)
```

- [ ] **Step 2: Bind nas tools do `glossario_agent`**

Edit (linhas ~95-103 originais):

```
old_string:
    tools=[
        FunctionTool(extract_text),
        FunctionTool(run_slicer),
        FunctionTool(run_search),
        FunctionTool(add_to_glossary),
        FunctionTool(check_glossary),
        FunctionTool(gerar_doubt_artifact),
    ],
)

# ── Agente Principal de Requisitos ───────────────────────────────────────────

new_string:
    tools=[
        FunctionTool(extract_text),
        FunctionTool(run_slicer),
        FunctionTool(run_search),
        FunctionTool(add_to_glossary),
        FunctionTool(check_glossary),
        _bind(FunctionTool(gerar_doubt_artifact), _GLOS_WS),
    ],
)

# ── Agente Principal de Requisitos ───────────────────────────────────────────
```

- [ ] **Step 3: Bind nas tools do `requirements_agent`**

Edit (linhas ~113-120 originais):

```
old_string:
    tools=[
        FunctionTool(run_slicer),
        FunctionTool(ler_chunk),
        FunctionTool(gerar_doubt_artifact),
        FunctionTool(tool_salvar_artefato_requisito),
        AgentTool(agent=glossario_agent),
    ],
)

new_string:
    tools=[
        FunctionTool(run_slicer),
        FunctionTool(ler_chunk),
        _bind(FunctionTool(gerar_doubt_artifact), _REQ_WS),
        _bind(FunctionTool(tool_salvar_artefato_requisito), _REQ_WS),
        AgentTool(agent=glossario_agent),
    ],
)
```

- [ ] **Step 4: Smoke import test**

```bash
cd adk && .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
# Importa coding_review primeiro pra inicializar workspace
from src.agents.workflow_coding_review.agent import agent as cr
from src.agents.requirements.agent import agent as req
print('OK', req.name, len(req.tools))
"
```

Expected: `OK requirements_agent 5` — sem erro.

- [ ] **Step 5: Schema check**

```bash
cd adk && .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from src.agents.workflow_coding_review.agent import agent as cr_init
from src.agents.requirements.agent import agent, glossario_agent
for a in (agent, glossario_agent):
    print('## ', a.name)
    for i, t in enumerate(a.tools):
        if hasattr(t, '_get_declaration'):
            j = t._get_declaration().model_dump_json(exclude_none=True, by_alias=True)
            tag = 'PROBLEM' if 'any_of' in j or 'additionalProperties' in j else 'ok'
            print('  ', f'[{i}]', t._get_declaration().name, tag)
"
```

Expected: tudo `ok`, nenhum `PROBLEM`.

- [ ] **Step 6: Commit**

```bash
git add adk/src/agents/requirements/agent.py
git commit -m "fix: bind workspace nas tools de requisitos do requirements_agent"
```

---

## Task 6: Suite completa + verificação manual

- [ ] **Step 1: Full pytest sweep**

```bash
cd adk && .venv/bin/pytest tests/unit -v 2>&1 | tail -40
```

Expected: todos PASS. Se algo falhar fora do escopo, parar e investigar — não suprimir.

- [ ] **Step 2: Conferência rápida de estrutura**

```bash
cd adk && git status
```

Expected: working tree clean nos arquivos tocados (commits feitos). Apenas alterações pré-existentes do branch fora dos arquivos do plan.

- [ ] **Step 3: Disparar diagnose do skill ai4es-e2e (pré-flight do servidor)**

```bash
cd /home/hhiroshi92/github/AI4ES && bash .claude/skills/ai4es-e2e/scripts/diagnose.sh 2>&1 | tail -30
```

Expected: relatório "tudo verde" — server import-checks dos 3 pipelines passa.

- [ ] **Step 4: Reportar conclusão**

Reportar ao usuário:
- 6 commits criados (1 unblocker + 5 do fix), todos atômicos.
- Suite de testes passa.
- Schema check Gemini-compat passa.
- **Verificação E2E real do workspace ainda depende de subir o servidor e rodar o orchestrator** — usar `bash .claude/skills/ai4es-e2e/scripts/run-agent.sh orchestrator <prompt>` seguido de `inspect-run.sh` (passo manual do usuário; agente não pode subir uvicorn em foreground).

---

## Self-Review

**Spec coverage** (validado contra `2026-05-17-workspace-binding-requisitos-doubts-design.md`):

- §3.1 `tool_salvar_artefato_requisito` com `base_dir` → Task 1
- §3.2 `gerar_doubt_artifact` rename → Task 2
- §3.3 `_FILESYSTEM_TOOL_NAMES` → Task 3
- §3.4 Bind no `workflow_coding_review` → Task 4
- §3.5 Bind no `requirements/agent.py` → Task 5
- §4 Testes (1, 2, 3, 4, 5, 6, 7, 8, 9 do spec) → cobertos em Tasks 1, 2 (test 6 redundante absorvido na proteção de ID_REQ_PATTERN, já coberto em Task 1 step 1)
- §5 Verificação E2E → Task 6 (parcial: agente faz diagnose; run real é manual)
- §6 Compatibilidade → preservada por `base_dir=None` fallback em Tasks 1 e 2

**Placeholder scan:** zero TBD/TODO/"implement appropriate handling". Todo código está inline.

**Type consistency:** parâmetro `base_dir: Optional[str] = None` consistente em ambas tools. `_bind` helper usado consistentemente nas Tasks 4 e 5.

**Out-of-scope mas incluído:** Task 0 (orphan merge marker) — necessário porque sem ele `pytest --collect-only` falha e não conseguimos rodar nenhum teste em `test_filesystem_tools.py`. Justificável e isolado em commit próprio.
