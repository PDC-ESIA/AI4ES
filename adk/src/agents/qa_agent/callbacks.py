"""Controles determinísticos do ciclo de ferramentas do QA Agent."""

import json
from typing import Any

from google.adk.agents.context import Context
from google.adk.models import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

_E2E_EXECUTADO_KEY = "temp:qa_agent:e2e_executado"
_E2E_RESULTADO_KEY = "temp:qa_agent:e2e_resultado"
_E2E_RESPOSTA_EMITIDA_KEY = "temp:qa_agent:e2e_resposta_emitida"


def bloquear_reexecucao_e2e(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
) -> dict[str, Any] | None:
    """Permite uma única chamada E2E por invocação do QA Agent."""

    del args
    if tool.name != "e2e_test_generator":
        return None
    if tool_context.state.get(_E2E_EXECUTADO_KEY, False):
        return {
            "tipo_saida": "bloqueado_reexecucao",
            "codigo": "REEXECUCAO_E2E_BLOQUEADA",
            "mensagem": (
                "O e2e_test_generator já foi executado nesta invocação. "
                "Use o resultado anterior para responder diretamente no chat."
            ),
            "resultado_terminal": True,
            "nao_reexecutar": True,
        }
    tool_context.state[_E2E_EXECUTADO_KEY] = True
    return None


def registrar_resultado_e2e(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: Context,
    tool_response: dict[str, Any],
) -> None:
    """Preserva o primeiro retorno E2E para a resposta terminal do QA."""

    del args
    if tool.name != "e2e_test_generator":
        return None
    if tool_context.state.get(_E2E_RESULTADO_KEY) is None:
        tool_context.state[_E2E_RESULTADO_KEY] = tool_response
    return None


def emitir_resultado_e2e_sem_reinterpretacao(
    callback_context: Context,
    llm_response: LlmResponse,
) -> LlmResponse | None:
    """Substitui a paráfrase do modelo pelo objeto E2E integral."""

    resultado = callback_context.state.get(_E2E_RESULTADO_KEY)
    if resultado is None or callback_context.state.get(
        _E2E_RESPOSTA_EMITIDA_KEY, False
    ):
        return None

    if hasattr(resultado, "model_dump"):
        resultado = resultado.model_dump(mode="json")
    texto_json = json.dumps(
        resultado,
        ensure_ascii=False,
        indent=2,
        default=str,
    )
    callback_context.state[_E2E_RESPOSTA_EMITIDA_KEY] = True
    return llm_response.model_copy(
        update={
            "content": types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text=f"Resultado E2E terminal:\n\n```json\n{texto_json}\n```"
                    )
                ],
            ),
            "turn_complete": True,
        }
    )
