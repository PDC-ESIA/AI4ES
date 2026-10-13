"""Unit tests for the MBPP coder contract (default vs lean mode)."""

from __future__ import annotations

from benchmarks.coding_review.mbpp.contract import build_coder_message
from benchmarks.coding_review.mbpp.dataset import MbppProblem

_P = MbppProblem(
    task_id="Mbpp/11",
    prompt="Remove first and last occurrence of a char.",
    entry_point="remove_Occ",
    test_list=['assert remove_Occ("hello","l") == "heo"'],
)


def test_default_message_keeps_coder_deliverables():
    msg = build_coder_message(_P)
    assert "Você ainda deve entregar `run.json` e `README.md`" in msg
    assert "MODO ENXUTO" not in msg


def test_lean_message_skips_non_graded_artifacts():
    msg = build_coder_message(_P, lean=True)
    assert "MODO ENXUTO" in msg
    assert "NÃO crie `PLAN.md`, `README.md`, `run.json`" in msg
    assert "ETAPA 0" in msg
    assert "Você ainda deve entregar" not in msg
    # As regras que tornam a solução avaliável continuam lá.
    assert "`from solution import remove_Occ`" in msg
    assert 'assert remove_Occ("hello","l") == "heo"' in msg
