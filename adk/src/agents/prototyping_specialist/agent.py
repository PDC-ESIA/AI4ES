from google.adk.tools.agent_tool import AgentTool
from google.genai import types

from shared.agent_factory import create_se_agent
from shared.tools.design_hitl_tool import remover_clarificacao_generica
from shared.tools.design_date import current_date
from shared.tools.design_filesystem import (
    save_artifact,
    acquire_lock,
    release_lock,
    list_design_files,
    read_analysis_sections,
    read_multiple_files,
)
from src.agents.io_agent.agent import agent as io_agent
from . import prompt

agent = create_se_agent(
    name="prototyping_specialist",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        AgentTool(agent=io_agent),
        current_date,
        # Leitura e gravação diretas: antes cada HTML/CSS era gerado duas vezes
        # (pelo especialista e de novo pelo io_agent ao salvar).
        list_design_files,
        read_analysis_sections,
        read_multiple_files,
        acquire_lock,
        save_artifact,
        release_lock,
    ],
    # "design" (e não o nome do agente): prototyping_specialist não está em
    # AGENT_DIRS; com o nome dele, as escritas iriam para
    # <workspace>/prototyping_specialist/ em vez de <workspace>/design/.
    agent_subdir="design",
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=16384,
    ),
)
remover_clarificacao_generica(agent)
