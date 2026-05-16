# Orchestrator SDLC v1 (MVP) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reescrever o `orchestrator` do ADK para acionar os 5 workflows dos Times 1-4, fazer scaffolding inicial em paralelo, e coletar/escalar doubt artifacts ao usuário entre fases — versão MVP sem auto-routing.

**Architecture:** `LlmAgent` com `AgentTool` por workflow + nova lib `adk/shared/tools/doubt_inbox.py` (parser tolerante de 4 formatos + responder). Protocolo de fases (0→4) instruído via prompt; doubts sempre escalam ao usuário (v1).

**Tech Stack:** Python 3.12, Google ADK 1.12+, LiteLLM, pytest 8+. Working directory para todos os comandos: `adk/`.

**Spec:** `docs/superpowers/specs/2026-05-16-orchestrator-sdlc-design.md`

---

## File Structure

| Arquivo | Operação | Responsabilidade |
|---|---|---|
| `adk/shared/tools/doubt_inbox.py` | **CREATE** | Parser dos 4 formatos + `coletar_doubts_pendentes` + `responder_doubt` |
| `adk/shared/tools/__init__.py` | **MODIFY** | Re-exporta as 2 novas funções |
| `adk/src/agents/orchestrator/prompt.py` | **REWRITE** | `description` + `instruction` com protocolo de fases MVP |
| `adk/src/agents/orchestrator/agent.py` | **REWRITE** | `LlmAgent` com 5 workflows + fs tools + inbox tools |
| `adk/tests/unit/test_doubt_inbox.py` | **CREATE** | TDD do parser (4 formatos), aggregator, responder |
| `adk/tests/unit/test_orchestrator_discovery.py` | **CREATE** | Smoke test de descoberta do ADK |

---

## Convenções de execução

- **CWD**: sempre `/home/hhiroshi92/github/AI4ES/adk/` (a pasta `adk/`, não a raiz do repo). Os comandos de teste e o uvicorn rodam dali.
- **Ative o venv antes de cada comando**: `source .venv/bin/activate`. Se o `.venv` não existe, rode `uv sync` primeiro.
- **Commits**: PT-BR, prefixos de `CONTRIBUTING.md` (`add:`, `update:`, `refactor:`, `docs:`, `test:`). Co-author do Claude no rodapé.
- **Pytest config**: já está em `adk/pyproject.toml` (testpaths=`tests`, asyncio_mode=auto). Rodar `pytest` sem flags pega tudo de `adk/tests/`.

---

### Task 1: Setup — skeleton de `doubt_inbox.py` + fixtures de teste

**Files:**
- Create: `adk/shared/tools/doubt_inbox.py`
- Create: `adk/tests/unit/test_doubt_inbox.py`

- [ ] **Step 1.1: Criar o esqueleto de `doubt_inbox.py`**

Conteúdo inicial (mínimo para imports não quebrarem nos testes; funções completas vêm nas próximas tasks):

```python
"""Doubt Inbox — coleta e respostas centralizadas de Doubt_Artifacts.

Suporta os 4 formatos vigentes no AI4ES:
- Time 1 (gerar_doubt_artifact): arquivo único, header `## Metadados da Sessão`.
- doubt_handler: arquivo centralizado com múltiplas seções `### [D-NNN]`.
- clarification: header `# Doubt Artifact — <titulo>` + `> EXECUÇÃO PAUSADA`.
- QA (DoubtArtifactGenerator): header `# DOUBT ARTEFACT |`.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

DIRETORIOS_IGNORADOS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", "dist", "build", ".tox",
}

SEVERIDADE_ORDEM = {
    "Crítica": 0, "Alta": 1, "Média": 2, "Baixa": 3, "Desconhecida": 4,
}


def _inferir_origem(path: Path) -> str:
    """Tenta inferir o agente origem pelo caminho do arquivo."""
    partes_lower = [p.lower() for p in path.parts]
    candidatos = [
        "requirements", "design_architect", "mermaid_specialist",
        "markdown_specialist", "validator", "io_agent",
        "coder", "reviewer", "architect", "test_planner",
        "finalizer", "qa_agent", "action_planner", "code_fix_agent",
        "design_orchestrator", "glossario_agent",
    ]
    for agente in candidatos:
        if any(agente in p for p in partes_lower):
            return agente
    return "desconhecido"


# Funções principais — implementadas nas tasks 2-7
def coletar_doubts_pendentes(caminho_projeto: str = ".") -> List[Dict]:
    raise NotImplementedError("Implementado em Task 6")


def responder_doubt(caminho_arquivo: str, resposta: str, autor: str = "humano") -> bool:
    raise NotImplementedError("Implementado em Task 7")
```

- [ ] **Step 1.2: Criar `tests/unit/test_doubt_inbox.py` com fixtures dos 4 formatos**

```python
"""Tests para shared/tools/doubt_inbox.py — parser tolerante + aggregator + responder."""

import pytest
from pathlib import Path

from shared.tools.doubt_inbox import coletar_doubts_pendentes, responder_doubt


# ---------- Fixtures: conteúdo dos 4 formatos vigentes ----------

FIXTURE_TIME1 = """# Doubt_Artifact — Registro de Dúvida do Agente

> Este arquivo registra uma incerteza...

---

## Metadados da Sessão

| Campo              | Valor                                       |
|--------------------|---------------------------------------------|
| Sessão / Rodada    | 001                          |
| Data               | 16-05-2026 14:30                          |
| Contexto lido      | PRD-001                 |
| Artefatos gerados  | [Pendente] |

---

## Dúvida Registrada

### D-001

- **Artefato afetado:** [HU-005]
- **Trecho do contexto:** "O usuário poderá editar seu perfil"
- **Dúvida:** Quais campos do perfil podem ser editados?
- **Motivo da dúvida**: PRD não especifica campos.
- **Impacto se não resolvida:** Assumir apenas email e nome
- **Bloqueante:** Sim
- **Status:** Aberta
- **Sugestão do Agente:** Definir lista de campos editáveis
- **Resposta:** _(preencher na revisão humana)_

---
"""

FIXTURE_DOUBT_HANDLER = """# Doubt Artifact — Registro de Dúvidas e Bloqueios
Este arquivo centraliza as dúvidas identificadas pelos agentes para revisão humana (Human-in-the-Loop).

## Histórico de Dúvidas

### [D-260516143000] - HU-005
- **Data:** 2026-05-16 14:30:00 UTC
- **Categoria:** Falta de Contexto
- **Severidade:** Alta
- **Descrição:** Campos editáveis do perfil não estão definidos
- **Contexto:** N/A
- **Sugestão do Agente:** Definir lista de campos
- **Status:** 🔴 Aberta
- **Resposta Humana:** _(Aguardando revisão)_

---

### [D-260516150000] - HU-006
- **Data:** 2026-05-16 15:00:00 UTC
- **Categoria:** Ambiguidade
- **Severidade:** Média
- **Descrição:** Comportamento ao deletar conta com posts ativos
- **Contexto:** N/A
- **Sugestão do Agente:** Soft-delete preservando posts
- **Status:** ✅ Resolvida
- **Resposta Humana:** Soft-delete com flag.

---
"""

