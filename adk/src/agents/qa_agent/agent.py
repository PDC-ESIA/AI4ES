from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from .tools.receive_requirements import receber_requisitos
from .tools.pytest_runner import executar_pytest_tool

from .prompts import QA_PROMPT

qa_agent = Agent(
    name="qa_agent",
    model="gemini-2.5-flash",
    description=(
        "Agente QA do Time 3 — PDC-AI4SE. "
        "Recebe artefatos de requisito (RF, HU, UC, RNF, RN), "
        "gera testes pytest automaticamente em paralelo e reporta cobertura."
    ),
    instruction=QA_PROMPT,
    
    tools=[
        FunctionTool(receber_requisitos),
        FunctionTool(executar_pytest_tool),
    ],
)