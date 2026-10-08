"""Testes das três métricas (funções puras)."""

from __future__ import annotations

import pytest

from benchmarks.coding_review.swebench._testutils import ADK_DIR, module_constant
from benchmarks.coding_review.swebench.metrics import (
    PARADA_APROVACAO,
    PARADA_MAX_ITER,
    PARADA_OUTRO,
    PARADA_POLITICA,
    aggregate,
    classificar_parada,
    confusion_matrix,
    iteration_stats,
    rate,
    wilson_interval,
)

LOOP_POLICY = ADK_DIR / "src/agents/workflow_coding_review/executor/loop_policy.py"


def test_wilson_bate_com_valores_de_referencia():
    baixo, alto = wilson_interval(9, 30)
    assert baixo == pytest.approx(0.1667, abs=1e-3)
    assert alto == pytest.approx(0.4788, abs=1e-3)
    baixo, alto = wilson_interval(1, 5)
    assert baixo == pytest.approx(0.0362, abs=1e-3)
    assert alto == pytest.approx(0.6245, abs=1e-3)
    assert wilson_interval(0, 0) is None
    assert wilson_interval(0, 5)[0] == 0.0
    assert wilson_interval(5, 5)[1] == 1.0


@pytest.mark.parametrize(
    "motivo, rodadas, esperado",
    [
        ("aprovado", 3, (PARADA_APROVACAO, "aprovado")),
        ("aprovado", 20, (PARADA_APROVACAO, "aprovado")),
        ("bloqueado_plato_nota", 5, (PARADA_POLITICA, "bloqueado_plato_nota")),
        ("bloqueado_erro_repetido", 20, (PARADA_POLITICA, "bloqueado_erro_repetido")),
        ("aceito_com_ressalvas_plato_nota", 4,
         (PARADA_POLITICA, "aceito_com_ressalvas_plato_nota")),
        ("reprovado_apos_loop", 20, (PARADA_MAX_ITER, "reprovado_apos_loop")),
        ("validation_ausente_ou_invalida", 20,
         (PARADA_MAX_ITER, "validation_ausente_ou_invalida")),
        ("reprovado_apos_loop", 2, (PARADA_OUTRO, "reprovado_apos_loop")),
        ("erro_operacional", 20, (PARADA_OUTRO, "erro_operacional")),
        ("timeout_da_instancia", 7, (PARADA_OUTRO, "timeout_da_instancia")),
        (None, 0, (PARADA_OUTRO, "desconhecido")),
    ],
)
def test_classificacao_do_motivo_de_parada(motivo, rodadas, esperado):
    assert classificar_parada(motivo, rodadas, 20) == esperado


def test_todo_motivo_da_politica_cai_na_categoria_politica():
    motivos = [
        module_constant(LOOP_POLICY, nome)
        for nome in (
            "MOTIVO_PLATO",
            "MOTIVO_SEM_ALTERACAO",
            "MOTIVO_ERRO_REPETIDO",
            "MOTIVO_ORCAMENTO_FALHAS",
        )
    ]
    for motivo in motivos:
        for prefixo in ("bloqueado_", "aceito_com_ressalvas_"):
            assert classificar_parada(prefixo + motivo, 1, 20)[0] == PARADA_POLITICA


def test_matriz_de_confusao():
    pares = [(True, True), (True, False), (True, False), (False, True), (False, False)]
    assert confusion_matrix(pares) == {"vp": 1, "fp": 2, "fn": 1, "vn": 1}


def test_estatisticas_de_rodadas():
    stats = iteration_stats([1, 3, 3, 20])
    assert stats["media"] == 6.75 and stats["mediana"] == 3.0
    assert stats["distribuicao"] == {"1": 1, "3": 2, "20": 1}
    assert iteration_stats([])["n"] == 0


def _registro(iid, *, aprovado, grading, rodadas=2, motivo="aprovado", repo="django/django",
              comandos=("python -m pytest t.py",), status_testes="sucesso",
              identificados=3, patch_vazio=False, historico=None, **extra):
    return {
        "instance_id": iid,
        "repo": repo,
        "rodadas": rodadas,
        "historico_notas": historico if historico is not None else [0.5] * rodadas,
        "motivo_terminacao": motivo,
        "status_desfecho": "aprovado" if aprovado else "reprovado",
        "veredito_validador": "aprovado" if aprovado else "reprovado",
        "execucao": {
            "test_commands": list(comandos),
            "status_testes": status_testes,
            "testes_identificados": identificados,
        },
        "patch": {"vazio": patch_vazio},
        "grading": {"status": grading},
        "uso": {"prompt_tokens": 10, "completion_tokens": 5, "llm_interactions": 1},
        "duracao_s": 1.5,
        **extra,
    }


