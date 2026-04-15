import os
 
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
 
from . import prompt, schemas
from .tools_requirements import (
    tool_ler_prd_arquivo_adk,
    tool_gerar_doubt_artifact_adk,
)
 
_DEFAULT_MODEL = "github_copilot/gpt-4"
 
agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
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