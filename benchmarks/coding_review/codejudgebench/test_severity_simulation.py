"""Testes da simulação de regras de severidade (fase B)."""

from __future__ import annotations

import pytest

from benchmarks.coding_review.codejudgebench import severity_simulation as sim
from benchmarks.coding_review.codejudgebench.dataset import RepairPair

_SO_DESEMPENHO = (
    "## Status: BLOQUEADO\n## Issues\n- Severity: critical\n  File: solution.py — Camada: corretude\n"
    "  Descrição: complexidade O(N^2) com N até 10^5 causará TLE.\n"
)
_LOGICA = (
    "## Status: BLOQUEADO\n## Issues\n- Severity: critical\n  File: solution.py — Camada: corretude\n"
    "  Descrição: off-by-one no laço produz resultado incorreto.\n"
)


def _par(erro: str) -> RepairPair:
    return RepairPair(
        pair_id="claude_3.7_sonnet/1",
        split="claude_3.7_sonnet",
        row_idx=1,
        question_id="q",
        question_title="t",
        question_content="c",
        platform="atcoder",
        difficulty="easy",
        starter_code="",
        wrong_code="x",
        pos_response="p",
        neg_response="n",
        wrong_meta={"error_message": erro},
    )


@pytest.mark.parametrize(
    ("markdown", "erro", "regra", "esperado"),
    [
        (_SO_DESEMPENHO, "Wrong answer", "V0", "fail"),
        (_SO_DESEMPENHO, "Wrong answer", "V1", "pass"),
        (_SO_DESEMPENHO, "Wrong answer", "V2", "pass"),
        (_SO_DESEMPENHO, "Time Limit Exceeded", "V1", "pass"),
        (_SO_DESEMPENHO, "Time Limit Exceeded", "V2", "fail"),  # a correção era sobre desempenho
        (_LOGICA, "Wrong answer", "V1", "fail"),  # erro de lógica nunca é rebaixado
    ],
)
def test_regras(markdown, erro, regra, esperado):
    assert sim.veredito_simulado(markdown, _par(erro), regra) == esperado


def test_sem_issue_critica_aprova():
    assert sim.veredito_simulado("## Status: APROVADO\n## Issues\nNenhum.\n", _par("x"), "V0") == "pass"
