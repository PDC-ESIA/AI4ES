"""Amostragem determinística dos subsets do piloto da Fase 3.

Gera os subconjuntos reduzidos (rodada piloto) a partir dos datasets
normalizados em benchmark/datasets/normalized/, com seed global fixa para
reprodutibilidade, e grava em benchmarks/rodadas/<nome-da-rodada>/subsets/.

Tamanhos definidos no plano (benchmark/plano-fase3-piloto.md):
  nq_open=20, squad_v2=20 (estratificado por answerable), hotpot_qa=20,
  longbench_qasper=10, gaia_l1=10.

Rastreabilidade: subsets/manifest.json da rodada registra seed, método,
proporções e o SHA-256 de cada arquivo gerado.

Uso:
    python sample_subsets.py --rodada fase3-piloto [--seed 42] [--sizes nq_open=20,...]
"""

import argparse
import hashlib
import json
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NORM_DIR = ROOT / "benchmark" / "datasets" / "normalized"
RODADAS_DIR = ROOT / "benchmarks" / "rodadas"

DEFAULT_SIZES = {
    "nq_open": 20,
    "squad_v2": 20,
    "hotpot_qa": 20,
    "longbench_qasper": 10,
    "gaia_l1": 10,
}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sample_uniform(rows: list[dict], n: int, rng: random.Random) -> list[dict]:
    return sorted(rng.sample(rows, n), key=lambda r: r["id"])


def sample_stratified_answerable(rows: list[dict], n: int, rng: random.Random) -> list[dict]:
    """Estratifica pela classe answerable preservando a proporção do split."""
    grupos = defaultdict(list)
    for r in rows:
        grupos[r["answerable"]].append(r)
    total = len(rows)
    escolhidos = []
    restante = n
    classes = sorted(grupos.keys(), key=lambda k: len(grupos[k]))
    for i, chave in enumerate(classes):
        proporcao = len(grupos[chave]) / total
        if i == len(classes) - 1:
            k = restante
        else:
            k = max(1, round(n * proporcao))
            restante -= k
        escolhidos.extend(sample_uniform(grupos[chave], min(k, len(grupos[chave])), rng))
    return sorted(escolhidos, key=lambda r: r["id"])[:n]

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rodada", default="fase3-piloto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sizes", default="", help="ex.: nq_open=30,squad_v2=20")
    args = parser.parse_args()

    sizes = dict(DEFAULT_SIZES)
    # tamanhos declarados no config.yaml da rodada (chave "subsets") têm precedência
    cfg_path = RODADAS_DIR / args.rodada / "config.yaml"
    if cfg_path.exists():
        import yaml

        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        sizes.update(cfg.get("subsets", {}) or {})
    for par in filter(None, args.sizes.split(",")):
        nome, valor = par.split("=")
        sizes[nome.strip()] = int(valor)

    out_dir = RODADAS_DIR / args.rodada / "subsets"
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    relatorio = {"rodada": args.rodada, "seed": args.seed,
                 "gerado_em": datetime.now(timezone.utc).isoformat(), "subsets": {}}

    for name, n in sizes.items():
        src = NORM_DIR / f"{name}.jsonl"
        rows = load_jsonl(src)
        if name == "squad_v2":
            amostra = sample_stratified_answerable(rows, n, rng)
            metodo = "estratificado por answerable (proporção do split preservada)"
        else:
            amostra = sample_uniform(rows, n, rng)
            metodo = "uniforme aleatório simples"
        out = out_dir / f"{name}_pilot.jsonl"
        write_jsonl(out, amostra)
        resp = {
            "arquivo": str(out.relative_to(ROOT)),
            "metodo": metodo,
            "populacao": len(rows),
            "amostra": len(amostra),
            "percentual_da_populacao": round(100 * len(amostra) / len(rows), 2),
            "sha256": sha256_file(out),
        }
        if name == "squad_v2":
            ans = sum(1 for r in amostra if r["answerable"])
            resp["answerable"] = ans
            resp["unanswerable"] = len(amostra) - ans
        relatorio["subsets"][name] = resp
        print(f"[{name}] {len(amostra)} de {len(rows)} ({resp['percentual_da_populacao']}%) — {metodo}")

    (out_dir / "manifest.json").write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nmanifest: {out_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
