"""Callback de validação pós-LLM para agentes TACO.

Extrai JSON da resposta do LLM (mesmo quando vem envolto em markdown
ou com campos renomeados), valida contra o schema Pydantic esperado e
injeta o JSON normalizado de volta na resposta. Quando a validação
falha, preserva a resposta original e loga o erro no state para
diagnóstico.
"""

import json
import logging
import re
from typing import Type

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# Mapeamento de nomes errados comuns → nomes corretos do schema
_FIELD_ALIASES: dict[str, dict[str, str]] = {
    "GabaritoOutput": {
        "gabaritos": "solucoes",
        "solutions": "solucoes",
        "rotulo": "rotulo_variacao",
        "label": "rotulo_variacao",
        "resumo": "resumo_abordagem",
        "summary": "resumo_abordagem",
        "conceitos": "conceitos_exercitados",
        "concepts": "conceitos_exercitados",
        "validacao": "validacao_exemplos",
        "validation": "validacao_exemplos",
    },
    "ValidacaoExemplo": {
        "stdout": "esperado",
        "expected": "esperado",
        "output": "obtido",
        "result": "obtido",
        "passed": "passou",
    },
}


def _extract_json(text: str) -> str | None:
    """Extrai bloco JSON de texto que pode conter markdown fences."""
    # Tenta extrair de bloco ```json ... ```
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Tenta encontrar objeto JSON direto (primeiro { até último })
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1]

    return None


def _normalize_keys(obj: object, schema_name: str) -> object:
    """Aplica aliases de campo recursivamente em dicts/lists."""
    aliases = _FIELD_ALIASES.get(schema_name, {})

    if isinstance(obj, dict):
        normalized = {}
        for key, value in obj.items():
            new_key = aliases.get(key, key)
            # Normaliza recursivamente items de listas aninhadas
            if new_key in ("solucoes", "gabaritos", "solutions") and isinstance(
                value, list
            ):
                value = [_normalize_keys(item, schema_name) for item in value]
            elif new_key in (
                "validacao_exemplos",
                "validacao",
                "validation",
            ) and isinstance(value, list):
                value = [
                    _normalize_keys(item, "ValidacaoExemplo") for item in value
                ]
            normalized[new_key] = value
        return normalized

    if isinstance(obj, list):
        return [_normalize_keys(item, schema_name) for item in obj]

    return obj


def make_taco_validation_callback(
    schema: Type[BaseModel],
):
    """Cria um after_model_callback que valida a resposta contra o schema.

    Args:
        schema: Classe Pydantic esperada (ex: GabaritoOutput).

    Returns:
        Callback compatível com LlmAgent.after_model_callback.
    """
    schema_name = schema.__name__

    def _validate_response(
        callback_context: CallbackContext,
        llm_response: LlmResponse,
    ) -> LlmResponse | None:
        # Extrai texto da resposta
        if not llm_response.content or not llm_response.content.parts:
            return None

        text_parts = [p.text for p in llm_response.content.parts if p.text]
        if not text_parts:
            return None

        full_text = "\n".join(text_parts)
        json_str = _extract_json(full_text)
        if json_str is None:
            logger.warning(
                "[taco_validation] Nenhum JSON encontrado na resposta de %s",
                schema_name,
            )
            callback_context.state["taco_validation_error"] = (
                "Nenhum bloco JSON encontrado na resposta do LLM."
            )
            return None

        try:
            raw = json.loads(json_str)
        except json.JSONDecodeError as exc:
            logger.warning(
                "[taco_validation] JSON inválido para %s: %s",
                schema_name,
                exc,
            )
            callback_context.state["taco_validation_error"] = (
                f"JSON parse error: {exc}"
            )
            return None

        # Normaliza campos com nomes errados
        normalized = _normalize_keys(raw, schema_name)

        # Valida contra o schema Pydantic
        try:
            validated = schema.model_validate(normalized)
        except ValidationError as exc:
            logger.warning(
                "[taco_validation] Validação falhou para %s: %s",
                schema_name,
                exc,
            )
            callback_context.state["taco_validation_error"] = (
                f"Schema validation error: {exc}"
            )
            return None

        # Sucesso: substitui resposta pelo JSON normalizado
        clean_json = validated.model_dump_json(indent=2, ensure_ascii=False)
        callback_context.state.pop("taco_validation_error", None)
        callback_context.state["taco_validation_ok"] = True

        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text=clean_json)],
            ),
        )

    return _validate_response
