"""Unit tests for merging parallel BigCodeBench shards."""

from __future__ import annotations

import json

import pytest

from benchmarks.coding_review.bigcodebench import merge, run
from benchmarks.coding_review.bigcodebench.dataset import BigCodeBenchProblem

_TAREFAS = [f"BigCodeBench/{i}" for i in range(6)]


def _meta(shard, **kw):
    base = dict(
        model="m",
        limit=6,
        seed=42,
        task_ids=None,
        timeout=120,
        dataset_version="v0.1.4",
        allow_network=False,
        lean=True,
        shard=shard,
    )
    base.update(kw)
    return base


def _shard(tmp_path, i, n, categorias: dict[str, str], **meta_kw):
    d = tmp_path / f"shard{i}"
    d.mkdir()
    (d / "metadata.json").write_text(json.dumps(_meta(f"{i}/{n}", **meta_kw)))
    for task_id, cat in categorias.items():
        run._append_progresso(
            d / "progress.jsonl",
            {
                "task_id": task_id,
                "category": cat,
                "passed": cat == "passed",
                "libs": [],
                "prompt_tokens": 100,
                "cached_tokens": 50,
            },
        )
    (d / "report.json").write_text(
        json.dumps(
            {
                "sandbox": {"image": "img"},
                "usage_metrics": {"total_duration_s": 10.0 * (i + 1)},
            }
        )
    )
    return d


@pytest.fixture(autouse=True)
def _dataset_fake(monkeypatch):
    problemas = [BigCodeBenchProblem(t, "p", "task_func", "t") for t in _TAREFAS]
    monkeypatch.setattr(
        "benchmarks.coding_review.bigcodebench.dataset.load_problems",
        lambda *a, **kw: problemas,
    )


def test_merge_complete_shards(tmp_path):
    d0 = _shard(
        tmp_path,
        0,
        2,
        {
            "BigCodeBench/0": "passed",
            "BigCodeBench/2": "logic",
            "BigCodeBench/4": "passed",
        },
    )
    d1 = _shard(
        tmp_path,
        1,
        2,
        {
            "BigCodeBench/1": "passed",
            "BigCodeBench/3": "passed",
            "BigCodeBench/5": "api_misuse",
        },
    )
    out, rel = merge.merge([d0, d1], output_dir=tmp_path / "merged")

    assert rel["num_problems"] == 6 and rel["num_graded"] == 6
    assert rel["pass_at_k"]["pass@1"] == round(4 / 6, 4)
    assert rel["pending"] == []
    assert [p["task_id"] for p in rel["problems"]] == _TAREFAS  # ordem do dataset
    assert rel["usage_metrics"]["total_prompt_tokens"] == 600
    assert rel["usage_metrics"]["cache_hit_ratio"] == 0.5
    assert rel["usage_metrics"]["total_duration_s"] == 20.0  # shard mais lento
    meta = json.loads((out / "metadata.json").read_text())
    assert meta["shard"] is None and meta["lean"] is True
    assert len((out / "progress.jsonl").read_text().splitlines()) == 6
    assert (out / "report.md").is_file()


def test_merge_marks_missing_and_infra_as_pending(tmp_path):
    d0 = _shard(
        tmp_path, 0, 2, {"BigCodeBench/0": "passed", "BigCodeBench/2": "sandbox_error"}
    )
    d1 = _shard(tmp_path, 1, 2, {"BigCodeBench/1": "logic"})
    out, rel = merge.merge([d0, d1], output_dir=tmp_path / "merged")

    pendentes = {p["task_id"]: p["category"] for p in rel["pending"]}
    assert pendentes == {
        # sandbox_error gravado por versão antiga: descartado, refeito no resume.
        "BigCodeBench/2": "not_run",
        "BigCodeBench/3": "not_run",
        "BigCodeBench/4": "not_run",
        "BigCodeBench/5": "not_run",
    }
    assert rel["num_graded"] == 2
    # Só o que foi avaliado vai para o checkpoint: o resume refaz os pendentes.
    assert len((out / "progress.jsonl").read_text().splitlines()) == 2


def test_merged_dir_is_resumable_without_shard(tmp_path):
    d0 = _shard(tmp_path, 0, 1, {"BigCodeBench/0": "passed"})
    out, _ = merge.merge([d0], output_dir=tmp_path / "merged")
    args = run._parse_args(["--model", "m", "--limit", "6", "--lean"])
    run._validar_e_persistir_config(out, args)  # não levanta


def test_merge_rejects_incomplete_set(tmp_path):
    d0 = _shard(tmp_path, 0, 3, {})
    d2 = _shard(tmp_path, 2, 3, {})
    with pytest.raises(ValueError, match="Esperados os shards 0..2"):
        merge.merge([d0, d2], output_dir=tmp_path / "merged")


def test_merge_rejects_mismatched_params(tmp_path):
    d0 = _shard(tmp_path, 0, 2, {})
    d1 = _shard(tmp_path, 1, 2, {}, lean=False)
    with pytest.raises(ValueError, match="'lean' difere"):
        merge.merge([d0, d1], output_dir=tmp_path / "merged")


def test_merge_refuses_non_empty_output(tmp_path):
    d0 = _shard(tmp_path, 0, 1, {})
    out = tmp_path / "merged"
    out.mkdir()
    (out / "x").write_text("")
    with pytest.raises(FileExistsError):
        merge.merge([d0], output_dir=out)
