import os

from google.adk.agents import LlmAgent

from . import prompt, schemas

_DEFAULT_MODEL = "gemini-2.5-flash"

agent = LlmAgent(
    model=os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL),
    name="architecture_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    output_schema=schemas.ArchitectureOutput,
    output_key="architecture",
)
