"""Executor ADK de cenários e código E2E previamente planejados."""

import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from .prompt import E2E_TEST_GENERATOR_PROMPT
from .tools.gerar_testes_e2e import gerar_testes_e2e


agent = LlmAgent(
    name="e2e_test_generator",
    model=os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash"),
    description=(
        "Consome um plano validado do action_planner, materializa cenários E2E "
        "e gera/executa specs Playwright localmente para jornadas web."
    ),
    instruction=E2E_TEST_GENERATOR_PROMPT,
    tools=[FunctionTool(gerar_testes_e2e)],
)
