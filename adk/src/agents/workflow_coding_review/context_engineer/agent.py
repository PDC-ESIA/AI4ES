"""Context Engineer dedicado ao workflow coding_review.

- Consome o manifesto de requirements repassado pelo orquestrador via texto
  do prompt, seguindo o mesmo padrão do workflow_qa.
- Lê artefatos de design diretamente do workspace (fallback enquanto o
  Time 2 não produz manifesto).
- Verifica status do manifesto e pausa via HITL (aguardar_resolucao_bloqueio)
  se bloqueado, impedindo o avanço para o coder.
- Enriquece cada task com rastreabilidade explícita (requirement_id, design_refs)
  e critérios de aceitação derivados de múltiplas fontes.
- Persiste tasks em workspace_output/coder/tasks/.
"""

import json
import os
from typing import Any
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from shared.tools.coding_tools.context_engineer_tools import (
    tool_salvar_task_cr_adk,
    tool_salvar_macro_context_cr_adk,
    tool_ler_requirements_adk,
    tool_ler_design_adk,
    tool_gerar_doubt_artifact_adk,
    tool_emitir_manifesto_bloqueado_adk,
    tool_aguardar_resolucao_bloqueio_adk,
)

from . import prompt

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

def _parse_tasks_output(callback_context: CallbackContext) -> None:
    tasks_raw = callback_context.state.get("tasks")
    if isinstance(tasks_raw, str):
        try:
            callback_context.state["tasks"] = json.loads(tasks_raw)
        except (json.JSONDecodeError, ValueError):
            pass


agent = LlmAgent(
    model=_model,
    name="cr_context_engineer",
    description=prompt.description,
    instruction=prompt.instruction,
    output_key="tasks",
    after_agent_callback=_parse_tasks_output,
    tools=[
        tool_salvar_task_cr_adk,
        tool_salvar_macro_context_cr_adk,
        tool_ler_requirements_adk,
        tool_ler_design_adk,
        tool_gerar_doubt_artifact_adk,
        tool_emitir_manifesto_bloqueado_adk,
        tool_aguardar_resolucao_bloqueio_adk,
    ],
)
