"""Unit tests for the BigCodeBench CLI: arg validation, resume guard, report."""

from __future__ import annotations

import argparse
import json

import pytest

from benchmarks.coding_review.bigcodebench import run


def _args(**kw):
    base = dict(
        model="gpt-4",
        limit=50,
        seed=42,
        task_ids=None,
        timeout=120,
        allow_network=False,
    )
    base.update(kw)
    return argparse.Namespace(**base)


def test_main_missing_model():
    with pytest.raises(ValueError, match="parâmetro '--model' é obrigatório"):
        run.main(["--limit", "5"])


def test_main_nonexistent_resume_dir(tmp_path):
    with pytest.raises(FileNotFoundError, match="não existe ou não é um diretório"):
        run.main(["--model", "gpt-4", "--resume-dir", str(tmp_path / "nada")])


def test_defaults_are_50_tasks_fixed_seed():
    args = run._parse_args(["--model", "m"])
    assert args.limit == 50
    assert args.seed == 42


def test_run_name_format():
    nome = run._construir_nome_run("github_copilot/gpt-4", 50, "20260101_120000")
    assert nome == "run_20260101_120000_github_copilot-gpt-4_n50"


def test_config_new_run_persists_metadata(tmp_path):
    run._validar_e_persistir_config(tmp_path, _args())
    saved = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    assert saved["model"] == "gpt-4"
    assert saved["seed"] == 42
    assert saved["limit"] == 50


def test_config_resume_valid(tmp_path):
    run._validar_e_persistir_config(tmp_path, _args())
    run._validar_e_persistir_config(tmp_path, _args())  # idêntico: não levanta


@pytest.mark.parametrize(
    "mudanca", [{"model": "outro"}, {"seed": 1}, {"limit": 10}, {"timeout": 5}]
)
def test_config_resume_mismatch(tmp_path, mudanca):
    run._validar_e_persistir_config(tmp_path, _args())
    with pytest.raises(ValueError, match="difere do valor original"):
        run._validar_e_persistir_config(tmp_path, _args(**mudanca))


def test_progress_roundtrip_ignores_corrupt_lines(tmp_path):
    p = tmp_path / "progress.jsonl"
    run._append_progresso(p, {"task_id": "BigCodeBench/1", "passed": True})
    with p.open("a", encoding="utf-8") as fh:
        fh.write("{linha truncada\n")
    assert list(run._carregar_progresso(p)) == ["BigCodeBench/1"]


def test_persist_report_has_three_metrics_and_comparison(tmp_path):
    relatorio = {
        "generated_at": "t",
        "model": "m",
        "dataset_version": "v0.1.4",
        "seed": 42,
        "num_problems": 2,
        "pass_at_k": {"pass@1": 0.5},
        "failures": {
            "total_failures": 1,
            "by_category": {"missing_dependency": 1},
            "by_group": {"library": 1, "logic": 0, "other": 0},
        },
        "usage_metrics": {
            "total_llm_interactions": 3,
            "total_prompt_tokens": 10,
            "total_completion_tokens": 5,
            "total_tokens": 15,
            "total_duration_s": 1.0,
        },
        "sandbox": {"image": "img", "network": "none"},
        "baseline_comparison": {
            "humaneval_pass_at_1": 0.9,
            "bigcodebench_pass_at_1": 0.5,
            "delta_pp": -40.0,
            "relative_drop_pct": 44.4,
            "humaneval_model": "m",
            "humaneval_num_problems": 50,
        },
        "problems": [
            {
                "task_id": "BigCodeBench/1",
                "libs": ["numpy"],
                "passed": True,
                "category": "passed",
            },
            {
                "task_id": "BigCodeBench/2",
                "libs": [],
                "passed": False,
                "category": "missing_dependency",
            },
        ],
    }
    _, md = run._persistir_relatorio(relatorio, tmp_path)
    texto = md.read_text(encoding="utf-8")
    assert "## 1. Pass@1" in texto
    assert "## 2. Falhas por import/dependência" in texto
    assert "## 3. Comparação com o HumanEval" in texto
    assert "-40.0 p.p." in texto
    assert (tmp_path / "report.json").is_file()
