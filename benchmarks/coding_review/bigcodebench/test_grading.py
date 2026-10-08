"""Unit tests for BigCodeBench grading: failure classification + grade program.

The Docker sandbox itself is not exercised here (needs the sandbox image); the
generated grade program is executed locally to prove the unittest runner works.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from benchmarks.coding_review.bigcodebench import categories as c
from benchmarks.coding_review.bigcodebench import grading
from benchmarks.coding_review.bigcodebench.dataset import BigCodeBenchProblem

_TEST = """
import unittest
class TestCases(unittest.TestCase):
    def test_add(self):
        self.assertEqual(task_func(1, 2), 3)
"""
_PROBLEM = BigCodeBenchProblem(
    task_id="BigCodeBench/0",
    prompt="def task_func(a, b):\n    ...\n",
    entry_point="task_func",
    test=_TEST,
)


def _run_local(source: str, tmp_path, problem: BigCodeBenchProblem = _PROBLEM):
    script = tmp_path / "g.py"
    script.write_text(grading.build_grade_program(problem, source), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, timeout=60
    )


def test_grade_program_passes_on_correct_solution(tmp_path):
    r = _run_local("def task_func(a, b):\n    return a + b\n", tmp_path)
    assert r.returncode == 0
    assert grading._PASS_MARKER in r.stdout


def test_grade_program_fails_on_wrong_solution(tmp_path):
    r = _run_local("def task_func(a, b):\n    return a - b\n", tmp_path)
    assert r.returncode == 1
    assert grading._PASS_MARKER not in r.stdout
    assert grading.classify_failure(r.returncode, False, r.stderr) == c.LOGIC


def test_grade_program_missing_dependency(tmp_path):
    src = (
        "import biblioteca_que_nao_existe_xyz\ndef task_func(a, b):\n    return a + b\n"
    )
    r = _run_local(src, tmp_path)
    assert r.returncode == 1
    assert (
        grading.classify_failure(r.returncode, False, r.stderr) == c.MISSING_DEPENDENCY
    )


def test_grade_program_syntax_error(tmp_path):
    r = _run_local("def task_func(a, b:\n    return a\n", tmp_path)
    assert grading.classify_failure(r.returncode, False, r.stderr) == c.SYNTAX


def test_grade_program_without_tests_does_not_pass(tmp_path):
    problem = BigCodeBenchProblem("BigCodeBench/1", "", "task_func", "x = 1\n")
    r = _run_local("def task_func():\n    pass\n", tmp_path, problem)
    assert r.returncode != 0
    assert grading._PASS_MARKER not in r.stdout


@pytest.mark.parametrize(
    "stderr, expected",
    [
        ("ModuleNotFoundError: No module named 'foo'", c.MISSING_DEPENDENCY),
        ("ImportError: cannot import name 'x' from 'y'", c.IMPORT_ERROR),
        ("AttributeError: module 'pandas' has no attribute 'foo'", c.API_MISUSE),
        (
            "TypeError: read_csv() got an unexpected keyword argument 'z'",
            c.API_MISUSE,
        ),
        (
            'File "/usr/lib/site-packages/pandas/x.py", line 1\nTypeError: bad',
            c.API_MISUSE,
        ),
        ("AssertionError: 1 != 2", c.LOGIC),
        ("ValueError: boom", c.RUNTIME_ERROR),
        ("TypeError: bad thing in my own code", c.RUNTIME_ERROR),
        ("IndentationError: unexpected indent", c.SYNTAX),
        ("", c.RUNTIME_ERROR),
    ],
)
def test_classify_failure(stderr, expected):
    assert grading.classify_failure(1, False, stderr) == expected


def test_classify_timeout_wins():
    assert grading.classify_failure(124, True, "ModuleNotFoundError: x") == c.TIMEOUT


def test_missing_dependency_wins_over_assertion():
    stderr = "AssertionError: x\nModuleNotFoundError: No module named 'a'"
    assert grading.classify_failure(1, False, stderr) == c.MISSING_DEPENDENCY


def test_dotted_exception_names_are_recognised():
    stderr = "pandas.errors.ParserError: bad\nAssertionError: x"
    assert grading.classify_failure(1, False, stderr) == c.LOGIC
