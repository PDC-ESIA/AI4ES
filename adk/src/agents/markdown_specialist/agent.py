from google.adk.tools.agent_tool import AgentTool
from google.genai import types

from shared.agent_factory import create_se_agent
from shared.tools.design_date import current_date
from shared.tools.design_filesystem import (
    save_artifact,
    list_design_files,
    read_file,
    read_multiple_files,
    append_artifact,
    patch_section,
    check_active_blocks,
    acquire_lock,
    check_lock,
    release_lock,
)
from src.agents.io_agent.agent import agent as io_agent
from . import prompt

agent = create_se_agent(
    name="markdown_specialist",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        current_date,
        read_file,
        read_multiple_files,
        save_artifact,
        append_artifact,
        patch_section,
        list_design_files,
        check_active_blocks,
        acquire_lock,
        check_lock,
        release_lock,
    ],
    agent_subdir="markdown_specialist",
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=16384,
    ),
)
