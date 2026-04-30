from google.adk.agents import LlmAgent

from shared.llm import get_model
from . import prompt, schemas

agent = LlmAgent(
    model=get_model(agent_name="test_planning_agent"),
    name="test_planning_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    output_schema=schemas.TestPlanOutput,
    output_key="test_plan",
)
