from google.adk.tools import FunctionTool

from shared.agent_factory import create_se_agent
from shared.tools import tool_ler_diff, tool_salvar_relatorio
from . import prompt, schemas

agent = create_se_agent(
    name="review_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    output_key="review",
    output_schema=schemas.ReviewOutput,
    tools=[
        FunctionTool(tool_ler_diff),
        FunctionTool(tool_salvar_relatorio),
    ],
)

# ADK CLI busca por `root_agent` ao carregar um app diretamente.
root_agent = agent
