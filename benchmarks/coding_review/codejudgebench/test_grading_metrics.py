"""Testes unitários de grading.py e metrics.py do CodeJudgeBench."""

from __future__ import annotations

import pytest

from benchmarks.coding_review.codejudgebench import grading, metrics


def _resp(verdict: str, kind: str = "ok", *, erro: str | None = None, tentativas: list[dict] | None = None, issues=None) -> dict:
    if tentativas is None:
        tentativas = [
            {
                "verdict": verdict,
                "lenient_status": {"pass": "APROVADO", "fail": "BLOQUEADO"}.get(verdict),
                "gate_applied": False,
                "duration_s": 10.0,
                "error": erro,
                "llm_interactions": 2,
                "prompt_tokens": 100,
                "completion_tokens": 20,
            }
        ]
    return {"verdict": verdict, "outcome_kind": kind, "code_found": kind != "no_code", "attempts": tentativas, "issues": issues or []}


def _registro(pos: dict, neg: dict, dificuldade: str = "easy") -> dict:
    return {"pair_id": "p", "difficulty": dificuldade, "outcome": grading.grade_pair(pos, neg), "pos": pos, "neg": neg}


# ---------------------------------------------------------------------------
# grading
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pos", "neg", "esperado"),
    [
        ("pass", "fail", "correct"),
        ("fail", "pass", "wrong"),
        ("pass", "pass", "tie_approve"),
        ("fail", "fail", "tie_block"),
    ],
)
def test_desfechos_julgados(pos, neg, esperado):
    assert grading.grade_pair(_resp(pos), _resp(neg)) == esperado


def test_falha_operacional_tem_precedencia():
    assert grading.grade_pair(_resp("absent", "operational"), _resp("absent", "invalid")) == "operational"


def test_resposta_invalida_exclui_o_par():
    assert grading.grade_pair(_resp("pass"), _resp("absent", "invalid")) == "invalid"


def test_sem_codigo_exclui_o_par():
    assert grading.grade_pair(_resp("absent", "no_code"), _resp("fail")) == "no_code"


# ---------------------------------------------------------------------------
# wilson
# ---------------------------------------------------------------------------


def test_wilson_valores_conhecidos():
    # 35/50 = 70% → IC de Wilson ≈ [56.2%, 80.9%]
    baixo, alto = metrics.wilson_interval(35, 50)
    assert baixo == pytest.approx(0.5623, abs=1e-3)
    assert alto == pytest.approx(0.8093, abs=1e-3)


def test_wilson_extremos_ficam_em_0_1():
    assert metrics.wilson_interval(0, 10)[0] == 0.0
    assert metrics.wilson_interval(10, 10)[1] == 1.0


def test_wilson_sem_amostra():
    assert metrics.wilson_interval(0, 0) is None


# ---------------------------------------------------------------------------
# compute_metrics
# ---------------------------------------------------------------------------


@pytest.fixture
def registros() -> list[dict]:
    critica_testes = [{"severity": "critical", "layer": "testes", "description": "sem testes", "file": None}]
    return [
        _registro(_resp("pass"), _resp("fail"), "easy"),  # correct
        _registro(_resp("pass"), _resp("fail"), "hard"),  # correct
        _registro(_resp("fail"), _resp("pass"), "hard"),  # wrong
        _registro(_resp("pass"), _resp("pass"), "easy"),  # tie_approve
        _registro(_resp("fail", issues=critica_testes), _resp("fail"), "easy"),  # tie_block
        _registro(_resp("absent", "operational", erro="quota"), _resp("absent", "operational", erro="quota")),
    ]


def test_acuracia_exclui_operacional_e_conta_empate_como_erro(registros):
    j = metrics.compute_metrics(registros)["judgment"]
    assert j["accuracy"]["k"] == 2 and j["accuracy"]["n"] == 5
    assert j["accuracy"]["value"] == 0.4
    assert j["accuracy_ties_half"] == pytest.approx((2 + 0.5 * 2) / 5)
    assert j["decisiveness"]["value"] == 0.6
    assert j["accuracy_when_decided"]["value"] == pytest.approx(2 / 3, abs=1e-4)
    assert j["positional_bias"] is None


def test_taxas_por_resposta(registros):
    d = metrics.compute_metrics(registros)["decision"]
    # neg julgadas: fail, fail, pass, pass, fail → 2 aprovadas de 5
    assert (d["false_approve_rate"]["k"], d["false_approve_rate"]["n"]) == (2, 5)
    # pos julgadas: pass, pass, fail, pass, fail → 2 bloqueadas de 5
    assert (d["false_block_rate"]["k"], d["false_block_rate"]["n"]) == (2, 5)
    assert d["critical_issue_layers_on_false_blocks"] == {"testes": 1}


def test_por_dificuldade(registros):
    por = metrics.compute_metrics(registros)["by_difficulty"]
    assert (por["easy"]["k"], por["easy"]["n"]) == (1, 3)
    assert (por["hard"]["k"], por["hard"]["n"]) == (1, 2)


def test_falha_operacional_nao_conta_como_invalida(registros):
    m = metrics.compute_metrics(registros)
    assert m["format"]["invalid_first_attempt_rate"]["k"] == 0
    assert m["format"]["invalid_first_attempt_rate"]["n"] == 10  # 12 respostas − 2 com erro de API
    assert m["operational"]["responses_with_operational_error"] == 2


def test_invalida_na_1a_e_valida_no_retry():
    tentativas = [
        {"verdict": "absent", "lenient_status": "APROVADO", "gate_applied": False, "duration_s": 5, "error": None},
        {"verdict": "pass", "lenient_status": "APROVADO", "gate_applied": False, "duration_s": 5, "error": None},
    ]
    registro = _registro(_resp("pass", tentativas=tentativas), _resp("fail"))
    f = metrics.compute_metrics([registro])["format"]
    assert f["invalid_first_attempt_rate"]["k"] == 1
    assert f["invalid_final_rate"]["k"] == 0
    assert f["responses_with_retry"] == 1
    assert f["format_only_failures"] == 1


def test_uso_somado(registros):
    uso = metrics.compute_metrics(registros)["usage"]
    assert uso["reviews"] == 12
    assert uso["prompt_tokens"] == 1200


def test_sem_registros():
    m = metrics.compute_metrics([])
    assert m["judgment"]["accuracy"]["value"] is None
    assert m["judgment"]["accuracy"]["ci95"] is None
