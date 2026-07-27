"""Context Engineer: transforma requisitos atômicos em Context Windows para o coder.

Portado de feat/me2/coding_squad (Time 4). Phase 2.E: migrado para usar a factory
composta com workspace binding — tool_salvar_task escreve em workspace/tasks/.
"""

from shared.agent_factory import create_se_agent

from . import prompt, schemas
from .tools import tool_salvar_task_adk, tool_ler_workspace_fase_adk

agent = create_se_agent(
    name="context_engineer",
    description=prompt.description,
    instruction=prompt.instruction,
    output_key="tasks",
    output_schema=schemas.TasksOutput,
    tools=[tool_salvar_task_adk, tool_ler_workspace_fase_adk,],
    agent_subdir="context_engineer",
)
