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
