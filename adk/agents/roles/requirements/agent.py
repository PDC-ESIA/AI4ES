import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool

from shared.tools import run_slicer, registrar_duvida, listar_duvidas_pendentes
from . import prompt, schemas

_DEFAULT_MODEL = "github_copilot/gpt-4"

agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
    name="requirements_analyst",
    description=prompt.description,
    instruction=prompt.instruction,
    output_schema=schemas.AnalystOutput,
    output_key="analysis_result",
    tools=[
        FunctionTool(run_slicer),
        FunctionTool(registrar_duvida),
        FunctionTool(listar_duvidas_pendentes),
    ]
)
