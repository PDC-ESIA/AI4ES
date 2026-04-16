"""App raiz: orquestrador que delega ao pipeline SDLC ou a agentes pontuais."""

import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool

from agents.roles.coder.agent import agent as coder_specialist
from agents.roles.reviewer.agent import agent as reviewer_specialist
from agents.workflows.coding.agent import agent as sdlc_pipeline

from . import prompt

_DEFAULT_MODEL = "github_copilot/gpt-4"

root_agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
    name="orchestrator",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        AgentTool(agent=sdlc_pipeline),
        AgentTool(agent=coder_specialist),
        AgentTool(agent=reviewer_specialist),
    ],
)
