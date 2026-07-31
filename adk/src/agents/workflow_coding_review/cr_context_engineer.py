"""Context Engineer dedicado ao workflow coding_review.

Instância ajustada do context_engineer original (src/agents/context_engineer/):
- Lê requisitos da mensagem de entrada (contexto acumulado pelo orchestrator)
  em vez de state["requirements"].
- Persiste tasks em workspace_output/coder/tasks/ (consolidado sob coder/).
- Evita conflito de parent com o sdlc_pipeline (instância dedicada).
"""

import os

from google.adk.agents import LlmAgent

from shared.tools.coding_review.context_engineer_task import _tool_salvar_task_cr_adk
from src.agents.context_engineer import prompt as ce_prompt, schemas as ce_schemas

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)


# ---------------------------------------------------------------------------
# Prompt: seção ENTRADA ajustada para ler da mensagem de entrada
# ---------------------------------------------------------------------------

_INSTRUCTION = ce_prompt.instruction.replace(
    "Você receberá os requisitos atômicos do agente anterior via state[\"requirements\"].\n"
    "Cada requisito contém: id, description e acceptance_criteria.\n\n"
    "Se a entrada estiver vazia ou ausente, retorne um erro claro e encerre.",
    "Você receberá os requisitos como parte da mensagem de entrada (contexto das\n"
    "fases anteriores do pipeline). Extraia os requisitos atômicos do texto recebido.\n"
    "Cada requisito contém: id, description e acceptance_criteria.\n\n"
    "Se a entrada estiver vazia ou não contiver requisitos identificáveis, retorne\n"
    "um erro claro e encerre.",
)

agent = LlmAgent(
    model=_model,
    name="cr_context_engineer",
    description=ce_prompt.description,
    instruction=_INSTRUCTION,
    output_key="tasks",
    output_schema=ce_schemas.TasksOutput,
    tools=[_tool_salvar_task_cr_adk],
)
