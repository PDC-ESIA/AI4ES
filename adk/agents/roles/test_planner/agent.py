from . import prompt, schemas
from shared.factory import create_base_agent

agent = create_base_agent(
    name="test_planning_agent",
    prompt_module=prompt,
    output_key="test_plan",
    output_schema=schemas.TestPlanOutput,
)
