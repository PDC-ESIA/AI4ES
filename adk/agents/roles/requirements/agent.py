import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from . import prompt, schemas
from shared.tools.requirements import (
    tool_ler_prd_arquivo_adk,
    tool_salvar_context_window_json_adk,
    tool_salvar_context_window_markdown_adk,
    tool_gerar_doubt_artifact_prd_adk,
)

_DEFAULT_MODEL = "github_copilot/gpt-4"

agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
    name="requirements_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        tool_ler_prd_arquivo_adk,
        tool_salvar_context_window_json_adk,
        tool_salvar_context_window_markdown_adk,
        tool_gerar_doubt_artifact_prd_adk,
    ],
)