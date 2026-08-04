"""TacoResearchAgent — Mapeamento conceitual para jornadas TACO.

App isolada que recebe um escopo de aprendizado e devolve um mapa
conceitual sequencial ordenado por pré-requisitos pedagógicos.
"""

import os

from google.adk.agents import LlmAgent

from shared.callbacks.taco_validation import make_taco_validation_callback
from . import prompt
from .schemas import MapaConceitual

_DEFAULT_MODEL = "gemini-2.5-flash"

agent = LlmAgent(
    model=os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL),
    name="taco_research",
    description=prompt.description,
    instruction=prompt.instruction,
    output_schema=MapaConceitual,
    after_model_callback=make_taco_validation_callback(MapaConceitual),
)

root_agent = agent
