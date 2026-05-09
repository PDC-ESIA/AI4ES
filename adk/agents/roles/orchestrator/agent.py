"""App raiz: orquestrador que delega ao pipeline SDLC ou a agentes pontuais."""

import logging

from google.adk.tools.agent_tool import AgentTool

from agents.roles.coder.agent import agent as coder_specialist
from agents.roles.reviewer.agent import agent as reviewer_specialist
from agents.workflows.coding.agent import agent as sdlc_pipeline

from . import prompt
from shared.factory import create_base_agent, init_workspace

logger = logging.getLogger(__name__)


def _reset_workspace(callback_context):
    """Limpa e recria o workspace no início de cada interação."""
    workspace_root = init_workspace()
    logger.info(f"[ORCHESTRATOR] Workspace reinicializado: {workspace_root}")
    return None


root_agent = create_base_agent(
    name="orchestrator",
    prompt_module=prompt,
    tools=[
        AgentTool(agent=sdlc_pipeline),
        AgentTool(agent=coder_specialist),
        AgentTool(agent=reviewer_specialist),
    ],
)
root_agent.before_agent_callback = _reset_workspace
