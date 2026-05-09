from . import prompt
from shared.factory import create_se_agent

agent = create_se_agent(
    name="coder_agent",
    prompt_module=prompt,
    output_key="implementation",
    preset="coder",
)

# ADK CLI busca por `root_agent` ao carregar um app diretamente.
root_agent = agent
