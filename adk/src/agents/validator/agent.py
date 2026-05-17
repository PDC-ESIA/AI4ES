import os
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import FunctionTool

from src.agents.mermaid_specialist.agent import agent as mermaid_specialist
from src.agents.markdown_specialist.agent import agent as markdown_specialist
from src.agents.io_agent.agent import agent as io_agent

from shared.tools.design_validate.gatekeeper_tool import validate_artifact
from . import prompt


_DEFAULT_MODEL = "gemini-2.5-flash"

agent = LlmAgent(
    model=os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL),
    name="validator",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        AgentTool(agent=mermaid_specialist),
        AgentTool(agent=markdown_specialist),
        AgentTool(agent=io_agent),
        
        FunctionTool(validate_artifact),
    ],
)