"""Testes da nota de aceite e da composição com a nota técnica (Fases 5 e 6)."""

from __future__ import annotations

import pytest

from src.agents.workflow_coding_review.executor.acceptance_score import (
    PESO_TECNICO,
    calcular_nota_aceite,
    nota_unificada,
)


def _report(*outcomes) -> dict:
    """ExecutionReport mínimo com uma evidência por outcome informado."""
    return {
        "criteria_evidence": [
            {
                "criterion": f"Critério {indice + 1}",
                "criterion_id": f"CA-{indice + 1:02d}",
                "outcome": outcome,
                "automatable": outcome != "nao_automatizavel",
                "checkable": outcome in ("atendido", "nao_atendido"),
                "check_performed": "-",
                "observed": "-",
            }
            for indice, outcome in enumerate(outcomes)
        ]
    }


# ---------------------------------------------------------------------------
# Nota e cobertura
# ---------------------------------------------------------------------------


def test_nota_considera_apenas_os_criterios_decididos():
    """3 atendidos, 1 não atendido, 2 sem verificação → nota 0.75, cobertura 4/6."""
    aceite = calcular_nota_aceite(
        _report(
            "atendido",
            "atendido",
            "atendido",
            "nao_atendido",
            "sem_teste_mapeado",
            "nao_automatizavel",
        )
    )

    assert aceite.nota == 0.75
    assert aceite.cobertura == pytest.approx(4 / 6)
    assert aceite.total == 6
    assert (aceite.atendidos, aceite.nao_atendidos, aceite.decididos) == (3, 1, 4)


def test_criterio_nao_verificado_nao_puxa_a_nota_para_baixo():
    """O ponto do desenho: cegueira do harness não vira desconto na nota."""
    so_atendidos = calcular_nota_aceite(_report("atendido", "atendido"))
    com_lacunas = calcular_nota_aceite(
        _report("atendido", "atendido", "nao_automatizavel", "sem_teste_mapeado")
    )

    assert com_lacunas.nota == so_atendidos.nota == 1.0
    # A incerteza aparece na cobertura, que é onde ela pertence.
    assert com_lacunas.cobertura == 0.5
    assert so_atendidos.cobertura == 1.0


def test_nada_decidido_devolve_nota_none_e_nao_zero():
    """`None` = 'não verifiquei'; zero seria 'verifiquei e não atende'."""
    aceite = calcular_nota_aceite(
        _report("sem_teste_mapeado", "nao_automatizavel", "teste_nao_executado")
    )

    assert aceite.nota is None
    assert aceite.cobertura == 0.0
    assert aceite.total == 3


def test_sem_criterios_nao_ha_dimensao_de_aceite():
    aceite = calcular_nota_aceite({"criteria_evidence": []})

    assert aceite.nota is None
    assert aceite.cobertura == 0.0
    assert aceite.total == 0
    assert aceite.criterios_enderecaveis == []


def test_todos_nao_atendidos_dao_nota_zero():
    aceite = calcular_nota_aceite(_report("nao_atendido", "nao_atendido"))

    assert aceite.nota == 0.0
    assert aceite.cobertura == 1.0


# ---------------------------------------------------------------------------
# Critérios endereçáveis — a base do aviso de cobertura
# ---------------------------------------------------------------------------


def test_enderecaveis_sao_so_os_que_o_coder_pode_fechar():
    aceite = calcular_nota_aceite(
        _report(
            "atendido",
            "sem_teste_mapeado",
            "teste_nao_executado",
            "nao_automatizavel",
        )
    )

    # CA-04 (nao_automatizavel) fica de fora: cobrar dele é pedir o impossível.
    assert aceite.criterios_enderecaveis == ["CA-02", "CA-03"]


def test_enderecavel_sem_id_cai_para_o_texto_do_criterio():
    """Report antigo, sem `criterion_id`: ainda dá para nomear a pendência."""
    aceite = calcular_nota_aceite(
        {
            "criteria_evidence": [
                {"criterion": "Critério sem id", "outcome": "sem_teste_mapeado"}
            ]
        }
    )

    assert aceite.criterios_enderecaveis == ["Critério sem id"]


# ---------------------------------------------------------------------------
# Totalidade — a entrada é um report que pode estar ausente ou corrompido
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "report",
    [
        None,
        {},
        "texto",
        42,
        {"criteria_evidence": None},
        {"criteria_evidence": "texto"},
        {"criteria_evidence": [None, 42, "x"]},
    ],
)
def test_report_inutilizavel_degrada_sem_levantar(report):
    aceite = calcular_nota_aceite(report)

    assert aceite.nota is None
    assert aceite.cobertura == 0.0
    assert aceite.total == 0


def test_outcome_desconhecido_conta_como_nao_decidido():
    """Valor fora do enum nunca vira atendimento."""
    aceite = calcular_nota_aceite(
        {"criteria_evidence": [{"criterion": "X", "outcome": "xpto"}]}
    )

    assert aceite.nota is None
    assert aceite.total == 1
    assert aceite.por_resultado == {"desconhecido": 1}


def test_report_antigo_sem_outcome_nao_inventa_atendimento():
    aceite = calcular_nota_aceite(
        {"criteria_evidence": [{"criterion": "X", "checkable": True}]}
    )

    assert aceite.nota is None
    assert aceite.cobertura == 0.0


def test_como_dict_e_serializavel_e_completo():
    aceite = calcular_nota_aceite(_report("atendido", "sem_teste_mapeado"))
    dados = aceite.como_dict()

    assert dados["nota"] == 1.0
    assert dados["cobertura"] == 0.5
    assert dados["total"] == 2
    assert dados["atendidos"] == 1
    assert dados["decididos"] == 1
    assert dados["criterios_enderecaveis"] == ["CA-02"]


# ---------------------------------------------------------------------------
# Composição com a nota técnica (Fase 6)
# ---------------------------------------------------------------------------


def test_nota_unificada_pondera_as_duas_dimensoes():
    assert nota_unificada(1.0, 0.0) == PESO_TECNICO
    assert nota_unificada(0.0, 1.0) == pytest.approx(1.0 - PESO_TECNICO)
    assert nota_unificada(1.0, 1.0) == 1.0
    assert nota_unificada(0.8, 0.5) == pytest.approx(0.65 * 0.8 + 0.35 * 0.5)


def test_sem_nota_de_aceite_o_peso_e_redistribuido_para_a_tecnica():
    """Dimensão que não se aplica sai da conta — nunca entra valendo zero.

    Sem isso, uma entrega correta cujos critérios são todos de interface ficaria
    com teto artificial de 0.65: exatamente o defeito que motivou remover o
    degrau de critérios da nota técnica.
    """
    assert nota_unificada(0.9, None) == 0.9
    assert nota_unificada(1.0, None) == 1.0


def test_sem_nota_tecnica_nao_ha_nota_final():
    assert nota_unificada(None, 1.0) is None
    assert nota_unificada(None, None) is None


def test_aceite_zero_e_diferente_de_aceite_ausente():
    """Verificar e reprovar desconta; não conseguir verificar, não."""
    assert nota_unificada(1.0, 0.0) == PESO_TECNICO
    assert nota_unificada(1.0, None) == 1.0
