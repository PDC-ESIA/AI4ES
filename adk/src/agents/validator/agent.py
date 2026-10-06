from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import FunctionTool, LongRunningFunctionTool

from shared.agent_factory import create_se_agent
from shared.tools.design_validate.gatekeeper_tool import validate_artifact, validate_artifact_file
from shared.tools.design_hitl_tool import aguardar_decisao_validacao, remover_clarificacao_generica
from shared.tools.design_filesystem import (
    save_artifact,
    acquire_lock,
    release_lock,
    list_design_files,
    read_multiple_files,
    read_analysis_sections,
)
from src.agents.mermaid_specialist.agent import agent as mermaid_specialist
from src.agents.io_agent.agent import agent as io_agent
from . import prompt


agent = create_se_agent(
    name="validator",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        AgentTool(agent=mermaid_specialist),
        AgentTool(agent=io_agent),
        FunctionTool(validate_artifact),
        FunctionTool(validate_artifact_file),
        list_design_files,
        read_multiple_files,
        read_analysis_sections,
        LongRunningFunctionTool(aguardar_decisao_validacao),
        acquire_lock,
        save_artifact,
        release_lock,
    ],
    agent_subdir="validator",
)
remover_clarificacao_generica(agent)
