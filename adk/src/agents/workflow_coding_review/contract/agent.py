"""Autor do contrato de interface (`cr_contract_author`), produto web.

Invocado pelo TaskIterator UMA vez por execução, antes da primeira task, quando
`AI4ES_CONTRATO_WEB` está ligada e o `product_type` é web_app (qualquer stack).
O contrato fica em `coder/tasks/_contrato_web.json` (fora do alcance do coder);
ver `shared/tools/coding_tools/contrato_web.py`.
"""

from __future__ import annotations

import json
import logging
import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types

from shared.agent_factory import _bind_tool_to_workspace, lazy_agent_workspace, lazy_workspace_root
from shared.tools.coding_tools import contrato_web
from shared.tools.filesystem import tool_ler_workspace, tool_listar_workspace
from shared.workspace import get_agent_workspace

from . import prompt as contract_prompt

logger = logging.getLogger(__name__)

NOME = "cr_contract_author"
CHAVE_CONTEXTO = "contrato_contexto"

_model = os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash")


def tool_salvar_contrato_web(conteudo: str, tool_context: ToolContext) -> dict:
    """Valida e salva o contrato de interface do produto.

    Args:
        conteudo: JSON do contrato (telas, rotas, convenções).

    Returns:
        dict com `sucesso` e um resumo, ou os erros a corrigir antes de salvar de novo.
    """
    try:
        dados = json.loads(conteudo)
    except ValueError as exc:
        return {"sucesso": False, "erros": [f"JSON inválido: {exc}"]}
    task_ids = [
        t.get("id")
        for t in ((tool_context.state.get("tasks") or {}).get("tasks") or [])
        if isinstance(t, dict)
    ]
    contrato, erros = contrato_web.validar(dados, task_ids)
    if contrato is None:
        return {"sucesso": False, "erros": erros}
    contrato_web.gravar(get_agent_workspace("cr_context_engineer"), contrato)
    resumo = {
        "telas": len(contrato.telas),
        "elementos": len(contrato_web.testids(contrato)),
        "rotas": len(contrato.rotas),
    }
    logger.info("[CONTRATO] contrato de interface gravado: %s", resumo)
    return {"sucesso": True, **resumo}


def _instrucao(readonly_context) -> str:
    contexto = readonly_context.state.get(CHAVE_CONTEXTO) or ""
    return contract_prompt.instruction.replace("{contrato_contexto?}", str(contexto))


def _bind(tool):
    return _bind_tool_to_workspace(tool, lazy_agent_workspace("cr_coder"), lazy_workspace_root())


author = LlmAgent(
    model=_model,
    name=NOME,
    description="Fixa o contrato de interface do produto web a partir do design, antes das tasks.",
    instruction=_instrucao,
    include_contents="none",
    generate_content_config=types.GenerateContentConfig(max_output_tokens=16384),
    tools=[
        _bind(FunctionTool(tool_listar_workspace)),
        _bind(FunctionTool(tool_ler_workspace)),
        FunctionTool(tool_salvar_contrato_web),
    ],
)
