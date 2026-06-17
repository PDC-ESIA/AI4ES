"""Context Engineer dedicado ao workflow coding_review.

Instância ajustada do context_engineer original (src/agents/context_engineer/):
- Lê requisitos da mensagem de entrada (contexto acumulado pelo orchestrator)
  em vez de state["requirements"].
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
from src.agents.context_engineer.tools import SalvarTaskSchema

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)


# ---------------------------------------------------------------------------
# Tool wrapper: persiste em coder/tasks/ em vez de tasks/ (canônico)
# ---------------------------------------------------------------------------

def _tool_salvar_task_cr(task_id: str, task_json: str) -> dict:
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
        return {"sucesso": False, "erro": f"JSON inválido: {e}", "caminho": None}

    output_dir = get_agent_workspace("cr_context_engineer")
    output_file = output_dir / f"{dados.task_id}.json"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            json.dumps(task_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(f"[CR CONTEXT ENGINEER] Task salva: {output_file.resolve()}")
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(output_file.resolve()),
            "task_id": dados.task_id,
        }
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro ao salvar task: {e}", "caminho": None}


_tool_salvar_task_cr_adk = FunctionTool(_tool_salvar_task_cr)


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
