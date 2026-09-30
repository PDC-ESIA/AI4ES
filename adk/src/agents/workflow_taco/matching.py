"""Associação arquivo-variação para o workflow TACO.

Produz um MatchResult por variação em cascata:
1. Exact match  — label normalizado (hífens → underscores) + .py
2. Fuzzy match  — label slug contido no stem ou vice-versa
3. Positional   — por ordem de nome entre os candidatos restantes

Quando um label fica sem correspondência, a causa é derivada
comparando len(candidatos) vs len(variações):
  len(candidatos) < len(variações)  → POSSÍVEL_TRUNCAMENTO
  contagens iguais mas matching falhou → FALHA_DE_MATCHING

Esta é a fonte única de verdade consumida por validator.py e pelo
result_composer — nenhum dos dois faz matching independente.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    path: Path | None
    strategy: str      # "exact" | "fuzzy" | "positional" | "not_found"
    cause: str | None  # "POSSÍVEL_TRUNCAMENTO" | "FALHA_DE_MATCHING" | None


def _label_slug(label: str) -> str:
    return label.replace("-", "_").lower()


def _is_candidate(path: Path, workspace: Path) -> bool:
    """True para .py candidatos a solução — exclui arquivos de teste por padrão."""
    try:
        rel = path.relative_to(workspace)
    except ValueError:
        return False
    parts = rel.parts
    name = path.name
    if any(p in ("tests", "test") for p in parts):
        return False
    if name.startswith("test_") or name.endswith("_test.py"):
        return False
    return path.suffix == ".py"


def match_files(workspace: Path, variations: list[dict]) -> dict[str, MatchResult]:
    """Associa cada label de variação ao arquivo .py gerado pelo coder.

    Args:
        workspace: Raiz do workspace do coder (get_agent_workspace("cr_coder")).
        variations: Lista de dicts com pelo menos o campo "label".

    Returns:
        Dict label → MatchResult (path=None quando não encontrado).
    """
    candidates = sorted(
        p for p in workspace.rglob("*.py") if _is_candidate(p, workspace)
    )

    results: dict[str, MatchResult] = {}
    used: set[Path] = set()

    # Passo 1: exact match (stem == slug normalizado)
    for var in variations:
        label = var["label"]
        slug = _label_slug(label)
        for candidate in candidates:
            if candidate in used:
                continue
            if candidate.stem.lower() == slug:
                results[label] = MatchResult(path=candidate, strategy="exact", cause=None)
                used.add(candidate)
                break

    # Passo 2: fuzzy (slug contido no stem ou vice-versa)
    unmatched = [v for v in variations if v["label"] not in results]
    for var in unmatched:
        label = var["label"]
        slug = _label_slug(label)
        for candidate in candidates:
            if candidate in used:
                continue
            stem = candidate.stem.lower()
            if slug in stem or stem in slug:
                results[label] = MatchResult(path=candidate, strategy="fuzzy", cause=None)
                used.add(candidate)
                break

    # Passo 3: positional fallback
    still_unmatched = [v for v in variations if v["label"] not in results]
    remaining = [c for c in candidates if c not in used]

    n_vars = len(still_unmatched)
    n_cands = len(remaining)

    if n_cands > n_vars and n_vars > 0:
        logger.warning(
            "[TACO-MATCH] EXCESSO_CANDIDATOS: %d arquivos para %d variações restantes"
            " — fallback posicional pode desalinhar associações.",
            n_cands,
            n_vars,
        )

    for var, candidate in zip(still_unmatched, remaining):
        results[var["label"]] = MatchResult(
            path=candidate, strategy="positional", cause=None
        )

    # Entradas nulas: derivar causa a partir da contagem total
    n_total_cands = len(candidates)
    n_total_vars = len(variations)
    for var in variations:
        label = var["label"]
        if label not in results:
            cause = (
                "POSSÍVEL_TRUNCAMENTO"
                if n_total_cands < n_total_vars
                else "FALHA_DE_MATCHING"
            )
            results[label] = MatchResult(path=None, strategy="not_found", cause=cause)
            logger.warning(
                "[TACO-MATCH] label '%s' sem arquivo correspondente: %s",
                label,
                cause,
            )

    return results
