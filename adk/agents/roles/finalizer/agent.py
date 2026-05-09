from . import prompt, schemas
from shared.factory import create_base_agent

agent = create_base_agent(
    name="finalization_agent",
    prompt_module=prompt,
    output_key="finalization",
    output_schema=schemas.FinalizationOutput,
)
