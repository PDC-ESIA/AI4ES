"""Definição multistack do subagente de integração."""

import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types

from .orchestration import inspecionar_projeto_integracao, preparar_testes_integracao
from .prompt import INTEGRATION_TEST_PROMPT


agent = LlmAgent(
    name="integration_tests_agent",
    model=os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash"),
    description=(
        "Inspeciona, gera e executa testes de integração para as famílias "
        "de stack declaradas pelo Coder."
    ),
    instruction=INTEGRATION_TEST_PROMPT,
    tools=[
        FunctionTool(inspecionar_projeto_integracao),
        FunctionTool(preparar_testes_integracao),
    ],
    output_key="last_integration_test_result",
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
)

integration_tests_agent = agent