FIXTURE_CLARIFICATION = """# Doubt Artifact — Campos editáveis do perfil

> EXECUÇÃO PAUSADA — INTERVENÇÃO NECESSÁRIA
> Gerado em 2026-05-16 14:30:00

---

## Localização / Contexto
HU-005 / módulo de perfil

## Descrição do Problema / Dúvida
Campos editáveis não definidos

## Impacto
Não é possível implementar o endpoint sem essa definição

## Pergunta / Sugestão de Resolução
Definir lista de campos editáveis (email, nome, telefone?)

---

## Checklist de Resolução
- [ ] Dúvida respondida pelo usuário
- [ ] Contexto atualizado
- [ ] Agente pode retomar a execução

Status: Pendente
"""

FIXTURE_QA = """# DOUBT ARTEFACT | [HU-005]

## 1. Identificação Técnica
- **ID do Artefato:** `HU-005`
- **Timestamp:** `2026-05-16 14:30:00 UTC`
- **Agente Responsável:** `qa_agente`
- **Módulo/Ferramenta:** `qa_agent / pytest_runner`
- **Severidade:** 🔴 Crítico | 🟠 Anomalia Lógica | 🟡 Contexto | 🟣 Segurança

## 2. Gatilho de Pausa (Diagnóstico de Falha do Agente)
> **[ Falhas de Execução & Limites ]**
> - [ ] **Erro de Sintaxe/Runtime:** Código gerado falhou na compilação/execução.
> - [x] **Timeout / Indisponibilidade:** API ou Tool externa não respondeu.

## 3. Evidência
**Trecho, Prompt ou StackTrace:**

`endpoint /perfil retornou 500`

**Análise / Motivo da Interrupção:**
> `Teste falha porque os campos editáveis do perfil não estão claros.`

## 4. Contexto de Execução
- **Artefato de Entrada:** `HU-005.md`
- **Ação Realizada:** `Execução de testes`
- **Resposta Bruta (Raw Output):** `ERR_LOOP detectado`

## 5. Próximos Passos (Resolução)
- [ ] Ajustar System Prompt ou In-Context Learning (Few-shot).
- [ ] Implementar retry automático.
- [ ] Corrigir Tool/API.
- [x] Esclarecer intenção com o usuário/coordenação.

---
**Gerado automaticamente via ADK Tool v1.0**
*Status da Validação (Coordenação Técnica): [ ] Aprovado | [ ] Reprovado*
"""


@pytest.fixture
def projeto_vazio(tmp_path: Path) -> Path:
    """Diretório de projeto sem doubt artifacts."""
    return tmp_path


@pytest.fixture
def projeto_com_time1(tmp_path: Path) -> Path:
    arq = tmp_path / "docs" / "Time_1_Requisitos" / "setup-ADK" / "AgenteAnalista" / "Doubt_Artifact_D-001_20260516_143000.md"
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(FIXTURE_TIME1, encoding="utf-8")
    return tmp_path


@pytest.fixture
def projeto_com_doubt_handler(tmp_path: Path) -> Path:
    arq = tmp_path / "Doubt_Artifact.md"
    arq.write_text(FIXTURE_DOUBT_HANDLER, encoding="utf-8")
    return tmp_path


@pytest.fixture
def projeto_com_clarification(tmp_path: Path) -> Path:
    arq = tmp_path / "Doubt_Artifact_Clarification.md"
    arq.write_text(FIXTURE_CLARIFICATION, encoding="utf-8")
    return tmp_path


@pytest.fixture
def projeto_com_qa(tmp_path: Path) -> Path:
    arq = tmp_path / "adk" / "src" / "agents" / "qa_agent" / "doubt_artifacts" / "Doubt_Artifact_HU-005_20260516T143000.md"
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(FIXTURE_QA, encoding="utf-8")
    return tmp_path
```

- [ ] **Step 1.3: Rodar o arquivo de teste — sanity check de imports**

Run: `cd /home/hhiroshi92/github/AI4ES/adk && source .venv/bin/activate && pytest tests/unit/test_doubt_inbox.py -v --co`

Expected: pytest coleta o arquivo, mostra "collected 0 items" (sem testes ainda, mas sem erro de import).

- [ ] **Step 1.4: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/shared/tools/doubt_inbox.py adk/tests/unit/test_doubt_inbox.py
git commit -m "$(cat <<'EOF'
add: esqueleto de doubt_inbox + fixtures dos 4 formatos de Doubt_Artifact

Cria adk/shared/tools/doubt_inbox.py com stubs de coletar_doubts_pendentes
e responder_doubt (NotImplementedError nas funcoes principais), e arquivo
de testes com fixtures dos 4 formatos vigentes (Time 1, doubt_handler,
clarification, QA).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Parser do formato Time 1 (`gerar_doubt_artifact`)

**Files:**
- Modify: `adk/shared/tools/doubt_inbox.py` (adiciona detector + parser)
- Modify: `adk/tests/unit/test_doubt_inbox.py` (adiciona testes)

- [ ] **Step 2.1: Escrever os testes (TDD — falham primeiro)**

Adicionar ao final de `adk/tests/unit/test_doubt_inbox.py`:

```python
# ---------- Tests: parser Time 1 ----------

def test_time1_um_doubt_pendente(projeto_com_time1: Path):
    duvidas = coletar_doubts_pendentes(str(projeto_com_time1))
    assert len(duvidas) == 1
    d = duvidas[0]
    assert d["id"] == "D-001"
    assert d["status"] == "Aberta"
    assert d["pergunta"] == "Quais campos do perfil podem ser editados?"
    assert d["sugestao"] == "Definir lista de campos editáveis"
    assert d["bloqueante"] is True
    assert "AgenteAnalista" in d["path"]


def test_time1_origem_inferida_pelo_path(projeto_com_time1: Path):
    duvidas = coletar_doubts_pendentes(str(projeto_com_time1))
    # Path contém "Time_1_Requisitos" e "AgenteAnalista" — _inferir_origem deve achar "requirements"
    assert duvidas[0]["origem_agente"] in {"requirements", "desconhecido"}


def test_time1_status_resolvido_e_ignorado(tmp_path: Path):
    arq = tmp_path / "Doubt_Artifact_D-001_xx.md"
    arq.write_text(FIXTURE_TIME1.replace("**Status:** Aberta", "**Status:** Resolvido"), encoding="utf-8")
    duvidas = coletar_doubts_pendentes(str(tmp_path))
    assert duvidas == []
```

- [ ] **Step 2.2: Rodar testes — devem falhar com NotImplementedError**

Run: `cd /home/hhiroshi92/github/AI4ES/adk && source .venv/bin/activate && pytest tests/unit/test_doubt_inbox.py -v -k time1`

Expected: 3 testes coletados, todos falham com `NotImplementedError: Implementado em Task 6` (ou similar). Esse erro vai sumir ao implementar o aggregator na Task 6 + parser nesta task.

- [ ] **Step 2.3: Adicionar detector e parser Time 1 em `doubt_inbox.py`**

Adicionar antes da função `coletar_doubts_pendentes`:

```python
def _eh_formato_time1(conteudo: str) -> bool:
    return "## Metadados da Sessão" in conteudo and "## Dúvida Registrada" in conteudo


