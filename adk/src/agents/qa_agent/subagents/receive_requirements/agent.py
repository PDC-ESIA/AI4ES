"""Definição do LlmAgent receber_requisitos."""

import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from .orchestration import receber_requisitos
from .prompt import RECEBER_REQUISITOS_PROMPT

agent = LlmAgent(
    name="receber_requisitos",
    model=os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash"),
    description=(
        "Subagente que recebe artefatos de requisito em JSON e gera arquivos pytest "
        "funcionais em workspace_output/tests/inputs/."
    ),
    instruction=RECEBER_REQUISITOS_PROMPT,
    tools=[
        FunctionTool(receber_requisitos),
    ],
)
