"""Métricas do benchmark BigCodeBench: Pass@1, falhas por categoria e baseline.

Com 1 amostra por tarefa, pass@1 é a taxa de tarefas aprovadas. A comparação com
o HumanEval é opcional e só lê o `report.json` de um run dele (dado, não código).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .categories import (
    LIBRARY_FAILURES,
    LOGIC_FAILURES,
    OTHER_FAILURES,
)

__all__ = [
    "aggregate_failures",
    "compare_with_baseline",
    "load_baseline",
    "pass_at_1",
]

_GROUPS = {
    "library": LIBRARY_FAILURES,
    "logic": LOGIC_FAILURES,
    "other": OTHER_FAILURES,
}


def pass_at_1(resultados: list[dict]) -> float:
    """Taxa de tarefas aprovadas (1 amostra por tarefa)."""
    if not resultados:
        return 0.0
    return sum(1 for r in resultados if r["passed"]) / len(resultados)


def aggregate_failures(resultados: list[dict]) -> dict:
    """Conta as reprovações por categoria e por grupo (biblioteca × lógica × outras).

    Returns:
        ``{"total_failures", "by_category", "by_group"}`` — `by_group` separa as
        falhas de biblioteca (ausente / import / API) das de lógica.
    """
    reprovadas = [r for r in resultados if not r["passed"]]
    por_categoria = Counter(r["category"] for r in reprovadas)
    por_grupo = {
        grupo: sum(por_categoria.get(c, 0) for c in categorias)
        for grupo, categorias in _GROUPS.items()
    }
    return {
        "total_failures": len(reprovadas),
        "by_category": dict(sorted(por_categoria.items())),
        "by_group": por_grupo,
    }


def load_baseline(path: Path) -> dict | None:
    """Lê um relatório do HumanEval (`report.json` ou o diretório do run).

    Returns:
        ``{"model", "num_problems", "pass_at_1", "source"}`` ou None se ausente.
    """
    if path.is_dir():
        path = path / "report.json"
    if not path.is_file():
        return None
    try:
        rel = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    p1 = (rel.get("pass_at_k") or {}).get("pass@1")
    if p1 is None:
        return None
    return {
        "model": rel.get("model"),
        "num_problems": rel.get("num_problems"),
        "pass_at_1": p1,
        "source": str(path),
    }


def compare_with_baseline(pass1: float, baseline: dict) -> dict:
    """Quantifica a queda do BigCodeBench em relação ao baseline do HumanEval."""
    base = baseline["pass_at_1"]
    return {
        "humaneval_pass_at_1": base,
        "bigcodebench_pass_at_1": pass1,
        "delta_pp": round((pass1 - base) * 100, 1),
        "relative_drop_pct": round((base - pass1) / base * 100, 1) if base else None,
        "humaneval_model": baseline.get("model"),
        "humaneval_num_problems": baseline.get("num_problems"),
        "humaneval_source": baseline.get("source"),
    }