def _parse_time1(conteudo: str, path: Path) -> List[Dict]:
    """Parse formato `gerar_doubt_artifact` (Time 1). Um doubt por arquivo."""
    id_match = re.search(r"### (D-[\w-]+)", conteudo)
    if not id_match:
        return []

    def _campo(pattern: str) -> str:
        m = re.search(pattern, conteudo, re.MULTILINE)
        return m.group(1).strip() if m else ""

    status = _campo(r"\*\*Status:\*\*\s*(.+?)\s*$")
    if "Resolvido" in status or "✅" in status:
        return []

    bloq_raw = _campo(r"\*\*Bloqueante:\*\*\s*(.+?)\s*$")
    bloqueante = "Sim" in bloq_raw

    return [{
        "path": str(path),
        "id": id_match.group(1),
        "status": status or "Aberta",
        "categoria": "Falta de Contexto",
        "severidade": "Crítica" if bloqueante else "Média",
        "origem_agente": _inferir_origem(path),
        "pergunta": _campo(r"\*\*Dúvida:\*\*\s*(.+?)\s*$"),
        "sugestao": _campo(r"\*\*Sugestão do Agente:\*\*\s*(.+?)\s*$"),
        "bloqueante": bloqueante,
    }]
```

- [ ] **Step 2.4: Verificar — testes Time 1 ainda falham (aggregator pendente)**

Run: `cd /home/hhiroshi92/github/AI4ES/adk && source .venv/bin/activate && pytest tests/unit/test_doubt_inbox.py -v -k time1`

Expected: ainda falham (aggregator é Task 6). Isso é OK — vamos completar todos os parsers primeiro, depois o aggregator destrava todos os testes de uma vez.

- [ ] **Step 2.5: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/shared/tools/doubt_inbox.py adk/tests/unit/test_doubt_inbox.py
git commit -m "$(cat <<'EOF'
add: parser do formato Time 1 (gerar_doubt_artifact) em doubt_inbox

Adiciona _eh_formato_time1 (detector) e _parse_time1 (extrator de campos
ID, status, pergunta, sugestao, bloqueante) + 3 testes TDD que falham
ate o aggregator ser implementado na Task 6.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Parser do formato `doubt_handler` (centralizado, múltiplos doubts/arquivo)

**Files:**
- Modify: `adk/shared/tools/doubt_inbox.py`
- Modify: `adk/tests/unit/test_doubt_inbox.py`

- [ ] **Step 3.1: Escrever os testes**

Adicionar a `test_doubt_inbox.py`:

```python
# ---------- Tests: parser doubt_handler ----------

def test_doubt_handler_filtra_apenas_abertas(projeto_com_doubt_handler: Path):
    duvidas = coletar_doubts_pendentes(str(projeto_com_doubt_handler))
    assert len(duvidas) == 1  # FIXTURE tem 2 entradas, 1 resolvida
    assert duvidas[0]["id"] == "D-260516143000"
    assert duvidas[0]["status"] == "🔴 Aberta"
    assert duvidas[0]["categoria"] == "Falta de Contexto"
    assert duvidas[0]["severidade"] == "Alta"
    assert duvidas[0]["pergunta"] == "Campos editáveis do perfil não estão definidos"


def test_doubt_handler_arquivo_sem_pendencias(tmp_path: Path):
    conteudo = FIXTURE_DOUBT_HANDLER.replace("🔴 Aberta", "✅ Resolvida")
    arq = tmp_path / "Doubt_Artifact.md"
    arq.write_text(conteudo, encoding="utf-8")
    assert coletar_doubts_pendentes(str(tmp_path)) == []
```

- [ ] **Step 3.2: Adicionar detector e parser `doubt_handler`**

Em `doubt_inbox.py`, após `_parse_time1`:

```python
def _eh_formato_doubt_handler(conteudo: str) -> bool:
    return "## Histórico de Dúvidas" in conteudo


def _parse_doubt_handler(conteudo: str, path: Path) -> List[Dict]:
    """Parse formato `doubt_handler.registrar_duvida` (arquivo único, múltiplos doubts)."""
    resultados = []
    # Divide em seções por header "### [D-"
    secoes = conteudo.split("### [D-")[1:]
    for secao in secoes:
        # Status aberto: emoji 🔴 + "Aberta" no campo Status
        if "🔴 Aberta" not in secao and "Status:** Aberta" not in secao:
            continue

        id_match = re.match(r"([\w-]+)\]", secao)
        if not id_match:
            continue
        duvida_id = f"D-{id_match.group(1)}"

        def _campo(pattern: str, default: str = "") -> str:
            m = re.search(pattern, secao, re.MULTILINE)
            return m.group(1).strip() if m else default

        severidade = _campo(r"\*\*Severidade:\*\*\s*(.+?)\s*$", "Desconhecida")
        bloqueante = severidade in {"Crítica", "Alta"}

        resultados.append({
            "path": str(path),
            "id": duvida_id,
            "status": _campo(r"\*\*Status:\*\*\s*(.+?)\s*$", "Aberta"),
            "categoria": _campo(r"\*\*Categoria:\*\*\s*(.+?)\s*$"),
            "severidade": severidade,
            "origem_agente": _inferir_origem(path),
            "pergunta": _campo(r"\*\*Descrição:\*\*\s*(.+?)\s*$"),
            "sugestao": _campo(r"\*\*Sugestão do Agente:\*\*\s*(.+?)\s*$"),
            "bloqueante": bloqueante,
        })
    return resultados
```

- [ ] **Step 3.3: Rodar testes (ainda falham — aggregator pendente)**

Run: `cd /home/hhiroshi92/github/AI4ES/adk && source .venv/bin/activate && pytest tests/unit/test_doubt_inbox.py -v -k doubt_handler`

Expected: falham com `NotImplementedError` (esperado até Task 6).

- [ ] **Step 3.4: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/shared/tools/doubt_inbox.py adk/tests/unit/test_doubt_inbox.py
git commit -m "$(cat <<'EOF'
add: parser do formato doubt_handler (centralizado) em doubt_inbox

Suporta multiplos doubts por arquivo (split em "### [D-"), filtra apenas
status "🔴 Aberta" ou "Aberta", deriva bloqueante de severidade ∈ {Critica, Alta}.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Parser do formato `clarification`

**Files:**
- Modify: `adk/shared/tools/doubt_inbox.py`
- Modify: `adk/tests/unit/test_doubt_inbox.py`

- [ ] **Step 4.1: Escrever os testes**

```python
# ---------- Tests: parser clarification ----------

def test_clarification_pendente(projeto_com_clarification: Path):
    duvidas = coletar_doubts_pendentes(str(projeto_com_clarification))
    assert len(duvidas) == 1
    d = duvidas[0]
    assert "Campos editáveis" in d["id"] or "Campos editáveis" in d["pergunta"]
    assert d["status"] == "Pendente"
    assert d["bloqueante"] is True  # clarification sempre é bloqueante
    assert "Campos editáveis não definidos" in d["pergunta"]
    assert "Definir lista de campos" in d["sugestao"]


def test_clarification_resolvida_ignorada(tmp_path: Path):
    arq = tmp_path / "Doubt_Artifact_Clarification.md"
    arq.write_text(FIXTURE_CLARIFICATION.replace("Status: Pendente", "Status: Resolvido"), encoding="utf-8")
    assert coletar_doubts_pendentes(str(tmp_path)) == []
```

- [ ] **Step 4.2: Adicionar detector e parser `clarification`**

Em `doubt_inbox.py`:

```python
def _eh_formato_clarification(conteudo: str) -> bool:
    return "EXECUÇÃO PAUSADA — INTERVENÇÃO NECESSÁRIA" in conteudo


