import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from design_agents.shared.tools.date import current_date
from . import prompt

from design_agents.shared.tools.filesystem import (
    save_artifact,
    check_lock,
    release_lock,
    list_versions,
    promote_artifact,
    read_file,
    list_staging_files,
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
        current_date,
        list_staging_files,
    ],
)

root_agent = agent