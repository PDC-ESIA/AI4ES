"""Unit tests for the BigCodeBench coder contract (default vs lean mode)."""

from __future__ import annotations

from benchmarks.coding_review.bigcodebench.contract import build_coder_message
from benchmarks.coding_review.bigcodebench.dataset import BigCodeBenchProblem

_P = BigCodeBenchProblem(
    task_id="BigCodeBench/0",
    prompt='import numpy as np\n\ndef task_func(n):\n    """Soma de 0..n-1."""\n',
    entry_point="task_func",
    test="class TestCases: ...\n",
    libs=("numpy",),
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
    assert "`numpy`" in msg
