"""
Agente PRD Optimizer
Subtasks 1.1 e 1.2: Fracionamento de PRDs e geração de Context Windows
"""

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from .prompts.prd_optimizer_prompts import (
    prd_optimizer_description,
    prd_optimizer_instruction,
)
from .tools.tools_prd_optimizer import (
    tool_ler_prd_arquivo_adk,
    tool_salvar_context_window_json_adk,
    tool_salvar_context_window_markdown_adk,
    tool_gerar_doubt_artifact_prd_adk,
)

# -------------------------------------------------------------------
# AGENTE PRD OPTIMIZER (root_agent)
# -------------------------------------------------------------------
root_agent = LlmAgent(
    model=LiteLlm("mistral/mistral-medium-latest"),
    name="prd_optimizer_agent",
    description=prd_optimizer_description,
    instruction=prd_optimizer_instruction,
    tools=[
        tool_ler_prd_arquivo_adk,
        tool_salvar_context_window_json_adk,
        tool_salvar_context_window_markdown_adk,
        tool_gerar_doubt_artifact_prd_adk,
    ],
)
