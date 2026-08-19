"""Context Engineer dedicado ao workflow coding_review.

- Lê artefatos de requisitos e design diretamente do workspace.
- Verifica artefatos mínimos obrigatórios e gera Doubt Artifact se ausentes.
- Enriquece cada task com rastreabilidade explícita (requirement_id,
  design_refs) e critérios de aceitação.
- Persiste tasks em workspace_output/coder/tasks/ (consolidado sob coder/).
- Instância dedicada com prompt e schemas próprios, evitando conflito de parent
  no pipeline.
"""

import os

from google.adk.agents import LlmAgent

from shared.tools.coding_tools.context_engineer_tools import (
    tool_salvar_task_cr_adk,
    tool_salvar_macro_context_cr_adk,
    tool_ler_requirements_adk,
    tool_ler_design_adk,
    tool_gerar_doubt_artifact_adk,
)

from . import prompt, schemas

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

agent = LlmAgent(
    model=_model,
    name="cr_context_engineer",
    description=prompt.description,
    instruction=prompt.instruction,
    output_key="tasks",
    output_schema=schemas.TasksOutput,
    tools=[
        tool_salvar_task_cr_adk,
        tool_salvar_macro_context_cr_adk,
        tool_ler_requirements_adk,
        tool_ler_design_adk,
        tool_gerar_doubt_artifact_adk,
    ],
)
