"""App raiz: orquestrador que delega ao pipeline SDLC ou a agentes pontuais."""

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from agents.roles.coder.agent import agent as coder_specialist
from agents.roles.reviewer.agent import agent as reviewer_specialist
from agents.workflows.coding.agent import agent as sdlc_pipeline
from shared.llm import get_model

from . import prompt

root_agent = LlmAgent(
    model=get_model(),
    name="orchestrator",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        AgentTool(agent=sdlc_pipeline),
        AgentTool(agent=coder_specialist),
        AgentTool(agent=reviewer_specialist),
    ],
)
