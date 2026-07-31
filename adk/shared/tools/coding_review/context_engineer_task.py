"""Tools de persistência de tasks contextualizadas (Context Engineer).

Duas variantes:
- tool_salvar_task / tool_salvar_task_adk: versão canônica, usada pelo
  agente standalone `context_engineer` — grava em workspace/tasks/.
- _tool_salvar_task_cr / _tool_salvar_task_cr_adk: mesma lógica, usada pelo
  `cr_context_engineer` (workflow_coding_review) — grava no subdir
  consolidado workspace/coder/tasks/.
"""

import json
import logging

from pydantic import BaseModel, Field, field_validator, ValidationError
from google.adk.tools import FunctionTool

from shared.workspace import get_agent_workspace

logger = logging.getLogger(__name__)


class SalvarTaskSchema(BaseModel):
    task_id: str = Field(..., description="ID da task (ex: 'TASK-001')")
    task_json: str = Field(..., description="Conteúdo JSON serializado da task")

    @field_validator("task_id")
    def validar_task_id(cls, v):
        if not v.startswith("TASK-"):
            raise ValueError(f"task_id deve iniciar com 'TASK-'. Recebido: '{v}'")
        return v


def tool_salvar_task(task_id: str, task_json: str) -> dict:
    """Salva uma task contextualizada como JSON em workspace/tasks/.

    Usa get_agent_workspace("context_engineer") — o workspace é resolvido via
    a variável de ambiente WORKSPACE_OUTPUT_DIR (default: ./workspace_output).

    Args:
        task_id (str): Identificador da task (ex: 'TASK-001').
        task_json (str): Conteúdo JSON serializado da task completa.

    Returns:
        dict: {sucesso, erro, caminho, task_id}
    """
    try:
        dados = SalvarTaskSchema(task_id=task_id, task_json=task_json)
    except ValidationError as e:
        return {"sucesso": False, "erro": str(e), "caminho": None}

    try:
        task_data = json.loads(dados.task_json)
    except json.JSONDecodeError as e:
        return {"sucesso": False, "erro": f"JSON inválido: {e}", "caminho": None}

    output_dir = get_agent_workspace("context_engineer")
    output_file = output_dir / f"{dados.task_id}.json"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            json.dumps(task_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(f"[CONTEXT ENGINEER] Task salva: {output_file.resolve()}")
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(output_file.resolve()),
            "task_id": dados.task_id,
        }
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro ao salvar task: {e}", "caminho": None}


tool_salvar_task_adk = FunctionTool(tool_salvar_task)


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
