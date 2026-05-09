from . import prompt, schemas
from shared.factory import create_base_agent

agent = create_base_agent(
    name="architecture_agent",
    prompt_module=prompt,
    output_key="architecture",
    output_schema=schemas.ArchitectureOutput,
)
