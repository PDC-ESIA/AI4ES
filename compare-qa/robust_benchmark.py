#!/usr/bin/env python3
"""Benchmark pareado e repetido do TACO atual versus TACO + QA em loop."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import random
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for item in (HERE, ROOT, ROOT / "adk"):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from benchmarks.coding_review.humaneval import bootstrap  # noqa: E402
from compare_pipelines import (  # noqa: E402
    Qa,
    clean,
    configure,
    feedback,
    invoke,
    run_oracle,
    run_qa,
    validation_ok,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="github_copilot/gemini-3.7-flash")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--max-iterations", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--cases", nargs="*", default=[])
    parser.add_argument("--output", type=Path, default=HERE / "robust_results.json")
    return parser.parse_args()


def usage_clone(source: Any) -> Any:
    from shared.token_usage import TokenUsage

    return TokenUsage.from_dict(source.to_dict(), source.agents_dict())


def usage_metrics(usage: Any) -> dict[str, int]:
    stages = usage.to_dict()
    agents = usage.agents_dict()
    input_tokens = sum(value["input"] for value in stages.values())
    output_tokens = sum(value["output"] for value in stages.values())
    calls = sum(
        value["calls"]
        for stage_agents in agents.values()
        for value in stage_agents.values()
    )
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "llm_calls": calls,
    }


def copy_tree(source: Path, destination: Path, allowed_root: Path) -> None:
    clean(destination, allowed_root)
    if source.exists():
        shutil.copytree(source, destination, dirs_exist_ok=True)


def matched_source(match: dict[str, Any]) -> Path | None:
    return next((item.path for item in match.values() if item.path), None)


def public_counts(validation: dict[str, dict[str, Any]]) -> tuple[int, int]:
    passed = failed = 0
    for item in validation.values():
        if not item.get("syntax_ok"):
            failed += 1
        for example in item.get("examples_run", []):
            if example.get("passed"):
                passed += 1
            else:
                failed += 1
    return passed, failed


def qa_dict(qa: Qa | None) -> dict[str, Any]:
    if qa is None:
        return {
            "status": "not_run",
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "source_coverage": None,
            "errors": [],
        }
    return {
        "status": qa.status,
        "passed": qa.passed,
        "failed": qa.failed,
        "skipped": qa.skipped,
        "source_coverage": qa.source_coverage,
        "errors": qa.errors,
    }


async def initial_generation(
    case: dict[str, Any], model: str, workspace: Path, evidence_dir: Path
) -> tuple[Any, float, Path, str | None]:
    from shared.token_usage import TokenUsage
    from shared.workspace import get_agent_workspace
    from src.agents.workflow_coding_review.coder.agent import agent as coder
    from src.agents.workflow_taco.task_builder.agent import agent as task_builder

    for agent in (task_builder, coder):
        configure(agent, model)
    coder_workspace = get_agent_workspace("cr_coder")
    clean(coder_workspace, workspace)
    usage = TokenUsage()
    started = time.perf_counter()
    error = None
    raw = json.dumps(
        {key: value for key, value in case.items() if key != "_id"},
        ensure_ascii=False,
    )
    try:
        task = await invoke(task_builder, raw, usage, "paired_initial")
        await invoke(coder, task or raw, usage, "paired_initial")
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    latency = time.perf_counter() - started
    snapshot = evidence_dir / "initial_snapshot"
    copy_tree(coder_workspace, snapshot, evidence_dir)
    return usage, latency, snapshot, error


async def run_baseline(
    case: dict[str, Any], hidden: list[dict[str, str]], model: str, timeout: int,
    workspace: Path, snapshot: Path, evidence_dir: Path, initial_usage: Any,
    initial_latency: float,
) -> dict[str, Any]:
    from shared.workspace import get_agent_workspace
    from src.agents.workflow_taco.agent import _construir_input_composer
    from src.agents.workflow_taco.matching import match_files
    from src.agents.workflow_taco.result_composer.agent import agent as composer
    from src.agents.workflow_taco.validator import validate

    configure(composer, model)
    coder_workspace = get_agent_workspace("cr_coder")
    copy_tree(snapshot, coder_workspace, workspace)
    usage = usage_clone(initial_usage)
    started = time.perf_counter()
    error = None
    public = case["challenge"]["examples"]
    match = match_files(coder_workspace, case["variations"])
    validation = validate(match, public)
    source = matched_source(match)
    public_passed, public_failed = public_counts(validation)
    hidden_result = full_result = None
    try:
        await invoke(
            composer,
            _construir_input_composer(
                {key: value for key, value in case.items() if key != "_id"},
                match,
                validation,
            ),
            usage,
            "taco_current",
        )
        if source:
            hidden_result = run_oracle(source, hidden, timeout, workspace)
            full_result = run_oracle(source, public + hidden, timeout, workspace)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    copy_tree(coder_workspace, evidence_dir / "baseline_final", evidence_dir)
    metrics = usage_metrics(usage)
    return {
        "public_passed": public_passed,
        "public_failed": public_failed,
        "hidden_passed": hidden_result.passed if hidden_result else 0,
        "hidden_failed": hidden_result.failed if hidden_result else len(hidden),
        "coverage_percent": full_result.coverage if full_result else 0.0,
        "iterations": 1,
        "converged": validation_ok(validation),
        "qa": qa_dict(None),
        "latency_s": round(initial_latency + time.perf_counter() - started, 3),
        **metrics,
        "source_sha256": sha256_file(source) if source and source.is_file() else None,
        "error": error,
    }


async def run_loop(
    case: dict[str, Any], hidden: list[dict[str, str]], model: str, timeout: int,
    max_iterations: int, workspace: Path, snapshot: Path, evidence_dir: Path,
    initial_usage: Any, initial_latency: float,
) -> dict[str, Any]:
    from shared.workspace import get_agent_workspace
    from src.agents.workflow_coding_review.coder.agent import agent as coder
    from src.agents.workflow_taco.agent import _construir_input_composer
    from src.agents.workflow_taco.matching import match_files
    from src.agents.workflow_taco.result_composer.agent import agent as composer
    from src.agents.workflow_taco.task_builder.agent import agent as task_builder
    from src.agents.workflow_taco.validator import validate

    for agent in (task_builder, coder, composer):
        configure(agent, model)
    coder_workspace = get_agent_workspace("cr_coder")
    copy_tree(snapshot, coder_workspace, workspace)
    usage = usage_clone(initial_usage)
    started = time.perf_counter()
    error = None
    public = case["challenge"]["examples"]
    iterations: list[dict[str, Any]] = []
    qa: Qa | None = None
    match: dict[str, Any] = {}
    validation: dict[str, dict[str, Any]] = {}
    try:
        for index in range(1, max_iterations + 1):
            iteration_started = time.perf_counter()
            match = match_files(coder_workspace, case["variations"])
            validation = validate(match, public)
            source = matched_source(match)
            qa = run_qa(case, source, usage, workspace) if source else None
            from shared.workspace import get_agent_workspace as agent_workspace

            qa_workspace = agent_workspace("receive_requirements")
            copy_tree(
                qa_workspace,
                evidence_dir / "qa_iterations" / f"iteration_{index}",
                evidence_dir,
            )
            public_passed, public_failed = public_counts(validation)
            qa_ok = bool(
                qa and qa.status == "sucesso" and qa.passed > 0 and qa.failed == 0
            )
            converged = validation_ok(validation) and qa_ok
            iterations.append({
                "index": index,
                "public_passed": public_passed,
                "public_failed": public_failed,
                "qa": qa_dict(qa),
                "converged": converged,
                "duration_s": round(time.perf_counter() - iteration_started, 3),
            })
            if converged or index == max_iterations:
                break
            correction = f"""# FEEDBACK TACO + QA — iteração {index}
