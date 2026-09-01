"""Handoff determinístico da stack declarada para o Coder."""

from __future__ import annotations

import json
import re
from pathlib import Path

from shared.workspace import get_agent_workspace

_MACRO_CONTEXT_FILENAME = "_macro_context.json"
_STACK_MARKERS = {
    "python": re.compile(r"\b(?:python|fastapi|pytest)\b", re.IGNORECASE),
    "node": re.compile(
        r"\b(?:node(?:\.js|js)?|express|javascript|typescript)\b",
        re.IGNORECASE,
    ),
    "java": re.compile(r"\b(?:java|spring|maven|gradle|junit)\b", re.IGNORECASE),
    "go": re.compile(r"\b(?:go|golang)\b", re.IGNORECASE),
}


def resolve_coder_stack(tech_stack: object) -> str:
    """Normaliza a família já declarada; não interpreta arquivos de código."""
    if isinstance(tech_stack, str):
        values = [tech_stack]
    elif isinstance(tech_stack, list):
        values = [value for value in tech_stack if isinstance(value, str)]
    else:
        return ""

    declared = " ".join(values).strip()
    if not declared or declared.casefold() == "a definir":
        return ""
    matches = {
        stack for stack, pattern in _STACK_MARKERS.items() if pattern.search(declared)
    }
    return matches.pop() if len(matches) == 1 else ""


def load_coder_stack(macro_context_path: Path | None = None) -> str:
    """Lê `tech_stack` do contexto entregue ao Coder, quando disponível."""
    path = macro_context_path
    if path is None:
        path = get_agent_workspace("cr_context_engineer") / _MACRO_CONTEXT_FILENAME
    if not path.is_file():
        return ""
    try:
        macro_context = json.loads(path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return ""
    if not isinstance(macro_context, dict):
        return ""
    return resolve_coder_stack(macro_context.get("tech_stack"))


__all__ = ["load_coder_stack", "resolve_coder_stack"]
