"""Download e normalização dos datasets do piloto da Fase 3 (benchmark QA).

Baixa os 5 datasets definidos no Protocolo de Avaliação (seção 4.4) e os
normaliza para um esquema unificado JSONL em benchmark/datasets/normalized/.

Datasets e fontes (verificados em 21/08/2026):
  - nq_open          google-research-datasets/nq_open  (split validation, parquet API)
  - squad_v2         rajpurkar/squad_v2               (split validation, parquet API)
  - hotpot_qa        hotpotqa/hotpot_qa distractor    (split validation, parquet API)
  - longbench_qasper zai-org/LongBench data.zip       (subtask qasper/validation.jsonl)
  - gaia_l1          gaia-benchmark/GAIA              (2023/validation/metadata.level1.parquet,
                                                      apenas itens text-only)

Autenticação: HF_TOKEN carregado de benchmark/.env (necessário para o GAIA, gated).

Rastreabilidade: cada execução grava/atualiza benchmark/datasets/manifest.json com
repo, revisão (sha), URLs, data do download e contagens — conforme §6 do protocolo.

Uso:
    python download_datasets.py [--only nq_open,squad_v2] [--force]
"""

import argparse
import io
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
BENCH_DIR = ROOT / "benchmark"
DATASETS_DIR = BENCH_DIR / "datasets"
RAW_DIR = DATASETS_DIR / "raw"
NORM_DIR = DATASETS_DIR / "normalized"
MANIFEST_PATH = DATASETS_DIR / "manifest.json"

load_dotenv(BENCH_DIR / ".env")

HF = "https://huggingface.co"


