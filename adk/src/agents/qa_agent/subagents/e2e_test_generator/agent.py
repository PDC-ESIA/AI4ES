"""Definição multistack do subagente E2E."""

import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types

from .orchestration import inspecionar_projeto_e2e, preparar_testes_e2e
from .prompt import E2E_TEST_GENERATOR_PROMPT


agent = LlmAgent(
    name="e2e_test_generator",
    model=os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash"),
    description=(
        "Inspeciona projetos e gera ou executa Playwright E2E para as famílias "
        "de stack declaradas pelo Coder."
    ),
    instruction=E2E_TEST_GENERATOR_PROMPT,
    tools=[
        FunctionTool(inspecionar_projeto_e2e),
        FunctionTool(preparar_testes_e2e),
    ],
    output_key="last_e2e_test_result",
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
)
