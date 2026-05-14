import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from shared.tools.design_date import current_date
from . import prompt

from shared.tools.design_filesystem import (
    save_artifact,
    check_lock,
    release_lock,
    list_versions,
    promote_artifact,
    read_file,
    read_analysis_sections,
    read_multiple_files,
    list_staging_files,
    clear_staging_folder,
    check_active_blocks,
    copy_file,
)

_DEFAULT_MODEL = "github_copilot/gpt-4"

agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
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
        read_analysis_sections,
        read_multiple_files,
        current_date,
        list_staging_files,
        clear_staging_folder,
        check_active_blocks,
        copy_file,
    ],
)

root_agent = agent