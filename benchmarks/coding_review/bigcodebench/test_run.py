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
        lean=False,
        shard=None,
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
    "mudanca",
    [
        {"model": "outro"},
        {"seed": 1},
        {"limit": 10},
        {"timeout": 5},
        {"lean": True},
        {"shard": (0, 8)},
    ],
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


def test_parse_args_lean_flag():
    assert run._parse_args(["--model", "m"]).lean is False
    assert run._parse_args(["--model", "m", "--lean"]).lean is True


def test_run_name_lean():
    nome = run._construir_nome_run("gpt-4", 50, "20261008_120000", lean=True)
    assert nome == "run_20261008_120000_gpt-4_n50_lean"


def test_resume_old_metadata_without_lean_is_complete_mode(tmp_path):
    """metadata.json gravado antes do --lean equivale ao modo completo."""
    run._validar_e_persistir_config(tmp_path, _args())
    meta = tmp_path / "metadata.json"
    salvos = json.loads(meta.read_text(encoding="utf-8"))
    del salvos["lean"]
    meta.write_text(json.dumps(salvos), encoding="utf-8")
    run._validar_e_persistir_config(tmp_path, _args())
    with pytest.raises(ValueError, match="'lean'"):
        run._validar_e_persistir_config(tmp_path, _args(lean=True))


def test_agregar_uso_soma_cache_e_raciocinio():
    resultados = [
        {
            "llm_interactions": 2,
            "prompt_tokens": 1000,
            "completion_tokens": 100,
            "cached_tokens": 800,
            "reasoning_tokens": 40,
        },
        # Tarefa gravada antes da coleta de cache/raciocínio.
        {"llm_interactions": 1, "prompt_tokens": 1000, "completion_tokens": 50},
    ]
    assert run._agregar_uso(resultados) == {
        "total_llm_interactions": 3,
        "total_prompt_tokens": 2000,
        "total_completion_tokens": 150,
        "total_tokens": 2150,
        "total_cached_tokens": 800,
        "total_reasoning_tokens": 40,
        "cache_hit_ratio": 0.4,
    }


def test_agregar_uso_vazio():
    assert run._agregar_uso([])["cache_hit_ratio"] == 0.0


@pytest.mark.parametrize("valor", ["0/8", "7/8", "0/1"])
def test_parse_shard_valid(valor):
    i, n = (int(x) for x in valor.split("/"))
    assert run._parse_args(["--model", "m", "--shard", valor]).shard == (i, n)


@pytest.mark.parametrize("valor", ["8/8", "-1/8", "0/0", "a/b", "3"])
def test_parse_shard_invalid(valor):
    with pytest.raises(SystemExit):
        run._parse_args(["--model", "m", "--shard", valor])


def test_shards_are_disjoint_and_cover_everything():
    tarefas = list(range(1140))
    fatias = [run._aplicar_shard(tarefas, (i, 8)) for i in range(8)]
    assert sorted(t for f in fatias for t in f) == tarefas
    assert {len(f) for f in fatias} == {142, 143}
    assert run._aplicar_shard(tarefas, None) is tarefas


def test_run_name_shard_avoids_collisions():
    nomes = {
        run._construir_nome_run("m", 1140, "20261008_120000", lean=True, shard=(i, 8))
        for i in range(8)
    }
    assert len(nomes) == 8
    assert "run_20261008_120000_m_n1140_lean_shard3of8" in nomes


def _res(task_id, category, passed=False):
    return {"task_id": task_id, "category": category, "passed": passed, "libs": []}


