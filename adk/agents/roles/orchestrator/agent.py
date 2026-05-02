"""App raiz: orquestrador que delega ao pipeline SDLC ou a agentes pontuais."""

from google.adk.tools.agent_tool import AgentTool

from shared.factory import create_agent
from agents.roles.coder.agent import agent as coder_specialist
from agents.roles.reviewer.agent import agent as reviewer_specialist
from agents.workflows.coding.agent import agent as sdlc_pipeline

from . import prompt

root_agent = create_agent(
    name="orchestrator",
    model_key="orchestrator",
    instruction=prompt.instruction,
    description=prompt.description,
    tools=[
        AgentTool(agent=sdlc_pipeline),
        AgentTool(agent=coder_specialist),
        AgentTool(agent=reviewer_specialist),
    ],
)
