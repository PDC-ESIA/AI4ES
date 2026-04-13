import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from shared.tools.filesystem import (
    save_artifact,
    check_lock,
    release_lock,
    list_versions,
    promote_artifact,
)
from . import prompt_complexa

_DEFAULT_MODEL = "github_copilot/gpt-4"

agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
    name="io_agent",
    description=prompt_complexa.description,
    instruction=prompt_complexa.instruction,
    tools=[
        save_artifact,
        check_lock,
        release_lock,
        list_versions,
        promote_artifact,
    ],
)
root_agent = agent