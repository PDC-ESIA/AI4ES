import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from . import prompt, schemas

_DEFAULT_MODEL = "github_copilot/gpt-4"

agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
    name="test_planner",
    description=prompt.description,
    instruction=prompt.instruction,
    output_schema=schemas.TestPlanOutput,
    output_key="test_plan",
)
