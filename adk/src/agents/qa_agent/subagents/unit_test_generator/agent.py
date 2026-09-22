"""Definição do subagente de testes unitários."""

import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types

from .orchestration import gerar_testes_unitarios, inspecionar_projeto_unitario
from .prompt import UNIT_TEST_PROMPT


agent = LlmAgent(
    name="unit_test_generator",
    model=os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash"),
    description=(
        "Inspeciona a stack e gera testes unitários pelo perfil registrado. "
        "Executa perfis de alta e média prioridade em seus runtimes nativos e "
        "bloqueia frameworks não identificados ou dependências ausentes."
    ),
    instruction=UNIT_TEST_PROMPT,
    tools=[
        FunctionTool(inspecionar_projeto_unitario),
        FunctionTool(gerar_testes_unitarios),
    ],
    output_key="last_unit_test_result",
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
)
