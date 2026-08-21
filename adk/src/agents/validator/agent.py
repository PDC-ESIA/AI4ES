from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import FunctionTool, LongRunningFunctionTool

from shared.agent_factory import create_se_agent
from shared.tools.design_validate.gatekeeper_tool import validate_artifact
from shared.tools.design_hitl_tool import aguardar_decisao_validacao
from src.agents.mermaid_specialist.agent import agent as mermaid_specialist
from src.agents.markdown_specialist.agent import agent as markdown_specialist
from src.agents.io_agent.agent import agent as io_agent
from . import prompt


agent = create_se_agent(
    name="validator",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        AgentTool(agent=mermaid_specialist),
        AgentTool(agent=markdown_specialist),
        AgentTool(agent=io_agent),
        FunctionTool(validate_artifact),
        LongRunningFunctionTool(aguardar_decisao_validacao),
    ],
    agent_subdir="validator",
)
