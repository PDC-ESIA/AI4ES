"""App raiz: orquestrador que delega ao pipeline SDLC ou a agentes pontuais."""

from google.adk.tools.agent_tool import AgentTool

from agents.roles.coder.agent import agent as coder_specialist
from agents.roles.reviewer.agent import agent as reviewer_specialist
from agents.workflows.coding.agent import agent as sdlc_pipeline

from . import prompt
from shared.factory import create_base_agent

root_agent = create_base_agent(
    name="orchestrator",
    prompt_module=prompt,
    tools=[
        AgentTool(agent=sdlc_pipeline),
        AgentTool(agent=coder_specialist),
        AgentTool(agent=reviewer_specialist),
    ],
)
