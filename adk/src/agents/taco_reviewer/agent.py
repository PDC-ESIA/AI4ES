"""TacoReviewerAgent — Review pedagógico de submissões TACO.

App isolada que recebe a submissão de um aluno com contexto do exercício
e devolve feedback formativo estruturado para professor ou aluno.
"""

import os

from google.adk.agents import LlmAgent

from shared.callbacks.taco_validation import make_taco_validation_callback
from . import prompt
from .schemas import TacoReviewOutput

_DEFAULT_MODEL = "gemini-2.5-flash"

agent = LlmAgent(
    model=os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL),
    name="taco_reviewer",
    description=prompt.description,
    instruction=prompt.instruction,
    output_schema=TacoReviewOutput,
    after_model_callback=make_taco_validation_callback(TacoReviewOutput),
)

root_agent = agent