def test_agregacao_ponta_a_ponta():
    registros = [
        _registro("a", aprovado=True, grading="resolved"),
        _registro("b", aprovado=True, grading="unresolved", comandos=(),
                  status_testes="pulado", identificados=None),
        _registro("c", aprovado=False, grading="resolved", motivo="bloqueado_plato_nota",
                  rodadas=4, repo="sympy/sympy"),
        _registro("d", aprovado=False, grading="error", motivo="reprovado_apos_loop",
                  rodadas=20, historico=[0.1] * 19),
        _registro("e", aprovado=True, grading="empty_patch", patch_vazio=True),
    ]

    m = aggregate(registros, teto=20)

    m1 = m["metrica_1_resolucao"]
    assert (m1["k"], m1["n"]) == (2, 5)
    assert m1["por_status"] == {"empty_patch": 1, "error": 1, "resolved": 2, "unresolved": 1}

    m2 = m["metrica_2_loop"]
    assert m2["motivo_parada"] == {
        PARADA_APROVACAO: 3, PARADA_MAX_ITER: 1, PARADA_POLITICA: 1
    }
    assert m2["divergencias_rodadas_vs_historico"] == ["d"]

    m3 = m["metrica_3_validador"]
    assert m3["com_gabarito"] == 4 and m3["sem_gabarito"] == 1
    assert m3["matriz"] == {"vp": 1, "fp": 2, "fn": 1, "vn": 0}
    assert m3["falsos_positivos_ids"] == ["b", "e"]
    assert m3["aprovacoes_qualificadas"] == {"patch_vazio": 1, "suite_vazia_ou_pulada": 1}
    assert m3["taxa_fp_entre_aprovadas"]["k"] == 2
    assert m3["taxa_fp_entre_aprovadas"]["n"] == 3

    assert m["por_repositorio"]["django/django"] == {"n": 4, "resolvidas": 1, "aprovadas": 3}
    assert m["operacional"]["uso_llm"]["total_tokens"] == 75


def test_causas_exclusoes_e_uso_por_agente():
    registros = [
        _registro("a", aprovado=True, grading="unresolved",
                  uso={"prompt_tokens": 10, "completion_tokens": 1, "llm_interactions": 2,
                       "por_agente": {"implementation_validator": {
                           "prompt_tokens": 4, "completion_tokens": 1, "llm_interactions": 1}}}),
        _registro("b", aprovado=False, grading="falha_preparacao", rodadas=0, historico=[]),
        _registro("c", aprovado=True, grading="resolved"),
    ]
    registros[0]["grading"]["causa"] = "patch_nao_aplicou"
    registros[1]["grading"]["causa"] = "falha_preparacao"

    m = aggregate(registros, teto=20, excluidas={"a"})

    m1 = m["metrica_1_resolucao"]
    assert m1["causas_nao_resolvidas"] == {"falha_preparacao": 1, "patch_nao_aplicou": 1}
    assert (m1["sem_exclusoes_gold"]["k"], m1["sem_exclusoes_gold"]["n"]) == (1, 2)
    m3 = m["metrica_3_validador"]
    assert m3["com_gabarito"] == 1 and m3["excluidas_gold"] == 1  # "b" sem gabarito
    assert m3["falsos_positivos"] == 0
    uso = m["operacional"]["uso_llm"]
    assert uso["por_agente"]["implementation_validator"]["prompt_tokens"] == 4


def test_intervalo_nao_sofre_arredondamento_duplo_ao_exibir():
    """Regressão: 20/26 tem IC inferior 57,948%; com 4 casas guardadas, virava 58,0%."""
    from benchmarks.coding_review.swebench import report

    bloco = rate(20, 26)
    assert report._pct(bloco["ic95"][0]) == "57.9%"
    assert report._pct(bloco["ic95"][1]) == "89.0%"
    assert report._pct(bloco["taxa"]) == "76.9%"
