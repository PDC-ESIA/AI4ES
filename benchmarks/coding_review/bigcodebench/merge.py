"""Junta os shards de um run paralelo do BigCodeBench num relatório único.

Uso (a partir da raiz do repositório), após rodar os N shards com `--shard I/N`:

    python -m benchmarks.coding_review.bigcodebench.merge <dir_shard_0> … <dir_shard_N-1>

Valida que os diretórios formam um conjunto completo de shards (0..N-1) do mesmo
run (mesmos model/limit/seed/timeout/lean…), une os `progress.jsonl` e gera
`report.json`, `report.md`, `metadata.json` e `progress.jsonl` num diretório
novo. Tarefas sem resultado ficam como pendentes; o diretório gerado pode ser
retomado com `run --resume-dir` (sem `--shard`) para completá-las.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

# Permite executar como script ou como módulo (`python -m ...`).
if __package__ in (None, ""):
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from benchmarks.coding_review.bigcodebench import run as bcb_run
from benchmarks.coding_review.bigcodebench.categories import (
    NOT_RUN,
    PENDING_CATEGORIES,
)
from benchmarks.coding_review.bigcodebench.dataset import DEFAULT_DATASET_URL

# Parâmetros que precisam coincidir entre os shards (os mesmos do resume guard).
_CHAVES_COMUNS = (
    "model",
    "limit",
    "seed",
    "task_ids",
    "timeout",
    "dataset_version",
    "allow_network",
    "lean",
)


def _ler_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def validar_shards(metas: list[dict]) -> int:
    """Confere que `metas` são os shards 0..N-1 do mesmo run; devolve N."""
    if not metas:
        raise ValueError("Nenhum diretório de shard informado.")
    pares = []
    for m in metas:
        if not m.get("shard"):
            raise ValueError("Diretório sem `shard` no metadata.json (não é um shard).")
        pares.append(tuple(int(x) for x in m["shard"].split("/")))
    totais = {total for _, total in pares}
    if len(totais) != 1:
        raise ValueError(f"Shards de divisões diferentes: N = {sorted(totais)}.")
    total = totais.pop()
    indices = sorted(i for i, _ in pares)
    if indices != list(range(total)):
        raise ValueError(f"Esperados os shards 0..{total - 1}; recebidos {indices}.")
    for chave in _CHAVES_COMUNS:
        valores = {
            json.dumps(m.get(chave, False if chave == "lean" else None)) for m in metas
        }
        if len(valores) > 1:
            raise ValueError(
                f"Parâmetro '{chave}' difere entre os shards: {sorted(valores)}."
            )
    return total


def merge(
    shard_dirs: list[Path],
    *,
    output_dir: Path | None = None,
    dataset_path: Path = bcb_run._DEFAULT_DATASET,
    dataset_url: str = DEFAULT_DATASET_URL,
    baseline: Path | None = None,
) -> tuple[Path, dict]:
    """Une os shards e persiste o relatório consolidado; devolve (dir, relatório)."""
    from benchmarks.coding_review.bigcodebench.dataset import load_problems
    from benchmarks.coding_review.bigcodebench.sandbox_image import IMAGE_TAG

    metas = []
    for d in shard_dirs:
        meta = _ler_json(d / "metadata.json")
        if meta is None:
            raise FileNotFoundError(f"metadata.json ausente em {d}.")
        metas.append(meta)
    validar_shards(metas)
    base = metas[0]

    # A lista esperada vem do dataset com os parâmetros do run (antes do shard).
    problemas = load_problems(
        dataset_path,
        url=dataset_url,
        limit=base["limit"],
        seed=base["seed"],
        task_ids=base["task_ids"],
    )

    concluidos: dict[str, dict] = {}
    relatorios = []
    for d in shard_dirs:
        for task_id, detalhe in bcb_run._carregar_progresso(
            d / "progress.jsonl"
        ).items():
            if detalhe.get("category") not in PENDING_CATEGORIES:
                concluidos[task_id] = detalhe
        rel = _ler_json(d / "report.json")
        if rel is not None:
            relatorios.append(rel)

    resultados = [
        concluidos.get(
            p.task_id,
            {
                "task_id": p.task_id,
                "category": NOT_RUN,
                "reason": "Sem resultado nos shards.",
            },
        )
        for p in problemas
    ]

    imagens = {r.get("sandbox", {}).get("image") for r in relatorios} - {None}
    if len(imagens) > 1:
        raise ValueError(f"Shards avaliados com imagens diferentes: {sorted(imagens)}.")
    canonicas = [r["canonical_check"] for r in relatorios if r.get("canonical_check")]
    canonical_check = None
    if canonicas:
        canonical_check = {
            "checked": sum(c["checked"] for c in canonicas),
            "failed": {t: cat for c in canonicas for t, cat in c["failed"].items()},
        }

    relatorio = bcb_run.montar_relatorio(
        resultados,
        num_problems=len(problemas),
        model=base["model"],
        seed=base["seed"],
        lean=base.get("lean", False),
        image=imagens.pop() if imagens else IMAGE_TAG,
        allow_network=base["allow_network"],
        canonical_check=canonical_check,
        baseline_path=baseline,
    )
    relatorio["merged_from"] = [str(d) for d in shard_dirs]
    # Os shards rodam em paralelo: o tempo de parede é o do shard mais lento.
    relatorio["usage_metrics"]["total_duration_s"] = max(
        (r.get("usage_metrics", {}).get("total_duration_s", 0.0) for r in relatorios),
        default=0.0,
    )

    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome = bcb_run._construir_nome_run(
            base["model"], len(problemas), timestamp, lean=base.get("lean", False)
        )
        output_dir = shard_dirs[0].parent / f"{nome}_merged"
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Diretório de saída não está vazio: {output_dir}.")
    output_dir.mkdir(parents=True, exist_ok=True)

    # metadata/progress compatíveis com `run --resume-dir` (sem shard).
    meta_merged = {chave: base.get(chave) for chave in _CHAVES_COMUNS}
    meta_merged.update(shard=None, merged_from=relatorio["merged_from"])
    (output_dir / "metadata.json").write_text(
        json.dumps(meta_merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    progress_path = output_dir / "progress.jsonl"
    for r in resultados:
        if r["category"] not in PENDING_CATEGORIES:
            bcb_run._append_progresso(progress_path, r)

    bcb_run._persistir_relatorio(relatorio, output_dir)
    return output_dir, relatorio


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="benchmarks.coding_review.bigcodebench.merge",
        description="Junta os shards (--shard I/N) de um run do BigCodeBench.",
    )
    p.add_argument("shard_dirs", nargs="+", type=Path, help="Diretórios dos N shards.")
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--dataset-path", type=Path, default=bcb_run._DEFAULT_DATASET)
    p.add_argument("--dataset-url", default=DEFAULT_DATASET_URL)
    p.add_argument("--baseline", type=Path, default=None)
    args = p.parse_args(argv)

    out, rel = merge(
        args.shard_dirs,
        output_dir=args.output_dir,
        dataset_path=args.dataset_path,
        dataset_url=args.dataset_url,
        baseline=args.baseline,
    )
    print(
        f"pass@1: {rel['pass_at_k']['pass@1'] * 100:.1f}% ({rel['num_graded']} avaliadas)"
    )
    if rel["pending"]:
        print(
            f"⚠️ {len(rel['pending'])} tarefa(s) pendente(s) — complete com "
            f"`run --resume-dir {out}` e os mesmos parâmetros, sem --shard."
        )
    print(f"Relatório: {out / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
