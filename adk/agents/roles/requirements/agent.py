import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool

from shared.tools import (
    run_slicer,
    ler_chunk,
    extract_text,
    gerar_doubt_artifact,
    listar_duvidas_pendentes,
    tool_salvar_artefato_requisito,
    run_search,
    check_glossary,
    add_to_glossary,
    build_skill_toolset,
)
from .skills.hu_skill import hu_skill
from .skills.rf_skill import rf_skill
from .skills.rnf_skill import rnf_skill
from .skills.rn_skill import rn_skill
from .skills.uc_skill import uc_skill
from . import prompt

_DEFAULT_MODEL = os.environ.get("ADK_LLM_MODEL", "github_copilot/gpt-4")

artefatos_toolset = build_skill_toolset(
    [hu_skill, rf_skill, rnf_skill, rn_skill, uc_skill]
)
# ── Sub-Agente de Glossário ──────────────────────────────────────────────────
glossario_agent = LlmAgent(
    name="glossario_agent",
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", "github_copilot/gpt-4o")),
    description=prompt.glossario_description,
    instruction=prompt.glossario_instruction,
    tools=[
        FunctionTool(extract_text),
        FunctionTool(run_slicer),
        FunctionTool(run_search),
        FunctionTool(add_to_glossary),
        FunctionTool(check_glossary),
        FunctionTool(gerar_doubt_artifact),
    ],
)
# ── Agente Principal de Requisitos ───────────────────────────────────────────
root_agent = LlmAgent(
    model=LiteLlm(_DEFAULT_MODEL),
    name="requirements_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    output_key="analysis_result",
    tools=[
        artefatos_toolset,
        FunctionTool(run_slicer),
        FunctionTool(ler_chunk),
        FunctionTool(gerar_doubt_artifact),
        FunctionTool(tool_salvar_artefato_requisito),
        AgentTool(agent=glossario_agent),
    ],
)

agent = root_agent
