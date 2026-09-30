"""Task Builder TACO — Cenário 1 (Geração de Gabarito).

Recebe o JSON bruto do exercício TACO e produz uma instrução de
implementação formatada para o cr_coder_agent.
"""

import os

from google.adk.agents import LlmAgent

from . import prompt as task_builder_prompt

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

agent = LlmAgent(
    model=_model,
    name="taco_task_builder_agent",
    description=task_builder_prompt.description,
    instruction=task_builder_prompt.instruction,
    output_key="taco_task",
)
