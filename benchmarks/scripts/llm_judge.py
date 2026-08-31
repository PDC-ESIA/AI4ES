"""LLM-as-a-Judge para o Agente de QA (preparação Fase 4).

Avalia amostras de respostas abertas nos eixos:
  - Correctness (corretude factual)
  - Helpfulness (utilidade)
  - Coherence (coerência)
  - Completude (cobertura da pergunta)
  - Abstention adequada (saber dizer que não sabe)

O juiz deve ser um modelo forte e distinto do avaliado, conforme boas práticas
do protocolo (§8.6). Resultados são gravados em JSONL e podem ser agregados.

Uso:
    python llm_judge.py --rodada fase3-piloto \
        --judge github_copilot/gemini-3.1-pro-preview \
        --samples 50 \
        --output benchmarks/rodadas/fase3-piloto/resultados/judge_results.jsonl
"""

import argparse
import json
import os
import sys
import threading
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import litellm
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_benchmark import (  # noqa: E402
    TokenBucketRateLimiter,
    copilot_extra_headers,
    effective_max_tokens,
)

RODADAS_DIR = ROOT / "benchmarks" / "rodadas"

JUDGE_PROMPT = """You are an expert evaluator of Question Answering systems.
Rate the assistant's answer to the user's question using the rubric below.
Score each dimension from 1 to 5, where 1 = very poor, 3 = acceptable, 5 = excellent.

Dimensions:
1. Correctness: is the answer factually correct? (1-5)
2. Helpfulness: does the answer help the user solve their information need? (1-5)
3. Coherence: is the answer clear, well-formed and easy to understand? (1-5)
4. Completeness: does the answer cover all parts of the question? (1-5)
5. Abstention: if the question is unanswerable or outside the context, did the assistant appropriately refuse or say it doesn't know? (1-5; use N/A if not applicable)

Respond ONLY in JSON format. Do not write any explanation outside the JSON.

Example format (use exactly these keys):
{{
  "correctness": 4,
  "helpfulness": 4,
  "coherence": 5,
  "completeness": 3,
  "abstention": "N/A",
  "justification": "Brief justification here."
}}

Question:
{question}

{context_block}

Reference answer(s):
{gold}

Assistant answer:
{prediction}

JSON rating:"""



def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def model_slug(model: str) -> str:
    return model.replace("/", "_").replace(".", "-")


