"""Workflow coding_review: pipeline enxuto de codificação com revisão.

Instancia agentes dedicados (mesmo prompt/tools dos roles) para evitar
conflito de parent com o sdlc_pipeline.
"""

import os

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool

from src.agents.requirements import prompt as req_prompt
from src.agents.requirements import schemas as req_schemas
from src.agents.coder import prompt as coder_prompt
from src.agents.reviewer import prompt as reviewer_prompt
from shared.tools import (
    tool_criar_arquivo,
    tool_git_add,
    tool_git_commit,
    tool_git_checkout,
    tool_ler_arquivo,
    tool_substituir_trecho,
    tool_ler_diff,
    tool_salvar_relatorio,
    gerar_doubt_artifact,
)

# NOTA: as tools originais `tool_ler_prd_arquivo_adk` e `tool_gerar_doubt_artifact_adk`
# viviam em adk/agents/roles/requirements/tools_requirements.py e foram removidas na
# consolidacao com Time 1 (refatoracao da arquitetura de requisitos).
# Substituicao funcional: tool_ler_arquivo (leitura generica) + gerar_doubt_artifact
# (geracao de doubt artifact via shared.tools). Donos podem refinar se preciso.

_DEFAULT_MODEL = "github_copilot/gpt-4"
_model = LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL))

_requirements = LlmAgent(
    model=_model,
    name="cr_requirements_agent",
    description=req_prompt.description,
    instruction=req_prompt.instruction,
    output_schema=req_schemas.AnalystOutput,
    output_key="requirements",
    tools=[FunctionTool(tool_ler_arquivo), FunctionTool(gerar_doubt_artifact)],
)

_coder = LlmAgent(
    model=_model,
    name="cr_coder_agent",
    description=coder_prompt.description,
    instruction=coder_prompt.instruction,
    output_key="implementation",
    tools=[
        FunctionTool(tool_criar_arquivo),
        FunctionTool(tool_git_add),
        FunctionTool(tool_git_commit, require_confirmation=True),
        FunctionTool(tool_git_checkout),
        FunctionTool(tool_ler_arquivo),
        FunctionTool(tool_substituir_trecho),
    ],
)

_reviewer = LlmAgent(
    model=_model,
    name="cr_review_agent",
    description=reviewer_prompt.description,
    instruction=reviewer_prompt.instruction,
    output_key="review",
    tools=[
        FunctionTool(tool_ler_diff),
        FunctionTool(tool_salvar_relatorio),
    ],
)

agent = SequentialAgent(
    name="coding_review_pipeline",
    description=(
        "Pipeline enxuto de codificação com revisão: "
        "requisitos → codificação → revisão."
    ),
    sub_agents=[_requirements, _coder, _reviewer],
)
