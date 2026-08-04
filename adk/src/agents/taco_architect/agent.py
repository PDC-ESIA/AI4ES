"""TacoArchitectAgent — Geração de jornadas de exercícios TACO.

App isolada que recebe um mapa conceitual e projeta uma sequência
de exercícios encadeados prontos para inserção no banco do TACO.
"""

import os

from google.adk.agents import LlmAgent

from shared.callbacks.taco_validation import make_taco_validation_callback
from . import prompt
from .schemas import JornadaOutput

_DEFAULT_MODEL = "gemini-2.5-flash"

agent = LlmAgent(
    model=os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL),
    name="taco_architect",
    description=prompt.description,
    instruction=prompt.instruction,
    output_schema=JornadaOutput,
    after_model_callback=make_taco_validation_callback(JornadaOutput),
)

root_agent = agent
