"""Unit tests for the BigCodeBench dataset loader (offline, synthetic parquet)."""

from __future__ import annotations

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from benchmarks.coding_review.bigcodebench import dataset


@pytest.fixture
def parquet_path(tmp_path):
    rows = [
        {
            "task_id": f"BigCodeBench/{i}",
            "complete_prompt": f'def task_func():\n    """task {i}"""\n',
            "entry_point": "task_func",
            "test": "import unittest\nclass TestCases(unittest.TestCase):\n    pass\n",
            "libs": "['numpy', 'pandas']",
            "canonical_solution": "    return 1\n",
        }
        for i in (10, 2, 33, 4, 5, 61, 7, 8, 9, 100)
    ]
    path = tmp_path / "bcb.parquet"
    pq.write_table(pa.Table.from_pylist(rows), path)
    return path


def test_load_all_sorted_by_task_number(parquet_path):
    probs = dataset.load_problems(parquet_path)
    assert [p.task_id for p in probs][:3] == [
        "BigCodeBench/2",
        "BigCodeBench/4",
        "BigCodeBench/5",
    ]
    assert len(probs) == 10


def test_libs_parsed_and_prompt_is_complete_prompt(parquet_path):
    p = dataset.load_problems(parquet_path, limit=1, seed=1)[0]
    assert p.libs == ("numpy", "pandas")
    assert p.entry_point == "task_func"
    assert p.prompt.startswith("def task_func")


def test_limit_is_deterministic_for_same_seed(parquet_path):
    a = dataset.load_problems(parquet_path, limit=4, seed=7)
    b = dataset.load_problems(parquet_path, limit=4, seed=7)
    assert [p.task_id for p in a] == [p.task_id for p in b]
    assert len(a) == 4


def test_limit_differs_across_seeds(parquet_path):
    ids = {
        tuple(p.task_id for p in dataset.load_problems(parquet_path, limit=4, seed=s))
        for s in range(10)
    }
    assert len(ids) > 1


def test_limit_result_is_sorted_by_task_number(parquet_path):
    probs = dataset.load_problems(parquet_path, limit=5, seed=3)
    nums = [int(p.task_id.split("/")[1]) for p in probs]
    assert nums == sorted(nums)


def test_task_ids_filter_accepts_slug_and_ignores_limit(parquet_path):
    probs = dataset.load_problems(
        parquet_path, task_ids=["BigCodeBench/2", "BigCodeBench_4"], limit=1
    )
    assert [p.task_id for p in probs] == ["BigCodeBench/2", "BigCodeBench/4"]


def test_parse_libs_handles_garbage():
    assert dataset._parse_libs("not a list") == ()
    assert dataset._parse_libs(None) == ()
    assert dataset._parse_libs(["a", "b"]) == ("a", "b")
