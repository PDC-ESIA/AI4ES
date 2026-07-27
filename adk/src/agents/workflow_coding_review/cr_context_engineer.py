"""Context Engineer dedicado ao workflow coding_review.

Instância ajustada do context_engineer original (src/agents/context_engineer/):
- Lê artefatos de requisitos e design diretamente do workspace em vez de
  consumir state["requirements"] ou contexto acumulado pelo orchestrator.
- Enriquece cada task com rastreabilidade explicita (requirement_id,
  design_refs) e critérios de aceitação derivados de múltiplas fontes.
- Persiste tasks em workspace_output/coder/tasks/ (consolidado sob coder/).
- Evita conflito de parent com o sdlc_pipeline (instância dedicada).
"""

import json
import logging
import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from pydantic import ValidationError

from shared.workspace import get_agent_workspace
from src.agents.context_engineer import prompt as ce_prompt, schemas as ce_schemas
from src.agents.context_engineer.tools import (
    SalvarTaskSchema,
    tool_ler_workspace_fase_adk,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)


# ---------------------------------------------------------------------------
# Tool wrapper: persiste em coder/tasks/ em vez de tasks/ (canônico)
# ---------------------------------------------------------------------------

def tool_salvar_task_cr(task_id: str, task_json: str) -> dict:
    """Salva task contextualizada em workspace_output/coder/tasks/.

    Mesma lógica do tool_salvar_task canônico, mas escreve no subdir
    consolidado do workflow coding_review.
    """
    try:
        dados = SalvarTaskSchema(task_id=task_id, task_json=task_json)
    except ValidationError as e:
        return {"sucesso": False, "erro": str(e), "caminho": None}

    try:
        task_data = json.loads(dados.task_json)
    except json.JSONDecodeError as e:
        return {"sucesso": False, "erro": "JSON inválido: " + str(e), "caminho": None}

    output_dir = get_agent_workspace("cr_context_engineer")
    output_file = output_dir / (dados.task_id + ".json")
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            json.dumps(task_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("[CR CONTEXT ENGINEER] Task salva: " + str(output_file.resolve()))
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(output_file.resolve()),
            "task_id": dados.task_id,
        }
    except Exception as e:
        return {"sucesso": False, "erro": "Erro ao salvar task: " + str(e), "caminho": None}


tool_salvar_task_cr_adk = FunctionTool(tool_salvar_task_cr)

agent = LlmAgent(
    model=_model,
    name="cr_context_engineer",
    description=ce_prompt.description,
    instruction=ce_prompt.instruction,
    output_key="tasks",
    output_schema=ce_schemas.TasksOutput,
    tools=[
        tool_salvar_task_cr_adk,
        tool_ler_workspace_fase_adk,
    ],
)
