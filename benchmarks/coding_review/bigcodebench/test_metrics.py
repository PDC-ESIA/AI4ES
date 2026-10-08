"""Unit tests for BigCodeBench metrics (pass@1, failure aggregation, baseline)."""

from __future__ import annotations

import json

from benchmarks.coding_review.bigcodebench import metrics


def _r(passed, category="passed"):
    return {"passed": passed, "category": category}


def test_pass_at_1():
    assert metrics.pass_at_1([_r(True), _r(False, "logic")]) == 0.5
    assert metrics.pass_at_1([]) == 0.0


def test_aggregate_failures_groups():
    res = [
        _r(True),
        _r(False, "missing_dependency"),
        _r(False, "api_misuse"),
        _r(False, "logic"),
        _r(False, "runtime_error"),
        _r(False, "timeout"),
    ]
    f = metrics.aggregate_failures(res)
    assert f["total_failures"] == 5
    assert f["by_group"] == {"library": 2, "logic": 2, "other": 1}
    assert f["by_category"]["logic"] == 1


def test_load_baseline_from_dir_and_file(tmp_path):
    rel = {"model": "m", "num_problems": 50, "pass_at_k": {"pass@1": 0.9}}
    (tmp_path / "report.json").write_text(json.dumps(rel), encoding="utf-8")
    assert metrics.load_baseline(tmp_path)["pass_at_1"] == 0.9
    assert metrics.load_baseline(tmp_path / "report.json")["num_problems"] == 50
    assert metrics.load_baseline(tmp_path / "nope") is None


def test_compare_with_baseline():
    comp = metrics.compare_with_baseline(
        0.4, {"pass_at_1": 0.8, "model": "m", "num_problems": 50, "source": "s"}
    )
    assert comp["delta_pp"] == -40.0
    assert comp["relative_drop_pct"] == 50.0
