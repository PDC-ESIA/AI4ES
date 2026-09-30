"""Result Composer TACO — Cenário 1 (Geração de Gabarito).

Recebe o resultado do matching + validação e produz a resposta
final estruturada por variação para o docente do TACO.
"""

import os

from google.adk.agents import LlmAgent

from . import prompt as result_composer_prompt

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

agent = LlmAgent(
    model=_model,
    name="taco_result_composer_agent",
    description=result_composer_prompt.description,
    instruction=result_composer_prompt.instruction,
    output_key="taco_response",
)
