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
