"""Funções puras do orchestrator — testáveis sem ADK runtime.

Separadas de `agent.py` para isolar a lógica de orquestração (loop,
runners, eventos) das funções determinísticas (parsing, manipulação
de state, inspeção de event shape).
"""

from datetime import datetime, timezone
from typing import Any


def _parse_decision(text: str, allowed: list[str]) -> tuple[str, str]:
    """Parseia texto livre humano em (decision, comments).

    Regras:
        - Primeiro token (separado por whitespace) é a decisão.
        - Case insensitive; trailing punctuation removida.
        - Match exato ou prefixo (ex: "aprov" -> "aprovar").
        - Resto do texto vira `comments`.

    Args:
        text: Texto digitado pelo usuário.
        allowed: Lista de decisões aceitáveis.

    Returns:
        (decision_lower, comments_stripped). `decision_lower` é uma das
        strings de `allowed` (lowercase).

    Raises:
        ValueError: Se o texto for vazio ou não casar com nenhuma opção.
    """
    stripped = text.strip()
    if not stripped:
        raise ValueError("texto vazio")
    parts = stripped.split(None, 1)
    first = parts[0].lower().rstrip(",.;:!?")
    rest = parts[1] if len(parts) > 1 else ""

    for opt in allowed:
        opt_lower = opt.lower()
        if first == opt_lower or opt_lower.startswith(first):
            return opt_lower, rest

    raise ValueError(
        f"'{first}' não casa com nenhuma das decisões permitidas: {allowed}"
    )
