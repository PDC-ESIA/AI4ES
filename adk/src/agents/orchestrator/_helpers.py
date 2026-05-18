"""Funções puras do orchestrator — testáveis sem ADK runtime.

Separadas de `agent.py` para isolar a lógica de orquestração (loop,
runners, eventos) das funções determinísticas (parsing, manipulação
de state, inspeção de event shape).
"""

from datetime import datetime, timezone
from typing import Any


EMPTY_RETRY_PROMPT = (
    "Sua resposta anterior veio vazia. Por favor, reprocesse o pedido. "
    "Se não conseguir gerar um output útil, devolva um JSON ou texto curto "
    "explicando o bloqueio — NUNCA devolva string vazia."
)


def _is_empty_response(last_text) -> bool:
    """True quando o texto do LLM é vazio (None, "", ou só whitespace).

    Usado pelo orchestrator para detectar pipelines que devolveram nada
    e disparar retry uma vez antes de propagar falha.

    Args:
        last_text: Último texto acumulado do pipeline. Pode ser None,
            string vazia, whitespace, ou texto real.

    Returns:
        True se vazio (não-utilizável), False caso contrário.
    """
    if last_text is None:
        return True
    return not last_text.strip()


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


def _is_pending_long_running_call(part, event) -> bool:
    """True quando o part contém function_call long-running pendente no event.

    Detecção: `event.long_running_tool_ids` (set[str] | None) contém o
    `part.function_call.id`. ADK popula esse set quando emite um
    function_call de uma LongRunningFunctionTool sem auto-resposta.

    Args:
        part: `google.genai.types.Part` candidato.
        event: `google.adk.events.Event` que contém o part.

    Returns:
        True se part.function_call é um long-running pendente.
    """
    fc = getattr(part, "function_call", None)
    if fc is None:
        return False
    ids = getattr(event, "long_running_tool_ids", None)
    if not ids:
        return False
    return fc.id in ids


def _extract_user_text(ctx) -> str:
    """Concatena os textos dos parts de `ctx.user_content`.

    Retorna string vazia quando user_content é None ou todos os parts
    são não-texto (function_response, function_call, etc.).
    """
    user_content = getattr(ctx, "user_content", None)
    if user_content is None:
        return ""
    parts = getattr(user_content, "parts", None) or []
    chunks = []
    for part in parts:
        text = getattr(part, "text", None)
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()


def _build_input(user_text: str, accumulated: list[tuple[str, str]]) -> str:
    """Monta input para um pipeline interno.

    Sem accumulated: retorna `user_text` sem modificações (FRESH RUN do
    primeiro pipeline). Com accumulated: anexa "CONTEXTO DAS FASES
    ANTERIORES" com cada output truncado em 8000 caracteres.
    """
    if not accumulated:
        return user_text

    prior = "\n\n".join(
        f"### Output de {nome}:\n{texto[:8000]}"
        for nome, texto in accumulated
    )
    return (
        f"{user_text}\n\n"
        f"---\n"
        f"CONTEXTO DAS FASES ANTERIORES:\n{prior}\n"
        f"---\n"
    )


def _set_pause_state(
    state: dict[str, Any],
    *,
    pipeline_name: str,
    inner_session_id: str,
    function_call_id: str,
    function_call_name: str,
    function_call_args: dict[str, Any],
) -> None:
    """Grava as 3 chaves de pausa em state. Invariante: ou todas ou nenhuma."""
    state["paused_pipeline"] = pipeline_name
    state["paused_inner_session_id"] = inner_session_id
    state["paused_function_call"] = {
        "id": function_call_id,
        "name": function_call_name,
        "args": function_call_args,
    }


def _clear_pause_state(state: dict[str, Any]) -> None:
    """Zera as 3 chaves de pausa. Preserva `accumulated_outputs`."""
    state["paused_pipeline"] = None
    state["paused_inner_session_id"] = None
    state["paused_function_call"] = None


def _build_function_response_payload(
    decision: str,
    comments: str,
    checkpoint_id: str,
) -> dict[str, Any]:
    """Payload do function_response enviado ao runner pausado."""
    return {
        "decision": decision,
        "comments": comments,
        "reviewer": "usuario",
        "validated_at": datetime.now(timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checkpoint_id": checkpoint_id,
    }
