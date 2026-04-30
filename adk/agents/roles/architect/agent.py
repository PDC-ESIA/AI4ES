from google.adk.agents import LlmAgent

from shared.llm import get_model
from . import prompt, schemas

agent = LlmAgent(
    model=get_model(agent_name="architecture_agent"),
    name="architecture_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    output_schema=schemas.ArchitectureOutput,
    output_key="architecture",
)