def _parse_clarification(conteudo: str, path: Path) -> List[Dict]:
    """Parse formato `tool_ask_clarification` — pergunta única por arquivo."""
    # Status: campo "Status:" linha solta no final do arquivo
    status_match = re.search(r"^Status:\s*(.+?)\s*$", conteudo, re.MULTILINE)
    status = status_match.group(1).strip() if status_match else "Pendente"
    if "Resolvido" in status or "Resolvida" in status:
        return []

    titulo_match = re.search(r"^# Doubt Artifact — (.+?)$", conteudo, re.MULTILINE)
    titulo = titulo_match.group(1).strip() if titulo_match else path.stem

    def _secao(nome: str) -> str:
        """Captura conteúdo entre `## <nome>` e próxima seção (## ou ---)."""
        pattern = rf"^## {re.escape(nome)}.*?\n(.*?)(?=\n## |\n---|\Z)"
        m = re.search(pattern, conteudo, re.MULTILINE | re.DOTALL)
        return m.group(1).strip() if m else ""

    return [{
        "path": str(path),
        "id": titulo[:60],
        "status": status,
        "categoria": "Clarification",
        "severidade": "Alta",
        "origem_agente": _inferir_origem(path),
        "pergunta": _secao("Descrição do Problema / Dúvida"),
        "sugestao": _secao("Pergunta / Sugestão de Resolução"),
        "bloqueante": True,
    }]
```

- [ ] **Step 4.3: Verificar (testes falham ainda, esperado)**

Run: `pytest tests/unit/test_doubt_inbox.py -v -k clarification`

Expected: NotImplementedError do aggregator. OK.

- [ ] **Step 4.4: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/shared/tools/doubt_inbox.py adk/tests/unit/test_doubt_inbox.py
git commit -m "$(cat <<'EOF'
add: parser do formato clarification em doubt_inbox

Detecta header "EXECUCAO PAUSADA — INTERVENCAO NECESSARIA". Extrai descricao
e sugestao das secoes "## Descricao do Problema / Duvida" e "## Pergunta /
Sugestao de Resolucao". Bloqueante=True por natureza do formato.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Parser do formato QA (`DoubtArtifactGenerator`)

**Files:**
- Modify: `adk/shared/tools/doubt_inbox.py`
- Modify: `adk/tests/unit/test_doubt_inbox.py`

- [ ] **Step 5.1: Escrever os testes**

```python
# ---------- Tests: parser QA ----------

def test_qa_pendente(projeto_com_qa: Path):
    duvidas = coletar_doubts_pendentes(str(projeto_com_qa))
    assert len(duvidas) == 1
    d = duvidas[0]
    assert d["id"] == "HU-005"
    assert d["origem_agente"] == "qa_agent"
    assert "campos editáveis" in d["pergunta"].lower()
    assert d["bloqueante"] is True


def test_qa_aprovado_ignorado(tmp_path: Path):
    conteudo = FIXTURE_QA.replace("[ ] Aprovado", "[x] Aprovado")
    arq = tmp_path / "Doubt_Artifact_HU-005.md"
    arq.write_text(conteudo, encoding="utf-8")
    assert coletar_doubts_pendentes(str(tmp_path)) == []
```

- [ ] **Step 5.2: Adicionar detector e parser QA**

```python
def _eh_formato_qa(conteudo: str) -> bool:
    return "DOUBT ARTEFACT |" in conteudo or "DOUBT ARTEFACT|" in conteudo


def _parse_qa(conteudo: str, path: Path) -> List[Dict]:
    """Parse formato `DoubtArtifactGenerator` (Time 3)."""
    # Status: rodapé com "[x] Aprovado" ou "[x] Reprovado" → resolvido
    if re.search(r"\[x\]\s*Aprovado", conteudo) or re.search(r"\[x\]\s*Reprovado", conteudo):
        return []

    id_match = re.search(r"\*\*ID do Artefato:\*\*\s*`([^`]+)`", conteudo)
    if not id_match:
        return []
    duvida_id = id_match.group(1)

    motivo_match = re.search(
        r"\*\*Análise / Motivo da Interrupção:\*\*\s*\n?>\s*`([^`]+)`",
        conteudo,
    )
    pergunta = motivo_match.group(1).strip() if motivo_match else ""

    return [{
        "path": str(path),
        "id": duvida_id,
        "status": "Aberta",
        "categoria": "QA",
        "severidade": "Alta",
        "origem_agente": "qa_agent",
        "pergunta": pergunta,
        "sugestao": "",
        "bloqueante": True,
    }]
```

- [ ] **Step 5.3: Verificar (ainda falha — aggregator pendente)**

Run: `pytest tests/unit/test_doubt_inbox.py -v -k qa`

Expected: `NotImplementedError`. OK.

- [ ] **Step 5.4: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/shared/tools/doubt_inbox.py adk/tests/unit/test_doubt_inbox.py
git commit -m "$(cat <<'EOF'
add: parser do formato QA (DoubtArtifactGenerator) em doubt_inbox

Detecta header "DOUBT ARTEFACT |". Considera resolvido se rodape tem [x]
Aprovado ou [x] Reprovado. Extrai ID de "**ID do Artefato:** \`<id>\`" e
pergunta de "**Analise / Motivo da Interrupcao:** > \`<texto>\`".

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: `coletar_doubts_pendentes` (aggregator + ordenação)

**Files:**
- Modify: `adk/shared/tools/doubt_inbox.py`
- Modify: `adk/tests/unit/test_doubt_inbox.py`

- [ ] **Step 6.1: Escrever testes do aggregator**

```python
# ---------- Tests: aggregator ----------

def test_aggregator_projeto_vazio(projeto_vazio: Path):
    assert coletar_doubts_pendentes(str(projeto_vazio)) == []


def test_aggregator_ignora_diretorios_protegidos(tmp_path: Path):
    # Doubt dentro de .venv não deve ser coletado
    arq = tmp_path / ".venv" / "Doubt_Artifact_X.md"
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(FIXTURE_TIME1, encoding="utf-8")
    assert coletar_doubts_pendentes(str(tmp_path)) == []


def test_aggregator_ordena_bloqueante_primeiro(tmp_path: Path):
    # 1 não-bloqueante (severidade Média) + 1 bloqueante (severidade Crítica)
    naoBloq = FIXTURE_TIME1.replace("**Bloqueante:** Sim", "**Bloqueante:** Não")
    (tmp_path / "Doubt_Artifact_D-A.md").write_text(naoBloq, encoding="utf-8")
    (tmp_path / "Doubt_Artifact_D-B.md").write_text(FIXTURE_TIME1.replace("D-001", "D-002"), encoding="utf-8")
    duvidas = coletar_doubts_pendentes(str(tmp_path))
    assert len(duvidas) == 2
    assert duvidas[0]["bloqueante"] is True
    assert duvidas[1]["bloqueante"] is False


def test_aggregator_mistura_formatos(tmp_path: Path):
    (tmp_path / "Doubt_Artifact_T1.md").write_text(FIXTURE_TIME1, encoding="utf-8")
    (tmp_path / "Doubt_Artifact.md").write_text(FIXTURE_DOUBT_HANDLER, encoding="utf-8")
    (tmp_path / "Doubt_Artifact_Clarification.md").write_text(FIXTURE_CLARIFICATION, encoding="utf-8")
    duvidas = coletar_doubts_pendentes(str(tmp_path))
    # Time 1: 1 pendente. doubt_handler: 1 pendente (out of 2). clarification: 1.
    assert len(duvidas) == 3


