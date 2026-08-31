"""Agregação dos resultados da rodada piloto da Fase 3.

Lê os registros JSONL em benchmarks/rodadas/<rodada>/resultados/<modelo>/<benchmark>/runs.jsonl,
calcula as métricas do Protocolo (§9.4/§10) por modelo×benchmark e produz:

  - benchmarks/rodadas/<rodada>/resultados/summary.json  (dados completos)
  - benchmarks/rodadas/<rodada>/resultados/summary.md    (tabela comparativa legível)

Falhas de execução (api_error/timeout) são contadas separadamente das falhas
de qualidade do modelo — requisito da Fase 4 antecipado aqui.

Uso:
    python aggregate.py --rodada fase3-piloto
"""

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import aggregate_benchmark, case_metrics, latency_percentiles  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RODADAS_DIR = ROOT / "benchmarks" / "rodadas"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rodada", default="fase3-piloto")
    args = parser.parse_args()

    rodada_dir = RODADAS_DIR / args.rodada
    results_root = rodada_dir / "resultados"
    subsets_dir = rodada_dir / "subsets"
    if not results_root.exists():
        print(f"Nenhum resultado em {results_root}")
        return 1

    summary = {"rodada": args.rodada, "models": {}}

    for model_dir in sorted(p for p in results_root.iterdir() if p.is_dir()):
        model_name = model_dir.name.replace("_", "/") if "/" not in model_dir.name else model_dir.name
        # slug invertido: github_copilot_gpt-4-1-mini -> github_copilot/gpt-4.1-mini não é
        # recuperável unicamente; guardamos o nome real no primeiro registro.
        resumo_modelo = {}
        for bench_dir in sorted(p for p in model_dir.iterdir() if p.is_dir()):
            bench = bench_dir.name
            runs_file = bench_dir / "runs.jsonl"
            if not runs_file.exists():
                continue
            records = load_jsonl(runs_file)
            if not records:
                continue
            model_real = records[0]["model"]
            cases = {c["id"]: c for c in load_jsonl(subsets_dir / f"{bench}_pilot.jsonl")}

            # Deduplicação: reexecuções geram múltiplos registros por (caso, repetição);
            # a última ocorrência é o resultado final daquele par.
            finais = {}
            n_tentativas = len(records)
            for rec in records:
                finais[(rec["case_id"], rec["repetition"])] = rec
            records = list(finais.values())

            casos_resultados = defaultdict(list)
            status_counts = defaultdict(int)
            latencias, custos, tokens_out = [], [], []
            for rec in records:
                status_counts[rec["status"]] += 1
                if rec["status"] in ("api_error", "timeout", "rate_limited", "reasoning_truncated"):
                    continue
                case = cases.get(rec["case_id"])
                if case is None:
                    continue
                m = case_metrics(bench, rec.get("raw_response"), case)
                casos_resultados[rec["case_id"]].append(m)
                if rec["status"] == "ok":
                    latencias.append(rec["latency_s"])
                    if rec.get("cost_usd") is not None:
                        custos.append(rec["cost_usd"])
                    if rec.get("completion_tokens"):
                        tokens_out.append(rec["completion_tokens"])

            agg = aggregate_benchmark(bench, dict(casos_resultados))
            n_exec_ok = sum(v for k, v in status_counts.items() if k in ("ok", "empty"))
            if agg.get("answered_rate") is None and "n_unanswerable_cases" not in agg and n_exec_ok:
                answered = [
                    m["answered"]
                    for reps in casos_resultados.values()
                    for m in reps
                ]
                if answered and bench != "squad_v2":
                    agg["answered_rate"] = round(sum(answered) / len(answered), 4)

            resumo_modelo[bench] = {
                **agg,
                "execucoes": {
                    "total_registros_brutos": n_tentativas,
                    "pares_caso_repeticao": len(records),
                    **{f"n_{s}": c for s, c in sorted(status_counts.items())},
                },
                "latencia": latency_percentiles(latencias),
                "custo_total_usd": round(sum(custos), 6) if custos else 0.0,
                "custo_medio_por_chamada_usd": (
                    round(statistics.mean(custos), 8) if custos else 0.0
                ),
                "tokens_saida_media": (
                    round(statistics.mean(tokens_out), 1) if tokens_out else None
                ),
            }
            summary["models"].setdefault(model_real, {})[bench] = resumo_modelo[bench]

    out_json = results_root / "summary.json"
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    linhas_md = [
        f"# Resumo agregado — rodada {args.rodada}", "",
        f"Gerado a partir de `{out_json.relative_to(ROOT)}`.", "",
        "| Modelo | Benchmark | Casos | EM | F1 | pass^k | Recusa correta | FPA | Latência p50/p95 | Custo total |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for model, benches in summary["models"].items():
        for bench, r in benches.items():
            lat = r.get("latencia", {})
            linhas_md.append(
                f"| {model} | {bench} | {r['n_cases']} "
                f"| {r['EM_mean']:.3f} | {r['F1_mean']:.3f} | {r['pass_k_consistency']:.2f} "
                f"| {r.get('unanswerable_rate', '—')} | {r.get('false_positive_answering', '—')} "
                f"| {lat.get('p50_s', '—')}/{lat.get('p95_s', '—')}s "
                f"| US$ {r['custo_total_usd']:.4f} |"
            )
    out_md = results_root / "summary.md"
    out_md.write_text("\n".join(linhas_md) + "\n", encoding="utf-8")

    print("\n".join(linhas_md))
    print(f"\nOK: {out_json.relative_to(ROOT)}")
    print(f"OK: {out_md.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
