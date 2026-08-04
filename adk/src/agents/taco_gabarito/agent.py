"""TacoGabaritoAgent — Geração de gabaritos para exercícios TACO.

App isolada que recebe a especificação de um exercício e devolve N
soluções de referência estruturadas, prontas para uso como gabarito.
"""

import os

from google.adk.agents import LlmAgent

from shared.callbacks.taco_validation import make_taco_validation_callback
from . import prompt
from .schemas import GabaritoOutput

_DEFAULT_MODEL = "gemini-2.5-flash"

agent = LlmAgent(
    model=os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL),
    name="taco_gabarito",
    description=prompt.description,
    instruction=prompt.instruction,
    output_schema=GabaritoOutput,
    after_model_callback=make_taco_validation_callback(GabaritoOutput),
)

root_agent = agent
