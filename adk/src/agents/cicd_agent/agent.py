"""Agente de CI/CD Pipeline — gera Dockerfile, docker-compose e GitHub Actions."""

from google.adk.tools import FunctionTool

from shared.agent_factory import create_se_agent
from . import prompt, schemas
from .tools import tool_salvar_pipeline_config_adk

agent = create_se_agent(
    name="cicd_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    output_key="pipeline",
    output_schema=schemas.PipelineOutput,
    agent_subdir="pipeline",
    tools=[tool_salvar_pipeline_config_adk],
)
