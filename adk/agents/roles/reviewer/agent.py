from shared.factory import create_agent
from . import prompt

agent = create_agent(
    name="review_agent",
    model_key="review_agent",
    instruction=prompt.instruction,
    description=prompt.description,
    capabilities=["reporting"],
    output_key="review",
)

# ADK CLI busca por `root_agent` ao carregar um app diretamente.
root_agent = agent
