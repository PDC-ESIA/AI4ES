from . import prompt, schemas
from .tools import tool_salvar_task_adk
from shared.factory import create_base_agent

agent = create_base_agent(
    name="context_engineer",
    prompt_module=prompt,
    output_key="tasks",
    output_schema=schemas.TasksOutput,
    tools=[
        tool_salvar_task_adk,
    ],
)
