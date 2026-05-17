"""Tools do Agente Context Engineer.

Persistência de tasks contextualizadas como JSON.

Adaptado de feat/me2/coding_squad (Time 4): sem dependência da factory.
Caminho hardcoded para artefatos/tasks/ relativo ao CWD do uvicorn.
"""

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, ValidationError
from google.adk.tools import FunctionTool

logger = logging.getLogger(__name__)

_TASKS_DIR = Path("artefatos") / "tasks"


class SalvarTaskSchema(BaseModel):
    task_id: str = Field(..., description="ID da task (ex: 'TASK-001')")
    task_json: str = Field(..., description="Conteúdo JSON serializado da task")

    @field_validator("task_id")
    def validar_task_id(cls, v):
        if not v.startswith("TASK-"):
            raise ValueError(f"task_id deve iniciar com 'TASK-'. Recebido: '{v}'")
        return v


def tool_salvar_task(task_id: str, task_json: str) -> dict:
    """Salva uma task contextualizada como arquivo JSON em artefatos/tasks/.

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

    output_file = _TASKS_DIR / f"{dados.task_id}.json"
    try:
        _TASKS_DIR.mkdir(parents=True, exist_ok=True)
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
