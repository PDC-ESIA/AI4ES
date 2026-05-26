import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool

from agents.workflows.design_pipeline.agent import agent as design_pipeline
from agents.roles.io_agent.agent import agent as io_agent
from . import prompt

_DEFAULT_MODEL = "github_copilot/gpt-4"

root_agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
    name="design_orchestrator",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        AgentTool(agent=design_pipeline),
        AgentTool(agent=io_agent),
    ],
)