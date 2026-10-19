"""Testes do compare.py: comparação pareada entre dois runs."""

from __future__ import annotations

import json

import pytest

from benchmarks.coding_review.codejudgebench import compare


@pytest.mark.parametrize(
    ("so_a", "so_b", "esperado"),
    [
        (0, 0, 1.0),  # sem discordância, nada a testar
        (1, 1, 1.0),
        (2, 8, 0.109375),  # 2 * P(X <= 2), X ~ Bin(10, 0.5)
        (3, 26, 2 * (1 + 29 + 406 + 3654) / 2**29),
    ],
)
def test_mcnemar_exato(so_a, so_b, esperado):
    assert compare.mcnemar_exact(so_a, so_b) == pytest.approx(esperado)


def test_mcnemar_e_simetrico():
    assert compare.mcnemar_exact(3, 9) == compare.mcnemar_exact(9, 3)


def _resposta(verdict: str, kind: str = "ok") -> dict:
    return {"verdict": verdict, "outcome_kind": kind}


def _par(pair_id: str, outcome: str, pos: str, neg: str, kind: str = "ok") -> dict:
    return {
        "pair_id": pair_id,
        "difficulty": "easy",
        "outcome": outcome,
        "pos": _resposta(pos, kind),
        "neg": _resposta(neg, kind),
    }


def _gravar_run(pasta, pares, modelo="m", label=None):
    pasta.mkdir()
    relatorio = {
        "metadata": {"config": {"model": modelo}, "label": label, "code": {"commit": "a" * 40, "dirty": False}},
        "pairs": pares,
    }
    (pasta / "report.json").write_text(json.dumps(relatorio), encoding="utf-8")
    return pasta


@pytest.fixture
def runs(tmp_path):
    a = _gravar_run(
        tmp_path / "A",
        [
            _par("s/1", "tie_approve", "pass", "pass"),
            _par("s/2", "tie_approve", "pass", "pass"),
            _par("s/3", "correct", "pass", "fail"),
            _par("s/4", "operational", "absent", "absent", kind="operational"),
        ],
    )
    b = _gravar_run(
        tmp_path / "B",
        [
            _par("s/1", "correct", "pass", "fail"),
            _par("s/2", "tie_block", "fail", "fail"),
            _par("s/3", "correct", "pass", "fail"),
            _par("s/4", "correct", "pass", "fail"),
        ],
        label="fase-b",
    )
    return a, b


def test_compara_par_a_par(runs):
    resultado = compare.compare(*runs)
    acc = resultado["metricas"]["accuracy"]
    # s/4 fica de fora: é falha operacional em A.
    assert (acc["n"], acc["a"], acc["b"], acc["so_a"], acc["so_b"]) == (3, 1, 2, 0, 1)
    aprova = resultado["metricas"]["false_approve"]
    assert (aprova["a"], aprova["b"]) == (2, 0)
    bloqueia = resultado["metricas"]["false_block"]
    assert (bloqueia["a"], bloqueia["b"], bloqueia["so_b"]) == (0, 1, 1)


def test_lista_os_pares_que_mudaram(runs):
    mudancas = {m["pair_id"]: (m["a"], m["b"]) for m in compare.compare(*runs)["mudancas"]}
    assert mudancas == {
        "s/1": ("tie_approve", "correct"),
        "s/2": ("tie_approve", "tie_block"),
        "s/4": ("operational", "correct"),
    }


def test_avisa_quando_os_pares_diferem(tmp_path):
    a = _gravar_run(tmp_path / "A", [_par("s/1", "correct", "pass", "fail"), _par("s/2", "correct", "pass", "fail")])
    b = _gravar_run(tmp_path / "B", [_par("s/1", "correct", "pass", "fail"), _par("s/9", "correct", "pass", "fail")])
    resultado = compare.compare(a, b)
    assert resultado["pares_comuns"] == 1
    assert resultado["so_em_a"] == ["s/2"] and resultado["so_em_b"] == ["s/9"]
    assert "não avaliaram os mesmos pares" in compare.render_markdown(resultado)


def test_markdown_tem_leitura_e_rotulo(runs):
    texto = compare.render_markdown(compare.compare(*runs))
    assert "rótulo `fase-b`" in texto
    assert "piorou" in texto  # bloqueou código correto: 0 → 1
    assert "## Pares que mudaram de desfecho (3)" in texto


def test_cli_grava_arquivo(runs, tmp_path):
    saida = tmp_path / "comparacao.md"
    assert compare.main([str(runs[0]), str(runs[1]), "--output", str(saida)]) == 0
    assert saida.read_text(encoding="utf-8").startswith("# Comparação pareada")
