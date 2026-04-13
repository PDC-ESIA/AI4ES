import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool

from agents.roles.design_architect.agent import agent as design_architect
from agents.roles.mermaid_specialist.agent import agent as mermaid_specialist
from agents.roles.markdown_specialist.agent import agent as markdown_specialist
from agents.roles.validator.agent import agent as validator
from agents.roles.io_agent.agent import agent as io_agent
from . import prompt

_DEFAULT_MODEL = "github_copilot/gpt-4"

root_agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
    name="orchestrator",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        AgentTool(agent=design_architect),
        AgentTool(agent=mermaid_specialist),
        AgentTool(agent=markdown_specialist),
        AgentTool(agent=validator),
        AgentTool(agent=io_agent),
    ],
)