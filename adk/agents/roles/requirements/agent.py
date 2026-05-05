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
)
from . import prompt, schemas

_DEFAULT_MODEL = os.environ.get("ADK_LLM_MODEL", "github_copilot/gpt-4")

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

agent = LlmAgent(
    model=LiteLlm(_DEFAULT_MODEL),
    name="requirements_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    output_key="analysis_result",
    tools=[
        FunctionTool(run_slicer),
        FunctionTool(ler_chunk),
        FunctionTool(gerar_doubt_artifact),
        FunctionTool(tool_salvar_artefato_requisito),
        AgentTool(agent=glossario_agent),
    ],
)
