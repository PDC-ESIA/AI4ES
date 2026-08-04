#!/usr/bin/env python3
"""Orquestrador do benchmark HumanEval sobre o workflow agêntico.

Carrega o dataset HumanEval (164 problemas), alimenta cada problema no
workflow_humaneval (LoopAgent[coder <-> executor]) e coleta métricas Pass@1.

Uso:
    pip install datasets
    python scripts/run_humaneval.py [--n-problems 10] [--output results.json]
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

# Adiciona raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datasets import load_dataset
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.genai import types

from shared.workspace import init_workspace, get_agent_workspace
from src.agents.workflow_humaneval import root_agent

logger = logging.getLogger(__name__)


def _preparar_workspace(item: dict, first_run: bool = False) -> str:
    """Inicializa workspace e injeta task JSON + arquivo de teste.

    Args:
        item: Item do dataset HumanEval.
        first_run: Se True, reinicializa o workspace completo. Se False,
            limpa apenas o workspace do coder (preservando reports anteriores).

    Returns:
        task_id normalizado (sem "/").
    """
    if first_run:
        init_workspace()
    else:
        # Limpa apenas o workspace do coder (solution.py anterior + test antigo)
        coder_ws = get_agent_workspace("he_coder")
        for f in coder_ws.iterdir():
            if f.is_file():
                f.unlink()

    task_id = item["task_id"].replace("/", "_")  # "HumanEval/0" -> "HumanEval_0"
    prompt = item["prompt"]
    test_code = item["test"]
    entry_point = item["entry_point"]

    # Injeta task JSON para o harness
    tasks_ws = get_agent_workspace("he_tasks")
    task_json = {
        "task_id": task_id,
        "description": f"Implement function: {entry_point}",
        "acceptance_criteria": [
            f"All unit tests pass for function '{entry_point}'",
        ],
    }
    (tasks_ws / f"{task_id}.json").write_text(
        json.dumps(task_json, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Injeta arquivo de teste no workspace do coder.
    # O teste inclui o prompt completo (helpers + stub do entry_point), depois
    # sobrescreve o entry_point importando de solution.py. Isso garante que
    # funções auxiliares (poly, encode_cyclic, etc.) estejam disponíveis no
    # escopo do teste.
    coder_ws = get_agent_workspace("he_coder")
    test_content = (
        f"# Auto-generated test file for HumanEval benchmark\n"
        f"# Task: {item['task_id']}\n\n"
        f"# --- Prompt (helpers + stub) ---\n"
        f"{prompt}\n"
        f"    pass  # stub - will be overridden by import below\n\n\n"
        f"# Override entry_point with actual implementation from coder\n"
        f"from solution import {entry_point}  # noqa: E402\n\n\n"
        f"{test_code}\n\n"
        f"def test_{entry_point}():\n"
        f"    check({entry_point})\n"
    )
    (coder_ws / f"test_{task_id}.py").write_text(
        test_content, encoding="utf-8",
    )

    return task_id


async def _executar_problema(item: dict, first_run: bool = False) -> dict:
    """Executa um problema HumanEval no pipeline agêntico.

    Returns:
        dict com task_id, passed, iterations, duration_seconds, error.
    """
    task_id = _preparar_workspace(item, first_run=first_run)
    t0 = time.time()

    try:
        runner = Runner(
            app_name="humaneval_bench",
            agent=root_agent,
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        session = await runner.session_service.create_session(
            app_name="humaneval_bench",
            user_id="benchmark",
            state={"task_id": task_id},
        )

        prompt_text = (
            f"Implement the following Python function.\n\n"
            f"```python\n{item['prompt']}\n```\n\n"
            f"Task ID: {task_id}"
        )
        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt_text)],
        )

        last_text = ""
        async for event in runner.run_async(
            user_id="benchmark",
            session_id=session.id,
            new_message=message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        last_text = part.text

        await runner.close()

        # Determinar pass/fail: verificar se o harness reportou sucesso nos testes
        exec_ws = get_agent_workspace("he_executor")
        report_path = exec_ws / f"{task_id}.report.json"
        passed = False
        iterations = 1

        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            iterations = report.get("iteration", 1)
            for stage in report.get("stages", []):
                if stage.get("stage") == "testes_automatizados":
                    passed = stage.get("status") == "sucesso"
                    break

        return {
            "task_id": item["task_id"],
            "passed": passed,
            "iterations": iterations,
            "duration_seconds": round(time.time() - t0, 2),
            "error": None,
        }

    except Exception as e:
        logger.exception(f"Erro ao executar {item['task_id']}")
        return {
            "task_id": item["task_id"],
            "passed": False,
            "iterations": 0,
            "duration_seconds": round(time.time() - t0, 2),
            "error": str(e),
        }


async def run_benchmark(n_problems: int = 164, output_file: str = "humaneval_results.json"):
    """Executa o benchmark HumanEval completo."""
    print("Carregando dataset HumanEval...")
    dataset = load_dataset("openai/openai_humaneval", split="test")
    total = min(n_problems, len(dataset))
    print(f"Executando {total} problemas...\n")

    results = []
    for i, item in enumerate(dataset):
        if i >= total:
            break

        result = await _executar_problema(item, first_run=(i == 0))
        results.append(result)

        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"[{i+1:3d}/{total}] {result['task_id']:20s} "
            f"{status:4s}  "
            f"({result['iterations']} iter, {result['duration_seconds']}s)"
            f"{('  ERROR: ' + result['error']) if result['error'] else ''}"
        )

    # Métricas agregadas
    total_pass = sum(1 for r in results if r["passed"])
    total_fail = sum(1 for r in results if not r["passed"])
    avg_iter = (
        sum(r["iterations"] for r in results) / len(results)
        if results else 0
    )
    avg_duration = (
        sum(r["duration_seconds"] for r in results) / len(results)
        if results else 0
    )

    summary = {
        "benchmark": "HumanEval",
        "total_problems": len(results),
        "passed": total_pass,
        "failed": total_fail,
        "pass_at_1": round(total_pass / len(results), 4) if results else 0,
        "avg_iterations": round(avg_iter, 2),
        "avg_duration_seconds": round(avg_duration, 2),
        "results": results,
    }

    print(f"\n{'='*60}")
    print(f"  HumanEval Benchmark Results")
    print(f"{'='*60}")
    print(f"  Total:      {len(results)}")
    print(f"  Passed:     {total_pass}")
    print(f"  Failed:     {total_fail}")
    print(f"  Pass@1:     {summary['pass_at_1']*100:.1f}%")
    print(f"  Avg iters:  {summary['avg_iterations']}")
    print(f"  Avg time:   {summary['avg_duration_seconds']}s")
    print(f"{'='*60}")

    Path(output_file).write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nResultados salvos em: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="HumanEval Benchmark Runner")
    parser.add_argument(
        "--n-problems", type=int, default=164,
        help="Numero de problemas a executar (default: 164 = todos)",
    )
    parser.add_argument(
        "--output", type=str, default="humaneval_results.json",
        help="Arquivo de saida com resultados (default: humaneval_results.json)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Habilita logging detalhado",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    asyncio.run(run_benchmark(
        n_problems=args.n_problems,
        output_file=args.output,
    ))


if __name__ == "__main__":
    main()
