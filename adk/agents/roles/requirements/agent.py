from shared.factory import create_agent
from . import prompt, schemas
from .tools_requirements import (
    tool_ler_prd_arquivo_adk,
    tool_gerar_doubt_artifact_adk,
)

agent = create_agent(
    name="requirements_agent",
    model_key="requirements_agent",
    instruction=prompt.instruction,
    description=prompt.description,
    output_schema=schemas.RequirementsOutput,
    output_key="requirements",
    tools=[
        tool_ler_prd_arquivo_adk,
        tool_gerar_doubt_artifact_adk,
    ],
)
