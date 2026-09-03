"""Review Builder TACO — Cenário 2 (Revisão de Código do Aluno).

Recebe código do aluno + JSON do exercício e formata uma instrução
para o cr_review_analyzer_agent.
"""

import os

from google.adk.agents import LlmAgent

from . import prompt as review_builder_prompt

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

agent = LlmAgent(
    model=_model,
    name="taco_review_builder_agent",
    description=review_builder_prompt.description,
    instruction=review_builder_prompt.instruction,
    output_key="taco_review_task",
)
