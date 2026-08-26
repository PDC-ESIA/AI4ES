"""Tests para o Agente de Validação de Implementação.

A validação é dirigida por LLM em produção; aqui testamos a codificação
determinística da política de veredito (`montar_veredito` / `agregar_status`)
sobre um ExecutionReport mock — sem rodar o LLM real. Cobre:
- Camada 1: overall_status=erro/falha → reprovado, blocking_reason, inconclusivo;
- Camada 2: todos os critérios atendido → aprovado;
- um critério nao_atendido → reprovado global (conservador);
- um critério inconclusivo → reprovado global (conservador).
"""

import pytest

from src.agents.implementation_validator.agent import (
    agent,
    agregar_status,
    montar_veredito,
    root_agent,
)
from src.agents.implementation_validator.schemas import (
    CriterionStatus,
    CriterionVerdict,
    ValidationVerdict,
    VerdictStatus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _report(overall, criteria=("A rota / responde 200", "O domínio está correto")):
    """Monta um ExecutionReport mock (apenas evidência, sem veredito)."""
    return {
        "work_item_id": "TASK-001",
        "overall_status": overall,
        "stages": [
            {"stage": "implantacao_artefato", "status": "falha",
             "error_code": "CONTAINER_NAO_INICIOU"},
        ] if overall in ("falha", "erro") else [],
        "acceptance_criteria": list(criteria),
        "criteria_evidence": [
            {
                "criterion": c,
                "check_performed": "GET /",
                "observed": "HTTP 200",
                "checkable": True,
            }
            for c in criteria
        ],
    }


def _cv(status, criterion="c"):
    return CriterionVerdict(criterion=criterion, status=status, reasoning="justificativa")


# ===========================================================================
# Wiring do agente
# ===========================================================================

def test_agent_wiring():
    assert root_agent.name == "implementation_validator"
    # GAP-00: sem output_schema (schema + tools são mutuamente exclusivos no ADK).
    # O LLM emite markdown em output_key="validation_raw"; um after_agent_callback
    # determinístico parseia a resposta e aplica a política.
    assert agent.output_schema is None
    assert agent.output_key == "validation_raw"
    assert agent.after_agent_callback is not None


# ===========================================================================
# Camada 1 — execução falha/erro reprova imediatamente
# ===========================================================================

@pytest.mark.parametrize("overall", ["erro", "falha"])
def test_camada1_execucao_falha_reprova_com_inconclusivos(overall):
    v = montar_veredito(_report(overall))

    assert v.status == VerdictStatus.REPROVADO
    assert v.blocking_reason  # preenchido
    assert overall in v.blocking_reason
    assert "implantacao_artefato" in v.blocking_reason 
    assert "CONTAINER_NAO_INICIOU" in v.blocking_reason
    # Todos os critérios ficam inconclusivo (nenhum pôde ser comprovado)
    assert len(v.criteria_verdicts) == 2
    assert all(cv.status == CriterionStatus.INCONCLUSIVO for cv in v.criteria_verdicts)


def test_camada1_nao_avanca_para_camada2():
    # Mesmo recebendo vereditos positivos, a Camada 1 tem precedência absoluta.
    v = montar_veredito(
        _report("erro"),
        criteria_verdicts=[_cv(CriterionStatus.ATENDIDO), _cv(CriterionStatus.ATENDIDO)],
    )
    assert v.status == VerdictStatus.REPROVADO
    assert all(cv.status == CriterionStatus.INCONCLUSIVO for cv in v.criteria_verdicts)


# ===========================================================================
# Camada 2 — agregação conservadora
# ===========================================================================

def test_camada2_todos_atendido_aprova():
    cv = [_cv(CriterionStatus.ATENDIDO), _cv(CriterionStatus.ATENDIDO)]
    v = montar_veredito(_report("sucesso"), criteria_verdicts=cv)

    assert v.status == VerdictStatus.APROVADO
    assert v.blocking_reason is None
    assert v.criteria_verdicts == cv


def test_camada2_um_nao_atendido_reprova_global():
    cv = [_cv(CriterionStatus.ATENDIDO), _cv(CriterionStatus.NAO_ATENDIDO)]
    v = montar_veredito(_report("sucesso"), criteria_verdicts=cv)

    assert v.status == VerdictStatus.REPROVADO
    assert v.blocking_reason


def test_camada2_um_inconclusivo_reprova_global():
    cv = [_cv(CriterionStatus.ATENDIDO), _cv(CriterionStatus.INCONCLUSIVO)]
    v = montar_veredito(_report("sucesso"), criteria_verdicts=cv)

    assert v.status == VerdictStatus.REPROVADO
    assert v.blocking_reason


# ===========================================================================
# agregar_status — regra conservadora isolada
# ===========================================================================

def test_agregar_status_conservador():
    assert agregar_status([_cv(CriterionStatus.ATENDIDO)]) == VerdictStatus.APROVADO
    assert (
        agregar_status([_cv(CriterionStatus.ATENDIDO), _cv(CriterionStatus.ATENDIDO)])
        == VerdictStatus.APROVADO
    )
    assert agregar_status([_cv(CriterionStatus.NAO_ATENDIDO)]) == VerdictStatus.REPROVADO
    assert agregar_status([_cv(CriterionStatus.INCONCLUSIVO)]) == VerdictStatus.REPROVADO

def test_lista_vazia_reprova():
    """all([]) é True — sem esta guarda, zero critérios aprovariam vacuamente."""
    assert agregar_status([]) == VerdictStatus.REPROVADO


def test_execucao_ok_sem_vereditos_reprova():
    """Execução técnica OK mas nenhum critério julgado NÃO aprova o Work Item."""
    v = montar_veredito(_report("sucesso"))
    assert v.status == VerdictStatus.REPROVADO
    assert "Nenhum critério" in v.blocking_reason
