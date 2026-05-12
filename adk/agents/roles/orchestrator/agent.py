"""App raiz: orquestrador que delega ao pipeline SDLC ou a agentes pontuais."""

import os
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool

from agents.roles.coder.agent import agent as coder_specialist
from agents.roles.reviewer.agent import agent as reviewer_specialist
from agents.workflows.coding.agent import agent as sdlc_pipeline

from shared.tools.filesystem import tool_acessar_workspace

from . import prompt

_DEFAULT_MODEL = "github_copilot/gpt-4"

WORKSPACE_PATH = str(Path(os.environ.get("AI4ES_WORKSPACE", "~/ai4es_workspace")).expanduser().resolve())

root_agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
    name="orchestrator",
    description=prompt.description,
    instruction=prompt.instruction.replace("{WORKSPACE_PATH}", WORKSPACE_PATH),
    tools=[
        AgentTool(agent=sdlc_pipeline),
        AgentTool(agent=coder_specialist),
        AgentTool(agent=reviewer_specialist),
        tool_acessar_workspace
    ],
)
