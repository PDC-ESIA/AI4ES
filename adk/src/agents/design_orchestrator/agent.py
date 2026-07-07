import os
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

# TODO reimport a pipeline
from src.agents.design_architect.agent import agent as design_architect
from src.agents.mermaid_specialist.agent import agent as mermaid_specialist
from src.agents.markdown_specialist.agent import agent as markdown_specialist
from src.agents.validator.agent import agent as validator
from src.agents.io_agent.agent import agent as io_agent
from . import prompt

_DEFAULT_MODEL = "gemini-2.5-flash"

root_agent = LlmAgent(
    model=os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL),
    name="design_orchestrator",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        #AgentTool(agent=design_pipeline),
        AgentTool(agent=design_architect),
        AgentTool(agent=mermaid_specialist),
        AgentTool(agent=markdown_specialist),
        AgentTool(agent=validator),
        AgentTool(agent=io_agent),
    ],
)