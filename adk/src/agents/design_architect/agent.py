from google.adk.tools.agent_tool import AgentTool

from shared.agent_factory import create_se_agent
from shared.tools.design_date import current_date
from shared.tools.design_filesystem import save_artifact, list_staging_files
from src.agents.io_agent.agent import agent as io_agent
from . import prompt

agent = create_se_agent(
    name="design_architect",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        AgentTool(agent=io_agent),
        current_date,
        save_artifact,
        list_staging_files,
    ],
    agent_subdir="design_architect",
)
