from . import prompt
from shared.factory import create_se_agent

agent = create_se_agent(
    name="review_agent",
    prompt_module=prompt,
    output_key="review",
    preset="reviewer",
)

# ADK CLI busca por `root_agent` ao carregar um app diretamente.
root_agent = agent
