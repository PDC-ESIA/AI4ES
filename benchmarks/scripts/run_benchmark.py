"""Runner da rodada piloto da Fase 3.

Executa: modelo × benchmark × caso × repetição, chamando cada LLM via LiteLLM
com parâmetros idênticos (rodadas/<nome>/config.yaml) e gravando um registro JSONL por
chamada (Protocolo §11): resposta bruta, latência, tokens, custo e status.

Isolamento da produção: chama o LiteLLM diretamente (sem ADK/agente). Para
github_copilot replica os headers de IDE + X-Initiator=user usados em
adk/shared/llm.py (evita cota reduzida de "utility models").

Retomada: registros existentes com status ok/empty são pulados; falhas de API
(api_error/timeout) são reexecutadas — falhas de infra ficam separadas das
falhas de qualidade nas métricas (requisito antecipado da Fase 4).

Uso:
    python run_benchmark.py --rodada fase3-piloto [--dry-run] [--limit N] \
        [--models gemini/gemini-2.5-flash,...] [--benchmarks nq_open,...]
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import litellm
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from metrics import extract_answer  # noqa: E402

RODADAS_DIR = ROOT / "benchmarks" / "rodadas"

# Preços de referência para estimativa no --dry-run (USD por 1M tokens).
# Copilot está incluso na assinatura GitHub → custo marginal 0.
EST_PRICE_PER_MTOK = {
    "gemini": {"input": 0.30, "output": 2.50},
}


def copilot_extra_headers() -> dict:
    """Headers exigidos pela API do Copilot (réplica de adk/shared/llm.py)."""
    version = "0.26.7"
    return {
        "copilot-integration-id": "vscode-chat",
        "editor-version": "vscode/1.95.0",
        "editor-plugin-version": f"copilot-chat/{version}",
        "user-agent": f"GitHubCopilotChat/{version}",
        "openai-intent": "conversation-panel",
        "x-github-api-version": "2025-04-01",
        "x-vscode-user-agent-library-version": "electron-fetch",
        "X-Initiator": os.environ.get("GITHUB_COPILOT_X_INITIATOR", "user"),
    }


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def model_slug(model: str) -> str:
    return model.replace("/", "_").replace(".", "-")


def build_messages(benchmark: str, case: dict, prompts: dict) -> list[dict]:
    template = prompts[benchmark]["user"]
    text = (
        template.format(question=case["question"], context=case["context"] or "")
        .strip()
    )
    return [{"role": "user", "content": text}]


def rough_cost_usd(model: str, prompt_chars: int, max_tokens: int) -> float:
    family = model.split("/")[0].split("-")[0]
    price = EST_PRICE_PER_MTOK.get(family)
    if not price:
        return 0.0
    prompt_tok = prompt_chars / 4.0
    out_tok = min(max_tokens, 128)
    return (prompt_tok * price["input"] + out_tok * price["output"]) / 1e6


def effective_max_tokens(cfg: dict, model: str, benchmark: str) -> int:
    mt = cfg.get("max_tokens", {})
    return int(
        cfg.get("model_max_tokens", {}).get(model)
        or cfg.get("max_tokens", {}).get(benchmark)
        or mt.get("default", 256)
    )


def call_model(cfg: dict, model: str, messages: list[dict], benchmark: str = "") -> dict:
    """Uma chamada com tratamento próprio de rate-limit.

    Usa num_retries=0 no litellm (evita rajada de retries internos que agrava
    cota por minuto) e, em RateLimitError, espera o delay sugerido pela API
    ("Please retry in X s") antes de tentar de novo, até num_retries+1 vezes.
    """
    max_tentativas = int(cfg.get("num_retries", 2)) + 1
    t0_total = time.monotonic()
    ultimo_erro = None
    for _tentativa in range(max_tentativas):
        t0 = time.monotonic()
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": cfg["temperature"],
            "top_p": cfg["top_p"],
            "max_tokens": effective_max_tokens(cfg, model, benchmark),
            "timeout": cfg["timeout_s"],
            "num_retries": 0,
            "drop_params": True,
        }
        if model.startswith("github_copilot/"):
            kwargs["extra_headers"] = copilot_extra_headers() | {"x-request-id": str(uuid.uuid4())}
        try:
            resp = litellm.completion(**kwargs)
        except litellm.exceptions.RateLimitError as exc:
            latency = round(time.monotonic() - t0, 3)
            ultimo_erro = {
                "status": "rate_limited",
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
                "latency_s": latency,
            }
            import re as _re

            m = _re.search(r"retry in ([\d.]+)s", str(exc), _re.I)
            espera = min(float(m.group(1)) + 1.0, 90.0) if m else 30.0
            print(f"⏳ {model.split('/')[-1]}: cota atingida, aguardando {espera:.0f}s...", flush=True)
            time.sleep(espera)
            continue
        except Exception as exc:  # noqa: BLE001 — status detalhado abaixo
            latency = round(time.monotonic() - t0, 3)
            tipo = str(type(exc).__name__)
            status = "timeout" if "Timeout" in tipo or "timed out" in str(exc).lower() else "api_error"
            return {"status": status, "error_type": tipo, "error": str(exc)[:500], "latency_s": latency}
        latency = round(time.monotonic() - t0_total, 3)
        text = ""
        try:
            text = resp.choices[0].message.content or ""
        except Exception:  # noqa: BLE001
            pass
        usage = getattr(resp, "usage", None)
        cost = None
        try:
            cost = litellm.completion_cost(resp)
        except Exception:  # noqa: BLE001 — provider sem tabela de preço
            cost = None
        return {
            "status": "ok" if text.strip() else "empty",
            "raw_response": text,
            "extracted_answer": extract_answer(text),
            "finish_reason": getattr(resp.choices[0], "finish_reason", None),
            "provider_model": getattr(resp, "model", None),
            "system_fingerprint": getattr(resp, "system_fingerprint", None),
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "cost_usd": cost,
            "latency_s": latency,
        }
    return ultimo_erro or {"status": "api_error", "error_type": "Unknown", "error": "?", "latency_s": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rodada", default="fase3-piloto",
                        help="nome do diretório em benchmarks/rodadas/")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="máx. casos por benchmark")
    parser.add_argument("--models", default="", help="filtra modelos (vírgula)")
    parser.add_argument("--benchmarks", default="", help="filtra benchmarks (vírgula)")
    args = parser.parse_args()

    rodada_dir = RODADAS_DIR / args.rodada
    cfg = yaml.safe_load((rodada_dir / "config.yaml").read_text(encoding="utf-8"))
    prompts = yaml.safe_load((rodada_dir / "prompts.yaml").read_text(encoding="utf-8"))

    models = [m.strip() for m in args.models.split(",") if m.strip()] or cfg["models"]
    benchmarks = [b.strip() for b in args.benchmarks.split(",") if b.strip()] or \
        ["nq_open", "squad_v2", "hotpot_qa", "longbench_qasper", "gaia_l1"]

    subsets_dir = rodada_dir / "subsets"
    results_root = rodada_dir / "resultados"
    k = int(cfg["repetitions"])
    sleep_padrao = float(cfg.get("sleep_between_calls_s", 0.3))
    sleep_por_modelo = cfg.get("model_sleep_between_calls_s", {}) or {}

    # GOOGLE_API_KEY também atende o provider gemini no litellm
    if os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

    total_calls = 0
    estimativa_total = 0.0
    planos = []
    for model in models:
        for bench in benchmarks:
            subset_path = subsets_dir / f"{bench}_pilot.jsonl"
            cases = load_jsonl(subset_path)
            if args.limit:
                cases = cases[: args.limit]
            out_dir = results_root / model_slug(model) / bench
            out_dir.mkdir(parents=True, exist_ok=True)
            runs_file = out_dir / "runs.jsonl"

            done = set()
            if runs_file.exists():
                for rec in load_jsonl(runs_file):
                    if rec["status"] in ("ok", "empty"):
                        done.add((rec["case_id"], rec["repetition"]))
            pendentes = [
                (case, rep)
                for case in cases
                for rep in range(1, k + 1)
                if (case["id"], rep) not in done
            ]
            custo_bench = sum(
                rough_cost_usd(model, len(build_messages(bench, c, prompts)[0]["content"]),
                               cfg.get("max_tokens", {}).get("default", 256))
                for c, _ in pendentes
            )
            planos.append((model, bench, len(cases), len(done), len(pendentes), custo_bench, runs_file))
            total_calls += len(pendentes)
            estimativa_total += custo_bench

    print(f"\n=== PLANO: {total_calls} chamadas | estimativa grosseira de custo: US$ {estimativa_total:.4f}")
    for model, bench, nc, done, pend, cst, rf in planos:
        print(f"  {model:35s} {bench:18s} {pend:3d} a executar ({done}/{nc*k} já prontas) ~US${cst:.4f}")

    if args.dry_run:
        print("\n(dry-run — nada executado)")
        return 0

    litellm.drop_params = True
    for model, bench, _, _, _, _, runs_file in planos:
        sleep_s = float(sleep_por_modelo.get(model, sleep_padrao))
        cases = {c["id"]: c for c in load_jsonl(subsets_dir / f"{bench}_pilot.jsonl")}
        if args.limit:
            cases = dict(list(cases.items())[: args.limit])
        done = set()
        if runs_file.exists():
            for rec in load_jsonl(runs_file):
                if rec["status"] in ("ok", "empty"):
                    done.add((rec["case_id"], rec["repetition"]))

        with runs_file.open("a", encoding="utf-8") as fout:
            for cid, case in cases.items():
                messages = build_messages(bench, case, prompts)
                for rep in range(1, k + 1):
                    if (cid, rep) in done:
                        continue
                    record = {
                        "run_id": cfg["run_id"],
                        "ts_utc": datetime.now(timezone.utc).isoformat(),
                        "model": model,
                        "benchmark": bench,
                        "case_id": cid,
                        "repetition": rep,
                        "params": {
                            "temperature": cfg["temperature"], "top_p": cfg["top_p"],
                            "timeout_s": cfg["timeout_s"], "num_retries": cfg["num_retries"],
                        },
                    }
                    result = call_model(cfg, model, messages, bench)
                    record.update(result)
                    fout.write(json.dumps(record, ensure_ascii=False) + "\n")
                    fout.flush()
                    simbolo = {"ok": ".", "empty": "e"}.get(record["status"], record["status"][0].upper())
                    print(simbolo, end="", flush=True)
                    time.sleep(sleep_s)
        print(f"\n[{model} × {bench}] concluído → {runs_file.relative_to(ROOT)}")

    print("\nPiloto executado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
