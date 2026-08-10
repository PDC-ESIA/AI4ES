"""Coder do workflow coding_review.

- Prompt sem seções de Git/HITL.
- Tools de filesystem bound a workspace_output/coder/src/ (consolidado).
- Instância dedicada para evitar conflito de parent no pipeline.
"""

import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types

from shared.agent_factory import _bind_tool_to_workspace
from shared.workspace import get_agent_workspace, get_workspace_root
from shared.tools.coding_tools.filesystem_coding import (
    tool_criar_arquivo,
    tool_ler_arquivo,
    tool_substituir_trecho,
)
from shared.tools.filesystem import (
    tool_ler_workspace,
    tool_listar_workspace,
)

from . import prompt as coder_prompt

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

_WORKSPACE_ROOT = str(get_workspace_root())
_CODER_WS = str(get_agent_workspace("cr_coder"))


def _bind(tool):
    return _bind_tool_to_workspace(tool, _CODER_WS, _WORKSPACE_ROOT)


_INSTRUCTION = coder_prompt.build_instruction(_CODER_WS)

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
        _bind(FunctionTool(tool_ler_workspace)),
        _bind(FunctionTool(tool_listar_workspace)),
    ],
)
