import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from shared.tools.design_date import current_date
from shared.tools.design_filesystem import (
    read_file,
    read_multiple_files,
    save_artifact,
    append_artifact,
    patch_section,
    list_staging_files,
    check_active_blocks,
)
from . import prompt

_DEFAULT_MODEL = "github_copilot/gpt-4"

agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
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
        list_staging_files,
        check_active_blocks,
    ],
)