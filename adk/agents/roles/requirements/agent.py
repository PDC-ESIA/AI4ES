from google.adk.agents import LlmAgent

from shared.llm import get_model
from . import prompt, schemas

agent = LlmAgent(
    model=get_model(),
    name="requirements_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    output_schema=schemas.RequirementsOutput,
    output_key="requirements",
)
