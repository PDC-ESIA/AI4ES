import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool

from shared.tools import tool_ler_diff, tool_salvar_relatorio
from . import prompt

_DEFAULT_MODEL = "github_copilot/gpt-4"

agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
    name="review_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    output_key="review",
    tools=[
        FunctionTool(tool_ler_diff),
        FunctionTool(tool_salvar_relatorio),
    ],
)