Leia a solução existente e faça a menor correção no código de produção para atender ao contrato.
Preserve o nome do arquivo e solve(data: str) -> str. Não crie nem altere testes.

Evidência:
{feedback(validation, qa)[-6000:]}
"""
            await invoke(coder, correction, usage, "taco_qa_loop")

        await invoke(
            composer,
            _construir_input_composer(
                {key: value for key, value in case.items() if key != "_id"},
                match,
                validation,
            ),
            usage,
            "taco_qa_loop",
        )
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    final_match = match_files(coder_workspace, case["variations"])
    final_validation = validate(final_match, public)
    source = matched_source(final_match)
    public_passed, public_failed = public_counts(final_validation)
    hidden_result = full_result = None
    if source:
        hidden_result = run_oracle(source, hidden, timeout, workspace)
        full_result = run_oracle(source, public + hidden, timeout, workspace)
    copy_tree(coder_workspace, evidence_dir / "loop_final", evidence_dir)
    metrics = usage_metrics(usage)
    return {
        "public_passed": public_passed,
        "public_failed": public_failed,
        "hidden_passed": hidden_result.passed if hidden_result else 0,
        "hidden_failed": hidden_result.failed if hidden_result else len(hidden),
        "coverage_percent": full_result.coverage if full_result else 0.0,
        "iterations": len(iterations),
        "converged": bool(iterations and iterations[-1]["converged"]),
        "qa": qa_dict(qa),
        "iteration_details": iterations,
        "latency_s": round(initial_latency + time.perf_counter() - started, 3),
        **metrics,
        "source_sha256": sha256_file(source) if source and source.is_file() else None,
        "error": error,
    }


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_paths(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    files: list[Path] = []
    for path in paths:
        files.extend(sorted(item for item in path.rglob("*") if item.is_file()) if path.is_dir() else [path])
    for path in sorted(file for file in files if file.is_file()):
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def environment_manifest(model: str) -> dict[str, Any]:
    packages = [
        "google-adk", "litellm", "pytest", "pytest-cov", "pytest-json-report",
        "coverage", "psycopg2-binary",
    ]
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except subprocess.CalledProcessError:
        head = "unknown"
    return {
        "python": sys.version.split()[0],
        "packages": {name: version(name) for name in packages},
        "model": model,
        "git_head": head,
        "benchmark_sha256": sha256_file(Path(__file__)),
        "inputs_sha256": hash_paths([HERE / "inputs", HERE / "hidden_oracle.json"]),
        "agents_sha256": hash_paths([
            ROOT / "adk/src/agents/workflow_taco",
            ROOT / "adk/src/agents/workflow_coding_review/coder",
            ROOT / "adk/src/agents/qa_agent/subagents/receive_requirements",
            ROOT / "adk/src/agents/qa_agent/subagents/unit_test_generator",
        ]),
        "lock_exception": (
            "uv.lock fixa litellm 1.85.0, que declara Python <3.14; o projeto exige "
            "Python >=3.14. Foi mantido google-adk 1.33.0 e usado litellm 1.105.0."
        ),
    }


def bootstrap_ci(values: list[float], *, samples: int = 10000) -> list[float] | None:
    if not values:
        return None
    rng = random.Random(42)
    means = sorted(
        statistics.fmean(rng.choice(values) for _ in values) for _ in range(samples)
    )
    return [round(means[int(samples * 0.025)], 3), round(means[int(samples * 0.975)], 3)]


def sign_test_p(better: int, worse: int) -> float | None:
    n = better + worse
    if not n:
        return None
    tail = sum(math.comb(n, k) for k in range(0, min(better, worse) + 1)) / (2**n)
    return round(min(1.0, 2 * tail), 6)


def summarize(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    baseline = [pair["baseline"] for pair in pairs]
    loop = [pair["qa_loop"] for pair in pairs]

    def side(items: list[dict[str, Any]]) -> dict[str, Any]:
        hidden_passed = sum(item["hidden_passed"] for item in items)
        hidden_failed = sum(item["hidden_failed"] for item in items)
        qa_passed = sum(item["qa"]["passed"] for item in items)
        qa_failed = sum(item["qa"]["failed"] for item in items)
        return {
            "runs": len(items),
            "runs_all_hidden_passed": sum(item["hidden_failed"] == 0 for item in items),
            "hidden_passed": hidden_passed,
            "hidden_failed": hidden_failed,
            "hidden_pass_rate": round(hidden_passed / (hidden_passed + hidden_failed), 4),
            "mean_coverage_percent": round(statistics.fmean(item["coverage_percent"] for item in items), 2),
            "mean_iterations": round(statistics.fmean(item["iterations"] for item in items), 2),
            "qa_passed": qa_passed,
            "qa_failed": qa_failed,
            "qa_pass_rate": round(qa_passed / (qa_passed + qa_failed), 4) if qa_passed + qa_failed else None,
            "total_tokens": sum(item["total_tokens"] for item in items),
            "mean_tokens": round(statistics.fmean(item["total_tokens"] for item in items), 1),
            "total_latency_s": round(sum(item["latency_s"] for item in items), 3),
            "mean_latency_s": round(statistics.fmean(item["latency_s"] for item in items), 3),
            "llm_calls": sum(item["llm_calls"] for item in items),
        }

    deltas = {
        "hidden_pass_rate_pp": [
            100 * (
                q["hidden_passed"] / (q["hidden_passed"] + q["hidden_failed"])
                - b["hidden_passed"] / (b["hidden_passed"] + b["hidden_failed"])
            ) for b, q in zip(baseline, loop)
        ],
        "coverage_pp": [q["coverage_percent"] - b["coverage_percent"] for b, q in zip(baseline, loop)],
        "tokens": [q["total_tokens"] - b["total_tokens"] for b, q in zip(baseline, loop)],
        "latency_s": [q["latency_s"] - b["latency_s"] for b, q in zip(baseline, loop)],
    }
    baseline_wins = loop_wins = 0
    for b, q in zip(baseline, loop):
        b_ok, q_ok = b["hidden_failed"] == 0, q["hidden_failed"] == 0
        baseline_wins += int(b_ok and not q_ok)
        loop_wins += int(q_ok and not b_ok)
    return {
        "baseline": side(baseline),
        "qa_loop": side(loop),
        "paired_delta": {
            name: {
                "mean": round(statistics.fmean(values), 3),
                "median": round(statistics.median(values), 3),
                "bootstrap_95_ci_mean": bootstrap_ci(values),
            } for name, values in deltas.items()
        },
        "discordant_runs": {
            "loop_only_passed_all_hidden": loop_wins,
            "baseline_only_passed_all_hidden": baseline_wins,
            "exact_sign_test_p": sign_test_p(loop_wins, baseline_wins),
        },
    }


def checkpoint(path: Path, payload: dict[str, Any]) -> None:
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


async def main() -> int:
    options = parse_args()
    if options.repetitions < 1 or options.max_iterations < 1:
        raise SystemExit("repetitions e max-iterations devem ser >= 1")
    workspace = HERE / "workspaces" / "robust_native"
    evidence = HERE / "workspaces" / "robust_evidence"
    bootstrap.prepare_environment(workspace, model=options.model)
    from shared.workspace import init_workspace

    init_workspace()
    hidden_by_case = json.loads((HERE / "hidden_oracle.json").read_text(encoding="utf-8"))
    paths = sorted((HERE / "inputs").glob("*.json"))
    if options.cases:
        paths = [path for path in paths if path.stem in set(options.cases)]
    cases = []
    for path in paths:
        case = json.loads(path.read_text(encoding="utf-8"))
        case["_id"] = path.stem
        if path.stem not in hidden_by_case:
            raise SystemExit(f"oráculo oculto ausente: {path.stem}")
        cases.append(case)
    payload: dict[str, Any] = {
        "generated_at": datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(),
        "status": "running",
        "configuration": {
            "model": options.model,
            "temperature": 0.0,
            "repetitions": options.repetitions,
            "max_iterations": options.max_iterations,
            "timeout_s": options.timeout,
            "case_ids": [case["_id"] for case in cases],
            "paired_design": "um snapshot inicial compartilhado pelos dois ramos em cada repetição",
            "hidden_oracle_cases_per_repetition": sum(len(hidden_by_case[c["_id"]]) for c in cases),
        },
        "environment": environment_manifest(options.model),
        "pairs": [],
    }
    checkpoint(options.output, payload)
    total = len(cases) * options.repetitions
    current = 0
    for repetition in range(1, options.repetitions + 1):
        for case in cases:
            current += 1
            pair_id = f"{case['_id']}-r{repetition}"
            print(f"[{current}/{total}] {pair_id}: geração inicial", flush=True)
            pair_evidence = evidence / pair_id
            pair_evidence.mkdir(parents=True, exist_ok=True)
            initial_usage, initial_latency, snapshot, initial_error = await initial_generation(
                case, options.model, workspace, pair_evidence
            )
            print(f"[{current}/{total}] {pair_id}: baseline", flush=True)
            baseline_result = await run_baseline(
                case, hidden_by_case[case["_id"]], options.model, options.timeout,
                workspace, snapshot, pair_evidence, initial_usage, initial_latency,
            )
            print(f"[{current}/{total}] {pair_id}: loop QA", flush=True)
            loop_result = await run_loop(
                case, hidden_by_case[case["_id"]], options.model, options.timeout,
                options.max_iterations, workspace, snapshot, pair_evidence,
                initial_usage, initial_latency,
            )
            pair = {
                "pair_id": pair_id,
                "case_id": case["_id"],
                "title": case["challenge"]["title"],
                "repetition": repetition,
                "initial_generation": {
                    **usage_metrics(initial_usage),
                    "latency_s": round(initial_latency, 3),
                    "error": initial_error,
                },
                "baseline": baseline_result,
                "qa_loop": loop_result,
            }
            payload["pairs"].append(pair)
            payload["summary"] = summarize(payload["pairs"])
            checkpoint(options.output, payload)
            print(
                f"  hidden {baseline_result['hidden_passed']}/{baseline_result['hidden_passed'] + baseline_result['hidden_failed']}"
                f" -> {loop_result['hidden_passed']}/{loop_result['hidden_passed'] + loop_result['hidden_failed']} | "
                f"cov {baseline_result['coverage_percent']:.1f}% -> {loop_result['coverage_percent']:.1f}% | "
                f"it={loop_result['iterations']} | tokens {baseline_result['total_tokens']} -> {loop_result['total_tokens']} | "
                f"lat {baseline_result['latency_s']:.1f}s -> {loop_result['latency_s']:.1f}s",
                flush=True,
            )
    payload["status"] = "complete"
    payload["completed_at"] = datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat()
    payload["summary"] = summarize(payload["pairs"])
    checkpoint(options.output, payload)
    print(f"Resultados: {options.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
