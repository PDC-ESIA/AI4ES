"""Testes do stability.py: estabilidade entre execuções repetidas."""

from __future__ import annotations

import json

import pytest

from benchmarks.coding_review.codejudgebench import stability


def _par(pair_id: str, pos: str, neg: str) -> dict:
    outcome = {
        ("pass", "fail"): "correct",
        ("fail", "pass"): "wrong",
        ("pass", "pass"): "tie_approve",
        ("fail", "fail"): "tie_block",
    }[(pos, neg)]
    return {"pair_id": pair_id, "outcome": outcome, "pos": {"verdict": pos}, "neg": {"verdict": neg}}


def _run(pasta, pares):
    pasta.mkdir()
    (pasta / "report.json").write_text(json.dumps({"pairs": pares}), encoding="utf-8")
    return pasta


@pytest.fixture
def tres_runs(tmp_path):
    # s/1: certo sempre · s/2: errado sempre · s/3: oscila (certo, certo, empate)
    return [
        _run(tmp_path / "r1", [_par("s/1", "pass", "fail"), _par("s/2", "pass", "pass"), _par("s/3", "pass", "fail")]),
        _run(tmp_path / "r2", [_par("s/1", "pass", "fail"), _par("s/2", "pass", "pass"), _par("s/3", "pass", "fail")]),
        _run(tmp_path / "r3", [_par("s/1", "pass", "fail"), _par("s/2", "pass", "pass"), _par("s/3", "fail", "fail")]),
    ]


def test_agregado_por_execucao(tres_runs):
    r = stability.stability(tres_runs)
    assert r["agregado"]["accuracy"]["por_execucao"] == [2, 2, 1]
    assert r["agregado"]["false_block"]["por_execucao"] == [0, 0, 1]


def test_estabilidade_par_a_par(tres_runs):
    r = stability.stability(tres_runs)
    assert (r["pares_sempre_certos"], r["pares_sempre_errados"], r["pares_instaveis"]) == (1, 1, 1)
    assert r["pares_mesmo_desfecho"] == 2
    assert r["respostas_mesmo_veredito"] == 5  # só a pos de s/3 muda


def test_voto_da_maioria(tres_runs):
    r = stability.stability(tres_runs)
    # s/3: pos pass, pass, fail → maioria pass; neg fail → acerto.
    assert r["maioria"]["acertos"] == 2
    assert r["maioria"]["bloqueia_pos"] == 0


def test_exige_duas_execucoes(tmp_path):
    with pytest.raises(ValueError, match="duas execuções"):
        stability.stability([_run(tmp_path / "r1", [_par("s/1", "pass", "fail")])])


def test_markdown(tres_runs):
    texto = stability.render_markdown(stability.stability(tres_runs))
    assert "Pares acertados sempre: 1" in texto
    assert "Voto da maioria" in texto
