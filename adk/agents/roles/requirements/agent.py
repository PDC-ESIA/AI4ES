from google.adk.agents import LlmAgent

from shared.llm import get_model
from . import prompt, schemas
from .tools_requirements import (
    tool_ler_prd_arquivo_adk,
    tool_gerar_doubt_artifact_adk,
)

agent = LlmAgent(
    model=get_model(),
    name="requirements_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    output_schema=schemas.RequirementsOutput,
    output_key="requirements",
    tools=[
        tool_ler_prd_arquivo_adk,
        tool_gerar_doubt_artifact_adk,
    ],
)