def hf_headers() -> dict:
    import os

    token = os.environ.get("HF_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def http_get(url: str, timeout: int = 120) -> requests.Response:
    resp = requests.get(url, headers=hf_headers(), timeout=timeout)
    resp.raise_for_status()
    return resp


def repo_revision(repo: str) -> str:
    info = http_get(f"{HF}/api/datasets/{repo}", timeout=30).json()
    return info.get("sha", "desconhecida")


def parquet_shards(repo: str, config: str, split: str) -> list[str]:
    url = f"{HF}/api/datasets/{repo}/parquet/{config}/{split}"
    shards = http_get(url, timeout=30).json()
    if not isinstance(shards, list) or not shards:
        raise RuntimeError(f"Nenhum shard parquet em {url}")
    return shards


def read_parquet_rows(url: str) -> list[dict]:
    buf = io.BytesIO(http_get(url).content)
    return pq.read_table(buf).to_pylist()


def write_normalized(name: str, rows: list[dict]) -> Path:
    NORM_DIR.mkdir(parents=True, exist_ok=True)
    out = NORM_DIR / f"{name}.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return out


# ---------------------------------------------------------------------------
# Normalizadores por dataset
# ---------------------------------------------------------------------------

def norm_nq_open() -> tuple[list[dict], dict]:
    repo = "google-research-datasets/nq_open"
    rev = repo_revision(repo)
    rows_raw = []
    for shard in parquet_shards(repo, "nq_open", "validation"):
        rows_raw.extend(read_parquet_rows(shard))
    rows = [
        {
            "id": f"nq_open-{i}",
            "benchmark": "nq_open",
            "question": r["question"],
            "context": None,
            "gold_answers": list(r["answer"]),
            "answerable": True,
            "supporting_facts": None,
            "meta": {},
        }
        for i, r in enumerate(rows_raw)
    ]
    src = {"hf_repo": repo, "revision": rev, "config_split": "nq_open/validation",
           "urls": [f"{HF}/datasets/{repo}"]}
    return rows, {"raw": len(rows_raw), "normalized": len(rows), **src}


def norm_squad_v2() -> tuple[list[dict], dict]:
    repo = "rajpurkar/squad_v2"
    rev = repo_revision(repo)
    rows_raw = []
    for shard in parquet_shards(repo, "squad_v2", "validation"):
        rows_raw.extend(read_parquet_rows(shard))
    rows = []
    for i, r in enumerate(rows_raw):
        answers = [t for t in (r["answers"] or {}).get("text", []) if t]
        rows.append({
            "id": f"squad_v2-{r.get('id', i)}",
            "benchmark": "squad_v2",
            "question": r["question"],
            "context": r["context"],
            "gold_answers": answers,
            "answerable": bool(answers),
            "supporting_facts": None,
            "meta": {"title": r.get("title", "")},
        })
    src = {"hf_repo": repo, "revision": rev, "config_split": "squad_v2/validation",
           "urls": [f"{HF}/datasets/{repo}"]}
    return rows, {"raw": len(rows_raw), "normalized": len(rows), **src}


def norm_hotpot_qa() -> tuple[list[dict], dict]:
    repo = "hotpotqa/hotpot_qa"
    rev = repo_revision(repo)
    rows_raw = []
    for shard in parquet_shards(repo, "distractor", "validation"):
        rows_raw.extend(read_parquet_rows(shard))
    rows = []
    for i, r in enumerate(rows_raw):
        titles = r["context"]["title"]
        sents = r["context"]["sentences"]
        paragraphs = "\n".join(
            f"{t}: {''.join(s)}".strip() for t, s in zip(titles, sents)
        )
        sf = list(zip(r["supporting_facts"]["title"], r["supporting_facts"]["sent_id"]))
        rows.append({
            "id": f"hotpot_qa-{r.get('id', i)}",
            "benchmark": "hotpot_qa",
            "question": r["question"],
            "context": paragraphs,
            "gold_answers": [r["answer"]] if r["answer"] else [],
            "answerable": True,
            "supporting_facts": [[t, int(s)] for t, s in sf],
            "meta": {"type": r.get("type"), "level": r.get("level")},
        })
    src = {"hf_repo": repo, "revision": rev, "config_split": "distractor/validation",
           "urls": [f"{HF}/datasets/{repo}"]}
    return rows, {"raw": len(rows_raw), "normalized": len(rows), **src}


def norm_longbench_qasper() -> tuple[list[dict], dict]:
    repo = "zai-org/LongBench"
    rev = repo_revision(repo)
    zip_url = f"{HF}/datasets/{repo}/resolve/main/data.zip"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    local_zip = RAW_DIR / "longbench_data.zip"
    if not local_zip.exists():
        local_zip.write_bytes(http_get(zip_url).content)
    rows = []
    with zipfile.ZipFile(local_zip) as zf:
        member = "data/qasper.jsonl"
        with zf.open(member) as f:
            for i, line in enumerate(io.TextIOWrapper(f, encoding="utf-8")):
                if not line.strip():
                    continue
                r = json.loads(line)
                answers = json.loads(r["answers"]) if isinstance(r["answers"], str) else r["answers"]
                answers = [a for a in answers if a]
                rows.append({
                    "id": f"longbench_qasper-{i}",
                    "benchmark": "longbench_qasper",
                    "question": r["input"],
                    "context": r["context"],
                    "gold_answers": answers,
                    "answerable": True,
                    "supporting_facts": None,
                    "meta": {"length_words": r.get("length")},
                })
    src = {"hf_repo": repo, "revision": rev,            "config_split": "data.zip::data/qasper.jsonl",
           "urls": [zip_url]}
    return rows, {"raw": len(rows), "normalized": len(rows), **src}


def norm_gaia_l1() -> tuple[list[dict], dict]:
    repo = "gaia-benchmark/GAIA"
    rev = repo_revision(repo)
    url = f"{HF}/datasets/{repo}/resolve/main/2023/validation/metadata.level1.parquet"
    rows_raw = read_parquet_rows(url)
    rows, descartados_multimodal = [], 0
    for r in rows_raw:
        if r.get("file_name"):
            descartados_multimodal += 1
            continue
        final = (r.get("Final answer") or "").strip()
        rows.append({
            "id": f"gaia_l1-{r['task_id']}",
            "benchmark": "gaia_l1",
            "question": r["Question"],
            "context": None,
            "gold_answers": [final] if final else [],
            "answerable": True,
            "supporting_facts": None,
            "meta": {"level": r.get("Level")},
        })
    src = {"hf_repo": repo, "revision": rev,
           "config_split": "2023/validation/metadata.level1.parquet (text-only)",
           "urls": [url],
           "descartados_multimodal": descartados_multimodal}
    return rows, {"raw": len(rows_raw), "normalized": len(rows), **src}


NORMALIZERS = {
    "nq_open": norm_nq_open,
    "squad_v2": norm_squad_v2,
    "hotpot_qa": norm_hotpot_qa,
    "longbench_qasper": norm_longbench_qasper,
    "gaia_l1": norm_gaia_l1,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", default="", help="nomes separados por vírgula")
    parser.add_argument("--force", action="store_true", help="rebaixa mesmo se já normalizado")
    args = parser.parse_args()

    only = {s.strip() for s in args.only.split(",") if s.strip()}
    targets = [n for n in NORMALIZERS if not only or n in only]

    manifest = {}
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    falhas = []
    for name in targets:
        entry_previa = manifest.get(name, {})
        if entry_previa.get("normalized_file_exists") and not args.force:
            print(f"[{name}] já normalizado (use --force para rebaixar); pulando.")
            continue
        print(f"[{name}] baixando e normalizando...")
        try:
            rows, meta = NORMALIZERS[name]()
            out = write_normalized(name, rows)
            meta.update({
                "normalized_file": str(out.relative_to(ROOT)),
                "normalized_file_exists": True,
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
            })
            manifest[name] = meta
            extra = f" | multimodal descartado: {meta.get('descartados_multimodal', 0)}" if "descartados_multimodal" in meta else ""
            print(f"[{name}] OK: {meta['normalized']} casos "
                  f"(rev {meta['revision'][:10]}){extra}")
        except Exception as exc:  # noqa: BLE001 — registro explícito de falha por dataset
            falhas.append((name, str(exc)))
            print(f"[{name}] FALHOU: {exc}")

    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nmanifest: {MANIFEST_PATH}")
    if falhas:
        print("FALHAS:", ", ".join(n for n, _ in falhas))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
