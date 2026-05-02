from shared.factory import create_agent
from . import prompt

agent = create_agent(
    name="coder_agent",
    model_key="coder_agent",
    instruction=prompt.instruction,
    description=prompt.description,
    capabilities=["filesystem", "git"],
    output_key="implementation",
)

# ADK CLI busca por `root_agent` ao carregar um app diretamente.
root_agent = agent
