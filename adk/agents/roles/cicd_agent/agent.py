"""Agente de CI/CD Pipeline — gera Dockerfile, docker-compose e GitHub Actions."""

from . import prompt, schemas
from .tools import tool_salvar_pipeline_config_adk
from shared.factory import create_se_agent

agent = create_se_agent(
    name="cicd_agent",
    prompt_module=prompt,
    output_key="pipeline",
    output_schema=schemas.PipelineOutput,
    preset="pipeline",
    agent_subdir="pipeline",
    extra_tools=[tool_salvar_pipeline_config_adk],
)
