"""Unit tests for MBPP grading against the real DirectSandbox."""

from __future__ import annotations

import sys

import pytest

from benchmarks.coding_review.mbpp import bootstrap
from benchmarks.coding_review.mbpp.dataset import MbppProblem

if str(bootstrap.adk_dir()) not in sys.path:
    sys.path.insert(0, str(bootstrap.adk_dir()))

from benchmarks.coding_review.mbpp import grading  # noqa: E402

_ADD = MbppProblem(
    task_id="Mbpp/0",
    prompt="Add two numbers.",
    entry_point="add",
    test_list=["assert add(1, 2) == 3", "assert add(-1, 1) == 0"],
)
_CORRECT = "def add(a, b):\n    return a + b\n"


def _grade(tmp_path, rel: str, code: str, problem: MbppProblem = _ADD, **kw):
    sol = tmp_path / rel
    sol.parent.mkdir(parents=True, exist_ok=True)
    sol.write_text(code, encoding="utf-8")
    return grading.grade_solution(problem, tmp_path, sol, **kw)


def test_correct_solution_passes(tmp_path):
    assert _grade(tmp_path, "solution.py", _CORRECT).passed


def test_wrong_solution_fails_with_assertion(tmp_path):
    res = _grade(tmp_path, "solution.py", "def add(a, b):\n    return a - b\n")
    assert not res.passed
    assert "AssertionError" in res.reason


def test_only_later_assert_failing_still_fails(tmp_path):
    """Grading runs the FULL test_list, not only the example shown to the coder."""
    res = _grade(
        tmp_path, "solution.py", "def add(a, b):\n    return 3 if a == 1 else 99\n"
    )
    assert not res.passed


@pytest.mark.parametrize("rel", ["pkg/impl.py", "my-sol.py"])
def test_non_canonical_solution_location_is_gradable(tmp_path, rel):
    """Nested dirs and non-identifier filenames (fallback locator) must still load."""
    res = _grade(tmp_path, rel, _CORRECT)
    assert res.passed, res.stderr_tail


def test_nested_solution_can_import_sibling_module(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "helpers.py").write_text("def plus(a, b):\n    return a + b\n")
    code = "from helpers import plus\n\ndef add(a, b):\n    return plus(a, b)\n"
    assert _grade(tmp_path, "pkg/impl.py", code).passed


def test_test_imports_are_available_to_asserts(tmp_path):
    problem = MbppProblem(
        task_id="Mbpp/1",
        prompt="Square root.",
        entry_point="root",
        test_list=["assert math.isclose(root(4), 2.0)"],
        test_imports=["import math"],
    )
    code = "def root(x):\n    return x ** 0.5\n"
    assert _grade(tmp_path, "solution.py", code, problem=problem).passed


def test_timeout_is_reported(tmp_path):
    res = _grade(
        tmp_path, "solution.py", "def add(a, b):\n    while True:\n        pass\n",
        timeout=1,
    )
    assert not res.passed
    assert res.timed_out


def test_generic_failure_reason_includes_exception(tmp_path):
    res = _grade(tmp_path, "solution.py", "def add(a, b):\n    raise TypeError('boom')\n")
    assert not res.passed
    assert "TypeError: boom" in res.reason
