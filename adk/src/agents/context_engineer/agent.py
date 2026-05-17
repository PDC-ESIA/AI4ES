"""Context Engineer: transforma requisitos atômicos em Context Windows para o coder.

Portado de feat/me2/coding_squad (Time 4). Adaptado para usar LlmAgent direto
(sem dependência da factory que ainda não existe nesta branch).
"""

import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from . import prompt, schemas
from .tools import tool_salvar_task_adk

_DEFAULT_MODEL = "github_copilot/gpt-4"

agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
    name="context_engineer",
    description=prompt.description,
    instruction=prompt.instruction,
    output_key="tasks",
    output_schema=schemas.TasksOutput,
    tools=[tool_salvar_task_adk],
)
