import os
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from src.agents.io_agent.agent import agent as io_agent
from shared.tools.design_date import current_date
from shared.tools.design_filesystem import save_artifact, list_staging_files
from . import prompt

_DEFAULT_MODEL = "gemini-2.5-flash"

agent = LlmAgent(
    model=os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL),
    name="design_architect",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        AgentTool(agent=io_agent),
        current_date,
        save_artifact,
        list_staging_files,
    ],
)