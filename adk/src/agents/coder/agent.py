from google.adk.tools import FunctionTool

from shared.agent_factory import create_se_agent
from shared.tools.coding_review import (
    tool_criar_arquivo,
    tool_git_add,
    tool_git_checkout,
    tool_git_commit,
    tool_ler_arquivo,
    tool_substituir_trecho,
)
from . import prompt

agent = create_se_agent(
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

# ADK CLI busca por `root_agent` ao carregar um app diretamente.
root_agent = agent