def test_infra_failures_are_pending_not_failures():
    rel = run.montar_relatorio(
        [
            _res("BigCodeBench/1", "passed", passed=True),
            _res("BigCodeBench/2", "logic"),
            _res("BigCodeBench/3", "sandbox_error"),
            _res("BigCodeBench/4", "generation_error"),
        ],
        num_problems=4,
        model="m",
        seed=42,
        lean=False,
        image="img",
        allow_network=False,
    )
    assert rel["num_graded"] == 2
    assert rel["pass_at_k"]["pass@1"] == 0.5
    assert rel["failures"]["total_failures"] == 1
    assert [p["task_id"] for p in rel["pending"]] == [
        "BigCodeBench/3",
        "BigCodeBench/4",
    ]
    assert [p["task_id"] for p in rel["problems"]] == [
        "BigCodeBench/1",
        "BigCodeBench/2",
    ]


def test_report_md_warns_about_pending(tmp_path):
    rel = run.montar_relatorio(
        [
            _res("BigCodeBench/1", "passed", passed=True),
            _res("BigCodeBench/2", "sandbox_error"),
        ],
        num_problems=2,
        model="m",
        seed=42,
        lean=False,
        image="img",
        allow_network=False,
    )
    rel["usage_metrics"]["total_duration_s"] = 1.0
    _, md = run._persistir_relatorio(rel, tmp_path)
    texto = md.read_text(encoding="utf-8")
    assert "Resultado parcial" in texto and "BigCodeBench/2" in texto
    assert "1/1 tarefas aprovadas" in texto


def test_executar_retries_infra_failures_on_resume(tmp_path, monkeypatch):
    """Falha de LLM/Docker não vai para o checkpoint; o resume refaz só ela."""
    import asyncio

    from benchmarks.coding_review.bigcodebench import (
        coder_runner,
        dataset,
        grading,
        sandbox_image,
    )
    from benchmarks.coding_review.bigcodebench.coder_runner import CoderGeneration

    problemas = [
        dataset.BigCodeBenchProblem(f"BigCodeBench/{i}", "p", "task_func", "t")
        for i in range(4)
    ]
    monkeypatch.setattr(dataset, "load_problems", lambda *a, **kw: problemas)
    monkeypatch.setattr(sandbox_image, "ensure_image", lambda tag, rebuild: tag)
    sol = tmp_path / "solution.py"
    sol.write_text("def task_func(): ...\n")
    chamadas: list[str] = []
    falhar = {"BigCodeBench/1"}  # LLM falha nesta tarefa na 1ª rodada
    docker_falha = {"BigCodeBench/2"}  # e o Docker, nesta

    async def fake_coder(problema, model=None, lean=False):
        chamadas.append(problema.task_id)
        erro = "RateLimitError: 429" if problema.task_id in falhar else None
        return CoderGeneration(problema.slug, tmp_path, sol, error=erro)

    def fake_grade(problema, *a, **kw):
        if problema.task_id in docker_falha:
            return grading.GradeResult(False, "sandbox_error", None, False, "", "", "x")
        return grading.GradeResult(True, "passed", 0, False, "", "")

    monkeypatch.setattr(coder_runner, "run_coder", fake_coder)
    monkeypatch.setattr(grading, "grade_solution", fake_grade)

    args = _args(
        limit=4,
        shard=None,
        dataset_path=tmp_path / "d.parquet",
        dataset_url="u",
        image=None,
        rebuild_image=False,
        verify_canonical=False,
        baseline=None,
    )
    rel = asyncio.run(run._executar(args, tmp_path, model="m"))
    assert rel["num_graded"] == 2
    assert {p["task_id"] for p in rel["pending"]} == {
        "BigCodeBench/1",
        "BigCodeBench/2",
    }
    assert set(run._carregar_progresso(tmp_path / "progress.jsonl")) == {
        "BigCodeBench/0",
        "BigCodeBench/3",
    }

    falhar.clear()
    docker_falha.clear()
    chamadas.clear()
    rel = asyncio.run(run._executar(args, tmp_path, model="m"))
    assert chamadas == ["BigCodeBench/1", "BigCodeBench/2"]  # só as pendentes
    assert rel["pending"] == [] and rel["num_graded"] == 4
    assert rel["pass_at_k"]["pass@1"] == 1.0
