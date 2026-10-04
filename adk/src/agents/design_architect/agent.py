from google.adk.tools.agent_tool import AgentTool
from google.genai import types

from shared.agent_factory import create_se_agent
from shared.tools.design_hitl_tool import remover_clarificacao_generica
from shared.tools.design_date import current_date
from shared.tools.design_filesystem import (
    save_artifact,
    append_architect_section,
    patch_section,
    list_design_files,
    acquire_lock,
    check_lock,
    release_lock,
    validate_analysis_sections_vinculada,
)
from src.agents.io_agent.agent import agent as io_agent
from . import prompt

agent = create_se_agent(
    name="design_architect",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        AgentTool(agent=io_agent),
        current_date,
        save_artifact,
        append_architect_section,
        patch_section,
        list_design_files,
        acquire_lock,
        check_lock,
        release_lock,
        validate_analysis_sections_vinculada("design_architect"),
    ],
    agent_subdir="design_architect",
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=16384,
    ),
)
remover_clarificacao_generica(agent)
