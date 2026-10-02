"""Coder do workflow coding_review.

- Prompt sem seções de Git/HITL.
- Tools de filesystem bound a workspace_output/coder/src/ (consolidado).
- Instância dedicada para evitar conflito de parent no pipeline.
"""

import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types

from shared.agent_factory import (
    _bind_tool_to_workspace,
    lazy_agent_workspace,
    lazy_workspace_root,
    session_instruction,
)
from shared.workspace import get_agent_workspace
from shared.tools.coding_tools.filesystem_coding import (
    tool_criar_arquivo,
    tool_ler_arquivo,
    tool_remover_arquivo,
    tool_substituir_trecho,
)
from shared.tools.filesystem import (
    tool_ler_workspace,
    tool_listar_workspace,
)

from . import prompt as coder_prompt
from .workspace_guard import (
    anunciar_arquivos_herdados,
    auditar_remocao,
    bloquear_sobrescrita_herdada,
)

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

# Workspace resolvido a cada chamada/invocação: a raiz depende da sessão.
def _bind(tool):
    return _bind_tool_to_workspace(
        tool, lazy_agent_workspace("cr_coder"), lazy_workspace_root()
    )


def render_instruction() -> str:
    """Instrução (template, sem injeção de state) para o workspace da sessão."""
    return coder_prompt.build_instruction(str(get_agent_workspace("cr_coder")))


_INSTRUCTION = session_instruction(render_instruction)

agent = LlmAgent(
    model=_model,
    name="cr_coder_agent",
    description="Implementa código funcional a partir de requisitos, sem git.",
    instruction=_INSTRUCTION,
    output_key="implementation",
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=16384,
    ),
    tools=[
        _bind(FunctionTool(tool_criar_arquivo)),
        _bind(FunctionTool(tool_ler_arquivo)),
        _bind(FunctionTool(tool_substituir_trecho)),
        _bind(FunctionTool(tool_remover_arquivo)),
        _bind(FunctionTool(tool_ler_workspace)),
        _bind(FunctionTool(tool_listar_workspace)),
    ],
    # As frentes da proteção inter-task (ver `workspace_guard`): `anunciar_`
    # avisa que o projeto já existe antes da primeira escrita da task;
    # `bloquear_` recusa a sobrescrita se o aviso não bastar; `auditar_`
    # registra remoções e libera o caminho removido da baseline.
    before_tool_callback=bloquear_sobrescrita_herdada,
    after_tool_callback=[anunciar_arquivos_herdados, auditar_remocao],
)
