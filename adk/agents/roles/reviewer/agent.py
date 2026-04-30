from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from shared.llm import get_model
from shared.tools import tool_ler_diff, tool_salvar_relatorio
from . import prompt

agent = LlmAgent(
    model=get_model(agent_name="review_agent"),
    name="review_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    output_key="review",
    tools=[
        FunctionTool(tool_ler_diff),
        FunctionTool(tool_salvar_relatorio),
    ],
)


# ADK CLI busca por `root_agent` ao carregar um app diretamente.
root_agent = agent
