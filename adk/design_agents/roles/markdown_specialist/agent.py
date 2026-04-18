import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool

from design_agents.roles.io_agent.agent import agent as io_agent
from shared.tools.date import current_date
from . import prompt

_DEFAULT_MODEL = "github_copilot/gpt-4"

agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
    name="markdown_specialist",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        AgentTool(agent=io_agent),
        current_date,
    ],
)