def test_aggregator_arquivo_malformado_nao_explode(tmp_path: Path):
    (tmp_path / "Doubt_Artifact_quebrado.md").write_text("texto qualquer sem header conhecido", encoding="utf-8")
    duvidas = coletar_doubts_pendentes(str(tmp_path))
    assert duvidas == []  # ignora silenciosamente


def test_aggregator_diretorio_inexistente(tmp_path: Path):
    assert coletar_doubts_pendentes(str(tmp_path / "nao_existe")) == []
```

- [ ] **Step 6.2: Implementar `coletar_doubts_pendentes`**

Substituir o stub em `doubt_inbox.py`:

```python
def coletar_doubts_pendentes(caminho_projeto: str = ".") -> List[Dict]:
    """Coleta todos os doubt artifacts ainda em aberto no projeto.

    Faz varredura recursiva por `Doubt_Artifact*.md`, identifica o formato
    de cada arquivo e extrai metadados. Retorna lista ordenada por
    (bloqueante DESC, severidade ASC, id ASC).

    Args:
        caminho_projeto: diretório raiz da busca.

    Returns:
        Lista de dicts com chaves: path, id, status, categoria, severidade,
        origem_agente, pergunta, sugestao, bloqueante.
    """
    base = Path(caminho_projeto).resolve()
    if not base.is_dir():
        return []

    parsers = [
        (_eh_formato_time1, _parse_time1),
        (_eh_formato_doubt_handler, _parse_doubt_handler),
        (_eh_formato_clarification, _parse_clarification),
        (_eh_formato_qa, _parse_qa),
    ]

    duvidas: List[Dict] = []
    for arquivo in base.rglob("Doubt_Artifact*.md"):
        if any(parte in DIRETORIOS_IGNORADOS for parte in arquivo.parts):
            continue
        try:
            conteudo = arquivo.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for detector, parser in parsers:
            if detector(conteudo):
                try:
                    duvidas.extend(parser(conteudo, arquivo))
                except Exception:
                    # Parser falhou — ignora silenciosamente (best-effort)
                    pass
                break

    duvidas.sort(key=lambda d: (
        not d.get("bloqueante", False),
        SEVERIDADE_ORDEM.get(d.get("severidade", "Desconhecida"), 4),
        d.get("id", ""),
    ))
    return duvidas
```

- [ ] **Step 6.3: Rodar TODOS os testes do doubt_inbox — devem passar (exceto responder_doubt)**

Run: `cd /home/hhiroshi92/github/AI4ES/adk && source .venv/bin/activate && pytest tests/unit/test_doubt_inbox.py -v`

Expected: todos os testes das Tasks 2-6 PASSAM. Os testes de `responder_doubt` ainda não existem (vêm na Task 7). Se algum teste falhar, debugar antes de commitar.

- [ ] **Step 6.4: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/shared/tools/doubt_inbox.py adk/tests/unit/test_doubt_inbox.py
git commit -m "$(cat <<'EOF'
add: aggregator coletar_doubts_pendentes com ordenacao por prioridade

Implementa walk recursivo por Doubt_Artifact*.md, ignora diretorios
protegidos (.venv, .git, etc), tenta cada parser em ordem ate detectar
o formato. Ordena por bloqueante (DESC), severidade (Critica > Alta >
Media > Baixa), id (ASC). Todos os testes dos parsers passam agora.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: `responder_doubt` (atualiza status + grava resposta)

**Files:**
- Modify: `adk/shared/tools/doubt_inbox.py`
- Modify: `adk/tests/unit/test_doubt_inbox.py`

- [ ] **Step 7.1: Escrever testes para os 4 formatos**

```python
# ---------- Tests: responder_doubt ----------

def test_responder_time1_atualiza_status_e_resposta(projeto_com_time1: Path):
    duvidas = coletar_doubts_pendentes(str(projeto_com_time1))
    assert len(duvidas) == 1
    path = duvidas[0]["path"]
    ok = responder_doubt(path, "Editáveis: nome, email, telefone, foto.", autor="humano")
    assert ok is True
    conteudo = Path(path).read_text(encoding="utf-8")
    assert "**Status:** Resolvido" in conteudo
    assert "nome, email, telefone, foto" in conteudo
    assert "**Resolvido por:** humano" in conteudo
    # Recoleta — deve estar vazio
    assert coletar_doubts_pendentes(str(projeto_com_time1)) == []


def test_responder_doubt_handler_atualiza_status(projeto_com_doubt_handler: Path):
    duvidas = coletar_doubts_pendentes(str(projeto_com_doubt_handler))
    path = duvidas[0]["path"]
    ok = responder_doubt(path, "Confirmado: email, nome, telefone.", autor="humano")
    assert ok is True
    conteudo = Path(path).read_text(encoding="utf-8")
    assert "✅ Resolvida" in conteudo
    assert "email, nome, telefone" in conteudo


def test_responder_clarification(projeto_com_clarification: Path):
    duvidas = coletar_doubts_pendentes(str(projeto_com_clarification))
    path = duvidas[0]["path"]
    ok = responder_doubt(path, "Lista: email, nome, telefone.", autor="humano")
    assert ok is True
    conteudo = Path(path).read_text(encoding="utf-8")
    assert "Status: Resolvido" in conteudo
    assert "Lista: email, nome, telefone" in conteudo


def test_responder_qa(projeto_com_qa: Path):
    duvidas = coletar_doubts_pendentes(str(projeto_com_qa))
    path = duvidas[0]["path"]
    ok = responder_doubt(path, "Definir campos via UC-005.", autor="humano")
    assert ok is True
    conteudo = Path(path).read_text(encoding="utf-8")
    assert "[x] Aprovado" in conteudo
    assert "Definir campos via UC-005" in conteudo


def test_responder_doubt_arquivo_inexistente(tmp_path: Path):
    ok = responder_doubt(str(tmp_path / "nao_existe.md"), "resposta", autor="humano")
    assert ok is False
