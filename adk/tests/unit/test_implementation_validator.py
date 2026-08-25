"""Tests para o Agente de Validação de Implementação.

A validação é dirigida por LLM em produção; aqui testamos a codificação
determinística da política de veredito (`montar_veredito`) sobre um
ExecutionReport mock — sem rodar o LLM real.

A política tem UMA regra: o veredito é sobre a EXECUÇÃO. Aprova quando o harness
conclui com `overall_status == "sucesso"`; reprova em qualquer outro caso. O
julgamento semântico dos critérios de aceite entra no veredito como registro e
NÃO altera o status — ver a docstring de `montar_veredito`.
"""

import pytest

from src.agents.implementation_validator.agent import (
    agent,
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
# Execução não bem-sucedida reprova
# ===========================================================================

@pytest.mark.parametrize("overall", ["erro", "falha"])
def test_execucao_falha_reprova_com_inconclusivos(overall):
    v = montar_veredito(_report(overall))

    assert v.status == VerdictStatus.REPROVADO
    assert v.blocking_reason  # preenchido
    assert overall in v.blocking_reason
    assert "implantacao_artefato" in v.blocking_reason
    assert "CONTAINER_NAO_INICIOU" in v.blocking_reason
    # Todos os critérios ficam inconclusivo (nenhum pôde ser comprovado)
    assert len(v.criteria_verdicts) == 2
    assert all(cv.status == CriterionStatus.INCONCLUSIVO for cv in v.criteria_verdicts)


def test_execucao_falha_tem_precedencia_sobre_criterios_positivos():
    # Mesmo recebendo vereditos positivos, a execução falha manda no resultado.
    v = montar_veredito(
        _report("erro"),
        criteria_verdicts=[_cv(CriterionStatus.ATENDIDO), _cv(CriterionStatus.ATENDIDO)],
    )
    assert v.status == VerdictStatus.REPROVADO
    assert all(cv.status == CriterionStatus.INCONCLUSIVO for cv in v.criteria_verdicts)


def test_report_inconsistente_com_testes_falhos_reprova():
    """Defesa da regressão observada: overall sucesso não apaga suíte vermelha."""
    report = _report("sucesso")
    report["stages"] = [
        {
            "stage": "testes_automatizados",
            "status": "falha",
            "error_code": "TESTES_FALHARAM",
        }
    ]

    v = montar_veredito(report)

    assert v.status == VerdictStatus.REPROVADO
    assert "testes_automatizados" in (v.blocking_reason or "")
    assert "TESTES_FALHARAM" in (v.blocking_reason or "")


# ===========================================================================
# Fail-closed: só "sucesso" aprova
# ===========================================================================

@pytest.mark.parametrize(
    "overall",
    [None, "", "pulado", "SUCESSO", "parcial", "desconhecido"],
    ids=["ausente", "vazio", "pulado", "caixa-alta", "status-novo", "status-invalido"],
)
def test_apenas_sucesso_literal_aprova(overall):
    """Qualquer coisa que não seja exatamente 'sucesso' reprova.

    A checagem é por igualdade, não por ausência dos valores de falha: um report
    truncado, sem o campo, ou com um status que ninguém previu aqui não pode ser
    lido como aprovação.
    """
    report = _report("sucesso")
    if overall is None:
        report.pop("overall_status")
    else:
        report["overall_status"] = overall

    assert montar_veredito(report).status == VerdictStatus.REPROVADO


# ===========================================================================
# Execução bem-sucedida aprova — independentemente do julgamento semântico
# ===========================================================================

def test_execucao_ok_aprova():
    cv = [_cv(CriterionStatus.ATENDIDO), _cv(CriterionStatus.ATENDIDO)]
    v = montar_veredito(_report("sucesso"), criteria_verdicts=cv)

    assert v.status == VerdictStatus.APROVADO
    assert v.blocking_reason is None
    assert v.criteria_verdicts == cv


def test_execucao_ok_sem_vereditos_aprova():
    """Execução OK e nenhum critério julgado APROVA.

    Regressão da mudança que tirou o julgamento semântico do gate: antes esta
    combinação reprovava ("nenhum critério avaliado"), o que na prática travava
    toda task cujos critérios o harness não instrumenta.
    """
    v = montar_veredito(_report("sucesso"))

    assert v.status == VerdictStatus.APROVADO
    assert v.blocking_reason is None
    assert v.criteria_verdicts == []


@pytest.mark.parametrize(
    "status_criterio",
    [CriterionStatus.NAO_ATENDIDO, CriterionStatus.INCONCLUSIVO],
)
def test_criterio_negativo_nao_derruba_execucao_bem_sucedida(status_criterio):
    """O caso que motivou a mudança.

    Um critério de UI que o harness não consegue comprovar volta como
    `inconclusivo` rodada após rodada. Enquanto isso reprovava, a nota de
    progresso empacava e a task morria por platô com o sistema construído,
    subindo e com a suíte verde.
    """
    cv = [_cv(CriterionStatus.ATENDIDO), _cv(status_criterio)]
    v = montar_veredito(_report("sucesso"), criteria_verdicts=cv)

    assert v.status == VerdictStatus.APROVADO
    assert v.blocking_reason is None
    # O julgamento segue registrado para auditoria, apenas não decide nada.
    assert v.criteria_verdicts == cv


def test_veredito_e_um_validation_verdict():
    assert isinstance(montar_veredito(_report("sucesso")), ValidationVerdict)
