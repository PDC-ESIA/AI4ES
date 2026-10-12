"""Unit tests for MBPP dataset loading and entry_point derivation."""

from __future__ import annotations

import json

import pytest

from benchmarks.coding_review.mbpp.dataset import (
    MbppProblem,
    _derive_entry_point,
    load_problems,
)


def test_derive_entry_point_single_function():
    """A single top-level function is used directly, no cross-check needed."""
    code = "def similar_elements(a, b):\n    return tuple(set(a) & set(b))\n"
    test_list = ["assert set(similar_elements((1,), (1,))) == set((1,))"]
    assert _derive_entry_point(2, code, test_list) == "similar_elements"


def test_derive_entry_point_multiple_functions_cross_check():
    """With multiple top-level defs, the one referenced in test_list wins."""
    code = (
        "def _helper(x):\n"
        "    return x * 2\n\n"
        "def target(x):\n"
        "    return _helper(x) + 1\n"
    )
    test_list = ["assert target(1) == 3"]
    assert _derive_entry_point(1, code, test_list) == "target"


def test_derive_entry_point_ambiguous_falls_back_to_last_candidate():
    """No test references any top-level def: fallback to the last one defined."""
    code = "def first():\n    pass\n\ndef second():\n    pass\n"
    test_list = ["assert True"]
    assert _derive_entry_point(1, code, test_list) == "second"


def test_derive_entry_point_no_function_returns_none():
    """Unparseable or function-less code yields None (caller skips the problem)."""
    assert _derive_entry_point(1, "x = 1\n", []) is None
    assert _derive_entry_point(1, "def broken(:\n", []) is None


def test_load_problems_from_local_fixture(tmp_path):
    """load_problems parses the sanitized-mbpp.json schema without hitting the network."""
    fixture = [
        {
            "source_file": "x.ipynb",
            "task_id": 2,
            "prompt": "Write a function to find shared elements.",
            "code": "def similar_elements(a, b):\n    return tuple(set(a) & set(b))\n",
            "test_imports": [],
            "test_list": [
                "assert set(similar_elements((1, 2), (2, 3))) == set((2,))",
            ],
        },
        {
            "source_file": "x.ipynb",
            "task_id": 3,
            "prompt": "Write a function using math.",
            "code": "import math\ndef is_not_prime(n):\n    return any(n % i == 0 for i in range(2, int(math.sqrt(n)) + 1))\n",
            "test_imports": ["import math"],
            "test_list": ["assert is_not_prime(10) == True"],
        },
    ]
    dataset_path = tmp_path / "sanitized-mbpp.json"
    dataset_path.write_text(json.dumps(fixture), encoding="utf-8")

    problemas = load_problems(dataset_path)

    assert len(problemas) == 2
    assert all(isinstance(p, MbppProblem) for p in problemas)
    assert problemas[0].task_id == "Mbpp/2"
    assert problemas[0].slug == "Mbpp_2"
    assert problemas[0].entry_point == "similar_elements"
    assert problemas[1].entry_point == "is_not_prime"
    assert problemas[1].test_imports == ["import math"]


def test_load_problems_filters_by_task_ids(tmp_path):
    """--task-ids accepts the 'Mbpp/N', slug and raw numeric id forms."""
    fixture = [
        {
            "task_id": 2,
            "prompt": "p2",
            "code": "def f2():\n    return 1\n",
            "test_imports": [],
            "test_list": ["assert f2() == 1"],
        },
        {
            "task_id": 3,
            "prompt": "p3",
            "code": "def f3():\n    return 1\n",
            "test_imports": [],
            "test_list": ["assert f3() == 1"],
        },
    ]
    dataset_path = tmp_path / "sanitized-mbpp.json"
    dataset_path.write_text(json.dumps(fixture), encoding="utf-8")

    problemas = load_problems(dataset_path, task_ids=["3"])
    assert [p.task_id for p in problemas] == ["Mbpp/3"]

    problemas = load_problems(dataset_path, task_ids=["Mbpp/2"])
    assert [p.task_id for p in problemas] == ["Mbpp/2"]


def _fixture_ids(tmp_path, ids):
    fixture = [
        {
            "task_id": i,
            "prompt": f"p{i}",
            "code": f"def f{i}():\n    return 1\n",
            "test_imports": [],
            "test_list": [f"assert f{i}() == 1"],
        }
        for i in ids
    ]
    path = tmp_path / "sanitized-mbpp.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")
    return path


def test_load_problems_split_test_usa_faixa_do_paper(tmp_path):
    """O split 'test' é task_id 11–510, inclusivo nas duas pontas."""
    path = _fixture_ids(tmp_path, [2, 10, 11, 300, 510, 511, 700])
    assert [p.task_id for p in load_problems(path, split="test")] == [
        "Mbpp/11", "Mbpp/300", "Mbpp/510",
    ]
    assert len(load_problems(path)) == 7


def test_load_problems_split_antes_de_limit(tmp_path):
    path = _fixture_ids(tmp_path, [2, 3, 11, 12, 13])
    assert [p.task_id for p in load_problems(path, split="test", limit=2)] == [
        "Mbpp/11", "Mbpp/12",
    ]


def test_load_problems_split_desconhecido(tmp_path):
    path = _fixture_ids(tmp_path, [11])
    with pytest.raises(ValueError, match="Split desconhecido"):
        load_problems(path, split="train")
