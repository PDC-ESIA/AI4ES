"""Feedback Composer TACO — Cenário 2 (Revisão de Código do Aluno).

Recebe o output do cr_review_analyzer_agent (APROVADO/BLOQUEADO + issues)
e produz feedback pedagógico construtivo para o aluno.
"""

import os

from google.adk.agents import LlmAgent

from . import prompt as feedback_composer_prompt

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

agent = LlmAgent(
    model=_model,
    name="taco_feedback_composer_agent",
    description=feedback_composer_prompt.description,
    instruction=feedback_composer_prompt.instruction,
    output_key="taco_pedagogical_feedback",
)
