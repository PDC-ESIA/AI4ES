from google.adk.tools.agent_tool import AgentTool
from google.genai import types

from shared.agent_factory import create_se_agent
from shared.tools.design_date import current_date
from shared.tools.design_filesystem import save_artifact, list_design_files, append_artifact, patch_section
from src.agents.io_agent.agent import agent as io_agent
from . import prompt

agent = create_se_agent(
    name="mermaid_specialist",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        AgentTool(agent=io_agent),
        current_date,
        save_artifact,
        list_design_files,
        append_artifact,
        patch_section
    ],
    agent_subdir="mermaid_specialist",
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=16384,
    ),
)
