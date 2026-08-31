"""Testes da leitura de aceite: contagem, cobertura e entrada na nota única.

A composição por fora (`nota_unificada`/`PESO_TECNICO`) deixou de existir na PoC
do QA no loop (#394): os critérios entram na MESMA escada de capacidades, como o
degrau `CRITERIOS_ATENDIDOS`. As propriedades que aqueles testes protegiam
continuam valendo e são exercidas aqui contra a nota unificada.
"""

from __future__ import annotations

import pytest

from src.agents.workflow_coding_review.executor.acceptance_score import (
    calcular_nota_aceite,
)
from src.agents.workflow_coding_review.executor.progress_score import (
    CHAVE_FONTE_EVIDENCIA,
    FONTE_QA_E2E,
    Degrau,
    calcular_nota,
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
# Entrada do aceite na nota única (PoC #394 — QA no loop)
# ---------------------------------------------------------------------------


def _report_tecnico_verde(*outcomes, fonte_qa: bool = True) -> dict:
    """Report com toda a parte técnica em sucesso e os critérios informados.

    Isola a dimensão de aceite: qualquer variação da nota nestes testes vem do
    degrau de critérios, nunca dos degraus técnicos.

    `fonte_qa` marca a evidência como vinda da navegação independente — sem esse
    marcador o degrau de critérios NÃO pontua (ver
    `test_evidencia_do_harness_nao_alimenta_o_degrau`).
    """
    return {
        **({CHAVE_FONTE_EVIDENCIA: FONTE_QA_E2E} if fonte_qa else {}),
        "stages": [
            {
                "stage": "preparacao_ambiente",
                "status": "sucesso",
                "evidence": {"surface": "service", "test_commands": ["pytest -v"]},
            },
            {"stage": "implantacao_artefato", "status": "sucesso"},
            {"stage": "inicializacao_aplicacao", "status": "sucesso"},
            {
                "stage": "testes_automatizados",
                "status": "sucesso",
                "evidence": {
                    "resultados": [
                        {"resumo": {"passaram": 5, "falharam": 0, "erros": 0}}
                    ]
                },
            },
        ],
        **_report(*outcomes),
    }


def test_criterios_decididos_entram_na_nota_unica():
    """O degrau vale `atendidos / decididos` e puxa a nota para baixo."""
    nota = calcular_nota(_report_tecnico_verde("atendido", "nao_atendido"))

    assert Degrau.CRITERIOS_ATENDIDOS in nota.degraus_aplicaveis
    assert nota.por_degrau[Degrau.CRITERIOS_ATENDIDOS] == pytest.approx(0.5)
    assert nota.total < 1.0


def test_sem_criterio_decidido_o_peso_e_redistribuido():
    """Dimensão que não se aplica sai da conta — nunca entra valendo zero.

    Sem isso, uma entrega correta cujos critérios são todos de interface ficaria
    com teto artificial: exatamente o defeito que motivou remover este degrau no
    passado, e a razão de a aplicabilidade dele depender da evidência.
    """
    nota = calcular_nota(
        _report_tecnico_verde("nao_automatizavel", "sem_teste_mapeado")
    )

    assert Degrau.CRITERIOS_ATENDIDOS not in nota.degraus_aplicaveis
    assert nota.total == 1.0
    # Tolerância folgada de propósito: `pesos_efetivos` é o detalhamento
    # ARREDONDADO para o histórico, e a soma dos arredondados não fecha exato. A
    # nota em si é calculada com os pesos sem arredondar — é ela que precisa ser
    # exata, e o `total == 1.0` acima é quem garante isso.
    assert sum(nota.pesos_efetivos.values()) == pytest.approx(1.0, abs=1e-5)


def test_aceite_zero_e_diferente_de_aceite_ausente():
    """Verificar e reprovar desconta; não conseguir verificar, não."""
    reprovado = calcular_nota(_report_tecnico_verde("nao_atendido"))
    nao_verificado = calcular_nota(_report_tecnico_verde("nao_automatizavel"))

    assert reprovado.total < nao_verificado.total
    assert nao_verificado.total == 1.0


def test_cobertura_viaja_com_a_nota_sem_entrar_nela():
    """Cobertura informa o quanto deu para verificar; não desconta."""
    nota = calcular_nota(_report_tecnico_verde("atendido", "nao_automatizavel"))

    assert nota.aceite.cobertura == pytest.approx(0.5)
    # Todos os critérios DECIDIDOS passaram, então o degrau vale 1.0 — a
    # cobertura parcial não puxa a nota para baixo.
    assert nota.por_degrau[Degrau.CRITERIOS_ATENDIDOS] == pytest.approx(1.0)
    assert nota.total == 1.0


def test_evidencia_do_harness_nao_alimenta_o_degrau():
    """A trava central da PoC: só evidência do QA independente pontua.

    O estágio 7 do harness também emite `atendido`/`nao_atendido`, mas derivados
    de testes que o PRÓPRIO CODER escreveu e vinculou no `run.json`. Deixá-los
    pontuar daria 30% da nota para o coder se autoavaliar — o problema que este
    trabalho existe para eliminar.
    """
    do_qa = calcular_nota(_report_tecnico_verde("nao_atendido", fonte_qa=True))
    do_harness = calcular_nota(_report_tecnico_verde("nao_atendido", fonte_qa=False))

    assert Degrau.CRITERIOS_ATENDIDOS in do_qa.degraus_aplicaveis
    assert do_qa.total < 1.0

    assert Degrau.CRITERIOS_ATENDIDOS not in do_harness.degraus_aplicaveis
    assert do_harness.total == 1.0, (
        "evidência do coder puxou a nota: o degrau aceitou fonte não confiável"
    )
    # A cobertura continua sendo publicada nos dois casos — ela informa, não pontua.
    assert do_harness.aceite.cobertura == 1.0


def test_marcador_de_fonte_desconhecido_e_tratado_como_nao_confiavel():
    """Fail-closed: só o marcador exato libera o degrau."""
    report = _report_tecnico_verde("nao_atendido", fonte_qa=False)
    report[CHAVE_FONTE_EVIDENCIA] = "qualquer_outra_coisa"

    nota = calcular_nota(report)

    assert Degrau.CRITERIOS_ATENDIDOS not in nota.degraus_aplicaveis
