"""Testes do regrade.py: relê as revisões salvas sem tocar nos vereditos."""

from __future__ import annotations

import json

from benchmarks.coding_review.codejudgebench import regrade, run
from benchmarks.coding_review.codejudgebench.metrics import compute_metrics


def _resposta(verdict: str, issues: list[dict]) -> dict:
    return {
        "which": "pos",
        "verdict": verdict,
        "outcome_kind": "ok",
        "code_found": True,
        "attempts": [{"verdict": verdict, "error": None, "lenient_status": None, "gate_applied": False, "duration_s": 1.0}],
        "issues": issues,
    }


def test_slug_igual_ao_do_dataset():
    assert regrade._slug("claude_3.7_sonnet/42") == "claude_3_7_sonnet_0042"


def test_regrade_rele_issues_e_preserva_vereditos(tmp_path):
    antiga = [{"severity": "critical", "layer": "unknown", "description": "x", "file": None}]
    registro = {
        "pair_id": "claude_3.7_sonnet/42",
        "difficulty": "hard",
        "platform": "leetcode",
        "outcome": "tie_block",
        "pos": _resposta("fail", antiga),
        "neg": _resposta("fail", []),
    }
    relatorio = {
        "generated_at": "ontem",
        "complete": True,
        "total_duration_s": 1.0,
        "metadata": {"config": run._config(run._parse_args(["--model", "m"])), "dataset": {}},
        "metrics": compute_metrics([registro]),
        "pairs": [registro],
    }
    (tmp_path / "report.json").write_text(json.dumps(relatorio), encoding="utf-8")
    (tmp_path / "reviews").mkdir()
    (tmp_path / "reviews" / "claude_3_7_sonnet_0042_pos.md").write_text(
        "## Status: BLOQUEADO\n\n## Issues\n- Severity: critical\n  File: solution.py — Camada: corretude\n",
        encoding="utf-8",
    )

    novo = regrade.regrade(tmp_path)

    assert novo["pairs"][0]["pos"]["verdict"] == "fail"
    assert novo["pairs"][0]["outcome"] == "tie_block"
    assert novo["pairs"][0]["pos"]["issues"][0]["layer"] == "corretude"
    assert novo["metrics"]["decision"]["critical_issue_layers_on_false_blocks"] == {"corretude": 1}
    assert "regraded_at" in json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert (tmp_path / "report.md").is_file()
