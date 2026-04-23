import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool

from shared.tools import (
    run_slicer, 
    ler_chunk, 
    gerar_doubt_artifact, 
    listar_duvidas_pendentes,
    tool_salvar_artefato_requisito
)
from . import prompt, schemas

_DEFAULT_MODEL = os.environ.get("ADK_LLM_MODEL", "github_copilot/gpt-4")

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
    ]
)
