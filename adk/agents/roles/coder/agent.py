import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool

from shared.tools import (
    tool_criar_arquivo,
    tool_git_add,
    tool_git_checkout,
    tool_git_commit,
    tool_ler_arquivo,
    tool_substituir_trecho,
)
from . import prompt

_DEFAULT_MODEL = "github_copilot/gpt-4"

agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
    name="coder_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    output_key="implementation",
    tools=[
        FunctionTool(tool_criar_arquivo),
        FunctionTool(tool_git_add),
        FunctionTool(tool_git_commit, require_confirmation=True),
        FunctionTool(tool_git_checkout),
        FunctionTool(tool_ler_arquivo),
        FunctionTool(tool_substituir_trecho),
    ],
)