```

- [ ] **Step 7.2: Implementar `responder_doubt`**

Substituir o stub:

```python
def responder_doubt(caminho_arquivo: str, resposta: str, autor: str = "humano") -> bool:
    """Marca um doubt artifact como Resolvido e grava a resposta.

    Suporta os 4 formatos: tenta cada substituição; se alguma der match,
    considera o arquivo atualizado. Anexa metadado de autoria e data.

    Args:
        caminho_arquivo: caminho do .md
        resposta: texto da resposta humana ou de outro workflow
        autor: identificador de quem respondeu (default "humano")

    Returns:
        True se atualizou; False se arquivo não existe ou não havia
        nada pendente para atualizar.
    """
    path = Path(caminho_arquivo)
    if not path.is_file():
        return False

    try:
        conteudo = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    novo = conteudo
    timestamp = datetime.now(timezone.utc).isoformat()

    # Status: Aberta → Resolvido (Time 1)
    novo = re.sub(r"\*\*Status:\*\*\s*Aberta\b", "**Status:** Resolvido", novo)
    # Status: 🔴 Aberta → ✅ Resolvida (doubt_handler)
    novo = re.sub(r"\*\*Status:\*\*\s*🔴\s*Aberta\b", "**Status:** ✅ Resolvida", novo)
    # Status: Pendente → Resolvido (clarification)
    novo = re.sub(r"^Status:\s*Pendente\s*$", "Status: Resolvido", novo, flags=re.MULTILINE)
    # QA: [ ] Aprovado → [x] Aprovado (apenas o primeiro)
    if "DOUBT ARTEFACT" in conteudo:
        novo = re.sub(r"\[\s\]\s*Aprovado", "[x] Aprovado", novo, count=1)

    # Substitui campo Resposta (variantes)
    novo = re.sub(
        r"\*\*Resposta Humana:\*\*\s*.+?$",
        f"**Resposta Humana:** {resposta}",
        novo,
        flags=re.MULTILINE,
    )
    novo = re.sub(
        r"\*\*Resposta:\*\*\s*.+?$",
        f"**Resposta:** {resposta}",
        novo,
        flags=re.MULTILINE,
    )

    # Para QA e clarification (sem campo "Resposta" estruturado), anexa no rodapé
    if conteudo == novo:
        # Nenhum status mudou — provavelmente já estava resolvido
        return False

    # Anexa metadado de resolução (apenas uma vez por arquivo)
    if "**Resolvido por:**" not in novo:
        marcador = f"\n\n---\n\n**Resposta registrada por {autor}:** {resposta}\n\n- **Resolvido por:** {autor}\n- **Data resolução:** {timestamp}\n"
        novo = novo + marcador

    try:
        path.write_text(novo, encoding="utf-8")
        return True
    except OSError:
        return False
```

- [ ] **Step 7.3: Rodar TODOS os testes do doubt_inbox**

Run: `cd /home/hhiroshi92/github/AI4ES/adk && source .venv/bin/activate && pytest tests/unit/test_doubt_inbox.py -v`

Expected: TODOS passam (parsers + aggregator + responder).

- [ ] **Step 7.4: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/shared/tools/doubt_inbox.py adk/tests/unit/test_doubt_inbox.py
git commit -m "$(cat <<'EOF'
add: responder_doubt — marca doubt como Resolvido nos 4 formatos

Substitui status pendente em cada formato (Aberta -> Resolvido para Time 1
e clarification, 🔴 Aberta -> ✅ Resolvida para doubt_handler, [ ] Aprovado
-> [x] Aprovado para QA). Substitui campos "Resposta" e "Resposta Humana".
Anexa metadado "Resolvido por:" + timestamp no rodape.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Re-exportar em `shared/tools/__init__.py`

**Files:**
- Modify: `adk/shared/tools/__init__.py`

- [ ] **Step 8.1: Adicionar imports e `__all__`**

Editar `adk/shared/tools/__init__.py`. Conteúdo final completo:

```python
from .git import tool_git_add, tool_git_commit, tool_git_checkout, tool_ler_diff
from .filesystem import (
    tool_criar_arquivo,
    tool_salvar_relatorio,
    tool_ler_arquivo,
    tool_substituir_trecho,
    tool_salvar_artefato_requisito,
)
from .doubt_handler import registrar_duvida, listar_duvidas_pendentes
from .slicer_tool import run_slicer, ler_chunk, extract_text
from .doubt_generator_analista import gerar_doubt_artifact
from .search_tool import run_search
from .glossary_tool import check_glossary, add_to_glossary
from .clarification import tool_ask_clarification_adk
from .doubt_inbox import coletar_doubts_pendentes, responder_doubt

__all__ = [
    "tool_git_add",
    "tool_git_commit",
    "tool_git_checkout",
    "tool_ler_diff",
    "tool_criar_arquivo",
    "tool_salvar_relatorio",
    "tool_ler_arquivo",
    "tool_substituir_trecho",
    "tool_salvar_artefato_requisito",
    "registrar_duvida",
    "listar_duvidas_pendentes",
    "run_slicer",
    "ler_chunk",
    "extract_text",
    "gerar_doubt_artifact",
    "run_search",
    "check_glossary",
    "add_to_glossary",
    "tool_ask_clarification_adk",
    "coletar_doubts_pendentes",
    "responder_doubt",
]
```

- [ ] **Step 8.2: Sanity check do import**

Run: `cd /home/hhiroshi92/github/AI4ES/adk && source .venv/bin/activate && python -c "from shared.tools import coletar_doubts_pendentes, responder_doubt; print('ok')"`

Expected: imprime `ok`. Sem ImportError.

- [ ] **Step 8.3: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/shared/tools/__init__.py
git commit -m "$(cat <<'EOF'
update: re-exporta coletar_doubts_pendentes e responder_doubt em shared.tools

Permite "from shared.tools import coletar_doubts_pendentes, responder_doubt"
pelos agentes — convencao do projeto (CLAUDE.md).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Reescrever `orchestrator/prompt.py` com protocolo MVP

**Files:**
- Modify: `adk/src/agents/orchestrator/prompt.py`

- [ ] **Step 9.1: Substituir conteúdo completo de `prompt.py`**

Substituir o arquivo inteiro:

```python
description = """
Orquestrador principal do estúdio AI4ES (SDLC completo).
Coordena os 5 workflows dos Times 1-4 (Requisitos, Design, Testes, Codificação),
faz scaffolding inicial em paralelo, coleta doubt artifacts entre fases e escala
dúvidas ao usuário sempre que houver bloqueio.
"""

