from . import prompt, schemas
from .tools_requirements import (
    tool_ler_prd_arquivo_adk,
    tool_gerar_doubt_artifact_adk,
    tool_salvar_requisito_adk,
)
from shared.factory import create_base_agent

agent = create_base_agent(
    name="requirements_agent",
    prompt_module=prompt,
    output_key="requirements",
    output_schema=schemas.RequirementsOutput,
    tools=[
        tool_ler_prd_arquivo_adk,
        tool_gerar_doubt_artifact_adk,
        tool_salvar_requisito_adk,
    ],
)
