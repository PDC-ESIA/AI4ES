"""Unit tests for the HumanEval coder contract (default vs lean mode)."""

from __future__ import annotations

from benchmarks.coding_review.humaneval.contract import build_coder_message
from benchmarks.coding_review.humaneval.dataset import HumanEvalProblem

_P = HumanEvalProblem(
    task_id="HumanEval/0",
    prompt='def add(a: int, b: int) -> int:\n    """Soma a e b."""\n',
    entry_point="add",
    test="def check(c):\n    assert c(1, 2) == 3\n",
)


def test_default_message_keeps_coder_deliverables():
    msg = build_coder_message(_P)
    assert "Você ainda deve entregar `run.json` e `README.md`" in msg
    assert "MODO ENXUTO" not in msg


def test_lean_message_skips_non_graded_artifacts():
    msg = build_coder_message(_P, lean=True)
    assert "MODO ENXUTO" in msg
    assert "NÃO crie `PLAN.md`, `README.md`, `run.json`" in msg
    assert "Você ainda deve entregar" not in msg
    assert "`from solution import add`" in msg