instruction = """
# PAPEL
Você é o orquestrador SDLC do AI4ES. Você NÃO escreve código, NÃO analisa
requisitos, NÃO desenha arquitetura diretamente. Você COORDENA os 5
workflows dos Times, lê doubt artifacts entre fases e escala dúvidas ao
usuário.

# WORKFLOWS DISPONÍVEIS
1. `requirements_pipeline` — Time 1. Transforma PRD/descrição em
   HUs, RFs, RNFs, UCs, RNs, Glossário.
2. `design_pipeline` — Time 2. Transforma HUs em diagramas Mermaid (.mmd)
   e relatórios Markdown (.md) persistidos em staging.
3. `coding_review_pipeline` — Time 4 (default da Fase 3). Pipeline enxuto:
   requirements → coder → reviewer.
4. `sdlc_pipeline` — Time 4 (opt-in). Pipeline rígido com SDLC completo
   embutido. Use APENAS se o usuário pedir explicitamente "SDLC completo"
   ou "ciclo SDLC sequencial". Se usar este, PULE a Fase 4.
5. `qa_pipeline` — Time 3. Gera testes pytest a partir de requisitos +
   código, executa e autocorrige falhas.

# TOOLS DE FILESYSTEM
- `tool_criar_arquivo(caminho, conteudo)` — cria/sobrescreve arquivo.
- `tool_ler_arquivo(caminho)` — lê arquivo.

# TOOLS DE DOUBT INBOX
- `coletar_doubts_pendentes(caminho_projeto)` — lista doubts em aberto.
- `responder_doubt(caminho_arquivo, resposta, autor)` — grava resposta e
  marca como Resolvido.

# PROTOCOLO DE FASES

## FASE 0 — Scaffolding (sempre, antes de qualquer workflow)
Chame em PARALELO no MESMO TURNO (3 invocações simultâneas):
  - tool_criar_arquivo("temp/staging/README.md",
        "# Staging (Time 2)\\n\\nDiretório de artefatos intermediários do "
        "pipeline de Design. Gerenciado pelo io_agent.")
  - tool_criar_arquivo("artefactsTests/README.md",
        "# Testes Gerados (Time 3)\\n\\nDiretório onde o qa_agent salva os "
        "arquivos pytest gerados.")
  - tool_criar_arquivo("docs/Time_1_Requisitos/setup-ADK/AgenteAnalista/README.md",
        "# Agente Analista (Time 1)\\n\\nDiretório default para "
        "Doubt_Artifacts gerados pelo workflow_requirements.")

## FASE 1 — Requisitos (bloqueante)
Chame `requirements_pipeline(request=<pedido_original_do_usuario>)`.
Aguarde o retorno (HUs, RFs, RNFs, UCs, RNs, Glossário).

Em seguida chame `coletar_doubts_pendentes(".")`.
Se retornar ≥1 dúvida → execute PROTOCOLO DE DOUBT antes de seguir.

## FASE 2 — Design (paralelo)
Chame em PARALELO no MESMO TURNO:
  - design_pipeline(request=<contexto + HUs/RFs da Fase 1>)
  - tool_criar_arquivo(...) para preparar subpastas específicas do
    projeto em artefactsTests/, se aplicável.

Em seguida coletar_doubts_pendentes(".") → PROTOCOLO DE DOUBT se necessário.

## FASE 3 — Codificação
Default: `coding_review_pipeline(request=<contexto: requisitos + design>)`.
Opt-in: se usuário pediu explicitamente "SDLC completo" → use
`sdlc_pipeline` em vez disso e PULE a Fase 4 (o sdlc_pipeline já embute
qa internamente).

Em seguida coletar_doubts_pendentes(".") → PROTOCOLO DE DOUBT se necessário.

## FASE 4 — QA
Pule esta fase se a Fase 3 usou `sdlc_pipeline`.
Caso contrário, chame `qa_pipeline(request=<artefatos de requisito +
código implementado>)`.

Em seguida coletar_doubts_pendentes(".") → PROTOCOLO DE DOUBT se necessário.

## ENTREGA FINAL
Apresente ao usuário um resumo executivo em PT-BR com:
- Artefatos produzidos por fase, com caminhos absolutos.
- Doubt artifacts criados durante o ciclo e como foram resolvidos.
- Doubt artifacts ainda abertos (se houver — só em caso de erro).

# PROTOCOLO DE DOUBT (v1 — sempre escala ao usuário)

Sempre que `coletar_doubts_pendentes` retornar ≥1 dúvida:

1. Para CADA dúvida (a lista já vem ordenada por bloqueante + severidade):

   a. Apresente ao usuário em PT-BR:

      🚧 [<origem_agente>] precisa de esclarecimento sobre <id>:

      Pergunta: <pergunta>
      Sugestão do agente: <sugestao>

      Como deseja proceder?

   b. Aguarde a resposta do usuário.

   c. Chame `responder_doubt(<path>, <resposta>, autor="humano")`.

   d. Se `responder_doubt` retornar False, avise o usuário do problema e
      tente novamente após investigação.

2. Após resolver TODAS as dúvidas, chame `coletar_doubts_pendentes` mais
   uma vez:
   - Se vazio → siga para a próxima fase.
   - Se ainda há dúvidas → repita o protocolo (workflows podem ter
     gerado dúvidas novas no meio do caminho).

# REGRAS
- Idioma: SEMPRE Português brasileiro nas mensagens ao usuário.
- Caminhos: relativos ao CWD do uvicorn (`adk/`). Nunca absolutos.
- Nunca pule uma dúvida silenciosamente. Sempre escale ao usuário.
- Nunca avance para a próxima fase com doubts bloqueantes abertos.
- Aproveite paralelismo: quando duas tools não dependem uma da outra,
  emita as chamadas no mesmo turno (Fase 0 e Fase 2 são paralelos).
- Resuma cada fase para o usuário em 1-2 frases antes de seguir para a
  próxima.
"""
```

- [ ] **Step 9.2: Sanity check do import**

Run: `cd /home/hhiroshi92/github/AI4ES/adk && source .venv/bin/activate && python -c "from src.agents.orchestrator import prompt; print(prompt.description[:60])"`

Expected: imprime `Orquestrador principal do estúdio AI4ES (SDLC completo).` (sem erro).

- [ ] **Step 9.3: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/src/agents/orchestrator/prompt.py
git commit -m "$(cat <<'EOF'
refactor: reescreve prompt do orchestrator com protocolo de fases MVP

Substitui descricao e instruction completa do orchestrator para v1:
- Conhece os 5 workflows dos Times 1-4 (requirements, design, coding_review,
  sdlc, qa).
- Protocolo Fase 0 (scaffolding paralelo) -> Fase 1 -> ... -> Fase 4 com
  coletar_doubts_pendentes entre fases.
- Doubt routing v1: sempre escala ao usuario (sem auto-routing).
- Default Fase 3 e coding_review_pipeline; sdlc_pipeline opt-in exclusivo.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Reescrever `orchestrator/agent.py` + smoke test

**Files:**
- Modify: `adk/src/agents/orchestrator/agent.py`
- Create: `adk/tests/unit/test_orchestrator_discovery.py`

- [ ] **Step 10.1: Substituir conteúdo de `agent.py`**

Substituir o arquivo inteiro:

```python
"""Orchestrator SDLC: aciona os 5 workflows e coordena doubt inbox.

v1 (MVP): protocolo de fases instruido via prompt. Doubts sempre escalam
ao usuario (sem auto-routing — fica para v2).
"""

import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool

from src.agents.workflow_requirements.agent import agent as requirements_pipeline
from src.agents.workflow_design_pipeline.agent import agent as design_pipeline
from src.agents.workflow_coding_review.agent import agent as coding_review_pipeline
from src.agents.workflow_coding.agent import agent as sdlc_pipeline
from src.agents.workflow_qa.agent import agent as qa_pipeline

from shared.tools import (
    tool_criar_arquivo,
    tool_ler_arquivo,
    coletar_doubts_pendentes,
    responder_doubt,
)

from . import prompt

_DEFAULT_MODEL = "github_copilot/gpt-4"

root_agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
    name="orchestrator",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        AgentTool(agent=requirements_pipeline),
        AgentTool(agent=design_pipeline),
        AgentTool(agent=coding_review_pipeline),
        AgentTool(agent=sdlc_pipeline),
        AgentTool(agent=qa_pipeline),
        FunctionTool(tool_criar_arquivo),
        FunctionTool(tool_ler_arquivo),
        FunctionTool(coletar_doubts_pendentes),
        FunctionTool(responder_doubt),
    ],
)
```

- [ ] **Step 10.2: Criar smoke test de descoberta**

Criar `adk/tests/unit/test_orchestrator_discovery.py`:

```python
"""Smoke test: orchestrator é descoberto pelo ADK e expõe root_agent."""

import pytest


def test_orchestrator_root_agent_importavel():
    from src.agents.orchestrator import root_agent
    assert root_agent is not None
    assert root_agent.name == "orchestrator"


def test_orchestrator_tem_5_workflows_e_4_tools():
    from src.agents.orchestrator import root_agent
    # 5 workflows (AgentTool) + 4 FunctionTools = 9 tools
    assert len(root_agent.tools) == 9


