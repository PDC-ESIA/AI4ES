import os
from google.adk.agents import LlmAgent
from shared.tools.design_date import current_date
from . import prompt

from shared.tools.design_filesystem import (
    save_artifact,
    check_lock,
    release_lock,
    list_versions,
    promote_artifact,
    read_file,
    list_staging_files,
    clear_staging_folder,
    check_active_blocks,
)

_DEFAULT_MODEL = "gemini-2.5-flash"

agent = LlmAgent(
    model=os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL),
    name="io_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        save_artifact,
        check_lock,
        release_lock,
        list_versions,
        promote_artifact,
        read_file,
        current_date,
        list_staging_files,
        clear_staging_folder,
        check_active_blocks,
    ],
)

root_agent = agent