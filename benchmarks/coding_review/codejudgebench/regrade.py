"""Recalcula o relatório de um run a partir das revisões salvas — sem LLM.

Uso (a partir da raiz do repositório):

    python -m benchmarks.coding_review.codejudgebench.regrade results/run_<ts>_<modelo>_n50 [...]

Relê `reviews/<par>_<pos|neg>.md`, refaz a leitura das issues com o parser
atual de `contract.py` e regrava `report.json` e `report.md`. Os vereditos
(pass/fail/absent) NÃO mudam: eles vêm do manifesto no momento do run. Serve
para corrigir a leitura das issues (severidade, camada) sem pagar um novo run.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from benchmarks.coding_review.codejudgebench.contract import parse_review_markdown
from benchmarks.coding_review.codejudgebench.metrics import compute_metrics
from benchmarks.coding_review.codejudgebench.run import _persistir_relatorio


def _slug(pair_id: str) -> str:
    """Mesmo slug de `RepairPair.slug` (``claude_3.7_sonnet/42`` → ``claude_3_7_sonnet_0042``)."""
    split, _, row = pair_id.rpartition("/")
    return f"{split.replace('.', '_')}_{int(row):04d}"


def regrade(run_dir: Path) -> dict:
    """Reprocessa as issues de um run e regrava o relatório; devolve o relatório."""
    report_path = run_dir / "report.json"
    relatorio = json.loads(report_path.read_text(encoding="utf-8"))
    for registro in relatorio["pairs"]:
        for which in ("pos", "neg"):
            md = run_dir / "reviews" / f"{_slug(registro['pair_id'])}_{which}.md"
            if md.is_file():
                texto = md.read_text(encoding="utf-8", errors="replace")
                registro[which]["issues"] = parse_review_markdown(texto).issues
    relatorio["metrics"] = compute_metrics(relatorio["pairs"])
    relatorio["regraded_at"] = datetime.now(timezone.utc).isoformat()
    _persistir_relatorio(relatorio, run_dir)
    return relatorio


def main(argv: list[str] | None = None) -> int:
    dirs = [Path(a) for a in (argv if argv is not None else sys.argv[1:])]
    if not dirs:
        print("Uso: python -m benchmarks.coding_review.codejudgebench.regrade <run_dir> [...]")
        return 2
    for run_dir in dirs:
        camadas = regrade(run_dir)["metrics"]["decision"]["critical_issue_layers_on_false_blocks"]
        print(f"[regrade] {run_dir.name}: camadas dos bloqueios indevidos = {camadas or 'nenhuma'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