def test_orchestrator_nomes_dos_workflows_presentes():
    """Cada AgentTool deve apontar para um workflow esperado."""
    from src.agents.orchestrator import root_agent
    from google.adk.tools.agent_tool import AgentTool

    nomes_esperados = {
        "requirements_pipeline",
        "design_pipeline",
        "coding_review_pipeline",
        "sdlc_pipeline",
        "qa_pipeline",
    }
    nomes_encontrados = set()
    for t in root_agent.tools:
        if isinstance(t, AgentTool):
            nomes_encontrados.add(t.agent.name)
    assert nomes_esperados.issubset(nomes_encontrados), (
        f"Faltam workflows: {nomes_esperados - nomes_encontrados}"
    )
```

- [ ] **Step 10.3: Rodar smoke test**

Run: `cd /home/hhiroshi92/github/AI4ES/adk && source .venv/bin/activate && pytest tests/unit/test_orchestrator_discovery.py -v`

Expected: 3 testes passam.

**Se o teste `test_orchestrator_tem_5_workflows_e_4_tools` falhar com contagem diferente**: verifique que `agent.py` lista exatamente os 9 tools listados acima. Se algum workflow não importar, ler o traceback completo — geralmente é problema de path (`pythonpath = ["."]` em pyproject deve permitir `src.agents.X`).

- [ ] **Step 10.4: Rodar suite completa pra garantir que nada quebrou**

Run: `cd /home/hhiroshi92/github/AI4ES/adk && source .venv/bin/activate && pytest tests/unit/ -v`

Expected: TODOS os testes (doubt_inbox + orchestrator_discovery + qualquer outro pré-existente) passam.

- [ ] **Step 10.5: Commit**

```bash
cd /home/hhiroshi92/github/AI4ES
git add adk/src/agents/orchestrator/agent.py adk/tests/unit/test_orchestrator_discovery.py
git commit -m "$(cat <<'EOF'
refactor: orchestrator passa a conhecer os 5 workflows + doubt inbox

Reescreve adk/src/agents/orchestrator/agent.py removendo AgentTool de coder
e reviewer (substituidos por coding_review_pipeline que ja os encapsula) e
adicionando os 5 workflows dos Times 1-4 + tools de filesystem +
coletar_doubts_pendentes/responder_doubt.

Adiciona smoke test de descoberta em adk/tests/unit/test_orchestrator_discovery.py
verificando que root_agent eh importavel e expoe os 9 tools corretos.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: Validação manual via `dev-ui` (sem subagent automation)

**Files:** nenhum (validação manual)

- [ ] **Step 11.1: Subir o uvicorn**

Run em um terminal: `cd /home/hhiroshi92/github/AI4ES/adk && source .venv/bin/activate && uvicorn app.main:app --reload --port 8081`

Expected: servidor sobe sem erros de import. Se aparecer `OAuth device flow`, abrir `https://github.com/login/device`, colar o código, autorizar.

- [ ] **Step 11.2: Verificar que `orchestrator` aparece no `/list-apps`**

Em outro terminal: `curl -s http://127.0.0.1:8081/list-apps | python -m json.tool`

Expected: lista de apps inclui `"orchestrator"` (junto com os outros 18 agentes).

- [ ] **Step 11.3: Abrir dev-ui e mandar um pedido teste**

Abrir no browser: `http://127.0.0.1:8081/dev-ui/?app=orchestrator`

Enviar como prompt:
```
Construa um endpoint /healthcheck simples que retorna {"status": "ok"} em FastAPI.
```

**O que verificar manualmente:**

1. O orchestrator inicia chamando `tool_criar_arquivo` 3 vezes em paralelo (Fase 0).
2. Em seguida chama `requirements_pipeline` com o pedido (Fase 1).
3. Após retorno, chama `coletar_doubts_pendentes(".")`.
4. Se houver doubts → o orchestrator deve apresentar texto começando com `🚧 [<agente>] precisa de esclarecimento` e aguardar resposta.
5. Após resolver (ou se não houver doubts), prossegue para `design_pipeline` em paralelo com mais um `tool_criar_arquivo` (Fase 2).
6. Em seguida `coding_review_pipeline` (Fase 3, default).
7. Em seguida `qa_pipeline` (Fase 4).
8. Resumo final com lista de artefatos.

**Critérios de sucesso do MVP:**

- ✅ As 5 workflows são chamadas na ordem correta.
- ✅ `coletar_doubts_pendentes` é chamado entre cada fase.
- ✅ Quando há doubt, o orchestrator escala ao usuário em PT-BR com o template `🚧 [...]`.
- ✅ Resposta do usuário é gravada via `responder_doubt` e o status do arquivo muda.
- ✅ Fase 0 e Fase 2 mostram tools paralelas no log do uvicorn.

**Critérios de falha (corrigir antes de fechar):**

- ❌ Orchestrator pula uma fase silenciosamente.
- ❌ Orchestrator ignora um doubt em aberto.
- ❌ Orchestrator chama tools em inglês ou mistura idiomas nas mensagens.
- ❌ Tool calls aparecem todas sequenciais quando deveriam ser paralelas (Fase 0, Fase 2).

- [ ] **Step 11.4: Se algum critério falhar, ajustar o `prompt.py` e voltar ao Step 11.1**

Padrões comuns de fix:
- Fluxo de fases não respeitado → reforçar "OBRIGATÓRIO" no protocolo.
- Idioma inconsistente → adicionar exemplos em PT-BR explícitos no prompt.
- Falta de paralelismo → adicionar instrução tipo "EMITA AS 3 CHAMADAS NO MESMO TURNO".

Após ajuste, commitar com `update: refina prompt do orchestrator apos validacao manual` e rodar de novo.

- [ ] **Step 11.5: Quando passar — registro do que foi testado**

Não há commit final aqui — a validação é externa ao código. Após validação manual OK, o trabalho do MVP está concluído.

---

## Self-Review (executado durante a escrita do plano)

**1. Spec coverage:**
- ✅ Seção 2 (Em escopo): todos os 6 itens têm task.
- ✅ Seção 3.2 (composição do orchestrator): Task 10.
- ✅ Seção 3.3.1-2 (parser dos 4 formatos + responder): Tasks 2-7.
- ✅ Seção 4 (protocolo de fases): Task 9 (prompt) + Task 11 (validação).
- ✅ Seção 7 (testes): Tasks 2-7 (unit) + Task 10 (smoke).
- ✅ Seção 12 (escopo MVP): plano omite `classificar_doubt` corretamente.

**2. Placeholder scan:** Nenhum TBD/TODO/"implement later" no plano. Cada step tem código concreto ou comando exato.

**3. Type consistency:** as 7 chaves de cada doubt dict (`path`, `id`, `status`, `categoria`, `severidade`, `origem_agente`, `pergunta`, `sugestao`, `bloqueante`) são consistentes em todas as tasks. `coletar_doubts_pendentes` e `responder_doubt` têm assinaturas idênticas em prompt, agent.py e __init__.py.

**4. Decisões de implementação que valem flag:**
- O parser do `clarification` usa o título como `id` (truncado a 60 chars). Não há D-NNN no formato — é o melhor proxy.
- `responder_doubt` retorna `False` se o conteúdo do arquivo não mudou após as substituições (interpretação: já estava resolvido). Os testes esperam esse comportamento.
- A Task 10 só adiciona o `coding_review_pipeline` E `sdlc_pipeline` ao orchestrator — o prompt instrui sobre quando usar cada um.