def call_judge(cfg: dict, judge: str, question: str, context: str, golds: list[str], prediction: str) -> dict:
    context_block = f"Context:\n{context}" if context else ""
    gold_text = "\n".join(f"- {g}" for g in golds) if golds else "(none)"
    prompt = JUDGE_PROMPT.format(
        question=question,
        context_block=context_block,
        gold=gold_text,
        prediction=prediction if prediction else "(empty response)",
    )
    kwargs = {
        "model": judge,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": effective_max_tokens(cfg, judge, ""),
        "timeout": cfg.get("timeout_s", 120),
        "drop_params": True,
    }
    if judge.startswith("github_copilot/"):
        kwargs["extra_headers"] = copilot_extra_headers() | {"x-request-id": str(uuid.uuid4())}

    t0 = time.monotonic()
    try:
        resp = litellm.completion(**kwargs)
        latency = round(time.monotonic() - t0, 3)
        text = resp.choices[0].message.content or ""
        # Extrai JSON
        try:
            # Tenta encontrar JSON entre chaves
            start = text.find("{")
            end = text.rfind("}")
            parsed = json.loads(text[start:end + 1]) if start != -1 and end != -1 else {}
        except json.JSONDecodeError:
            parsed = {}
        return {
            "status": "ok",
            "raw_response": text,
            "rating": parsed,
            "latency_s": latency,
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)[:500], "rating": {}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rodada", default="fase3-piloto")
    parser.add_argument("--judge", default="github_copilot/gemini-3.1-pro-preview")
    parser.add_argument("--samples", type=int, default=50, help="número de respostas a avaliar por benchmark")
    parser.add_argument("--output", default="", help="caminho do JSONL de saída")
    parser.add_argument("--benchmarks", default="", help="filtrar benchmarks, vírgula")
    parser.add_argument("--workers", type=int, default=0, help="workers paralelos (0 = usar config)")
    parser.add_argument("--rate", type=float, default=0.0, help="máx. chamadas/segundo do juiz (0 = usar config)")
    args = parser.parse_args()

    rodada_dir = RODADAS_DIR / args.rodada
    cfg = yaml.safe_load((rodada_dir / "config.yaml").read_text(encoding="utf-8"))
    subsets_dir = rodada_dir / "subsets"
    results_root = rodada_dir / "resultados"

    benchmarks = [b.strip() for b in args.benchmarks.split(",") if b.strip()] or \
        ["nq_open", "squad_v2", "hotpot_qa", "longbench_qasper", "gaia_l1"]

    out_path = Path(args.output) if args.output else results_root / "judge_results.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
    litellm.drop_params = True

    rng_seed = cfg.get("seed", 42)
    import random
    rng = random.Random(rng_seed)

    # Carrega amostras já julgadas para retomada
    already_done = set()
    if out_path.exists():
        for rec in load_jsonl(out_path):
            if rec.get("judge_status") == "ok":
                already_done.add((rec["benchmark"], rec["case_id"], rec["model"]))
        print(f"[retomada] {len(already_done)} avaliações já salvas em {out_path}")

    # Configurações de paralelismo
    max_workers = args.workers or int(cfg.get("judge_max_workers", 10))
    rate = args.rate or float(cfg.get("judge_max_calls_per_second", 5.0))
    rate_limiter = TokenBucketRateLimiter(rate)

    tasks = []
    for bench in benchmarks:
        subset_path = subsets_dir / f"{bench}_pilot.jsonl"
        if not subset_path.exists():
            print(f"[aviso] subset não encontrado: {subset_path}")
            continue
        cases = {c["id"]: c for c in load_jsonl(subset_path)}
        sampled_case_ids = rng.sample(sorted(cases.keys()), min(args.samples, len(cases)))

        for model_dir in sorted(p for p in results_root.iterdir() if p.is_dir() and p.name != "judge_results.jsonl"):
            runs_file = model_dir / bench / "runs.jsonl"
            if not runs_file.exists():
                continue
            finals = {}
            for rec in load_jsonl(runs_file):
                finals[(rec["case_id"], rec["repetition"])] = rec
            for case_id in sampled_case_ids:
                case = cases[case_id]
                rep = 1
                rec = finals.get((case_id, rep))
                if not rec:
                    continue
                model_name = rec.get("model", model_dir.name)
                if (bench, case_id, model_name) in already_done:
                    continue
                tasks.append((args.judge, bench, case_id, case, rec, model_name))

    print(f"\n=== PLANO: {len(tasks)} avaliações do juiz | workers={max_workers} | rate={rate}/s")

    def run_judge_task(task):
        judge, bench, case_id, case, rec, model_name = task
        rate_limiter.acquire()
        pred = rec.get("raw_response", "")
        result = call_judge(
            cfg, judge,
            case["question"],
            case.get("context", ""),
            [g for g in case.get("gold_answers", []) if g],
            pred,
        )
        return {
            "rodada": args.rodada,
            "judge": judge,
            "benchmark": bench,
            "case_id": case_id,
            "model": model_name,
            "prediction": pred,
            "gold_answers": case.get("gold_answers"),
            "rating": result.get("rating"),
            "judge_status": result["status"],
            "judge_latency_s": result.get("latency_s"),
            "judge_raw": result.get("raw_response", "") if result["status"] != "ok" else "",
        }, result["status"]

    completed = 0
    failed = 0
    skipped_existing = len(already_done)
    write_lock = threading.Lock()

    with out_path.open("a", encoding="utf-8") as fout, \
         ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {executor.submit(run_judge_task, task): task for task in tasks}
        for future in as_completed(future_to_task):
            try:
                record, status = future.result()
                with write_lock:
                    fout.write(json.dumps(record, ensure_ascii=False) + "\n")
                    fout.flush()
                completed += 1
                symbol = "." if status == "ok" else "E"
            except Exception as exc:  # noqa: BLE001
                failed += 1
                symbol = "X"
                _, bench, case_id, _, rec, model_name = future_to_task[future]
                error_record = {
                    "rodada": args.rodada,
                    "judge": args.judge,
                    "benchmark": bench,
                    "case_id": case_id,
                    "model": model_name,
                    "judge_status": "runner_error",
                    "judge_error": str(exc)[:500],
                }
                with write_lock:
                    fout.write(json.dumps(error_record, ensure_ascii=False) + "\n")
                    fout.flush()
            print(symbol, end="", flush=True)
            total_processed = skipped_existing + completed + failed
            if total_processed % 100 == 0:
                print(f" [{completed + failed}/{len(tasks)} novas | {skipped_existing} retomadas]", end="", flush=True)

    print(f"\n\nResultados do juiz salvos em: {out_path}")
    print(f"Retomadas: {skipped_existing} | Concluídas: {completed} | Falhas: {failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
