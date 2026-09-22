"""Input Normalizer TACO — converte qualquer entrada para JSON estruturado.

Usado pelo TacoAgent quando a entrada não é JSON válido nem JSON TACO reconhecível.
Recebe texto livre e produz o JSON correto para Cenário 1 (gabarito) ou
Cenário 2 (revisão de código), inferindo campos e aplicando defaults.
"""

import os

from google.adk.agents import LlmAgent

from . import prompt as normalizer_prompt

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

agent = LlmAgent(
    model=_model,
    name="taco_input_normalizer_agent",
    description=normalizer_prompt.description,
    instruction=normalizer_prompt.instruction,
)
