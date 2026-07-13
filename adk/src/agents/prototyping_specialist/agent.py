from google.adk.tools.agent_tool import AgentTool
from google.genai import types

from shared.agent_factory import create_se_agent
from shared.tools.design_date import current_date
from src.agents.io_agent.agent import agent as io_agent
from . import prompt

agent = create_se_agent(
    name="prototyping_specialist",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        AgentTool(agent=io_agent),
        current_date,
    ],
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=16384,
    ),
)
