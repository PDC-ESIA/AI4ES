"""
Tools do Agente Context Engineer

Responsabilidades:
- Persistir tasks contextualizadas (Context Windows) como arquivos JSON
  no workspace do projeto.
"""

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, ValidationError
from google.adk.tools import FunctionTool

from shared.factory.workspace import get_workspace_root, AGENT_DIRS

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# SCHEMAS DE VALIDACAO (Pydantic)
# -------------------------------------------------------------------

class SalvarTaskSchema(BaseModel):
    task_id: str = Field(..., description="ID da task (ex: 'TASK-001')")
    task_json: str = Field(..., description="Conteúdo JSON serializado da task")

    @field_validator("task_id")
    def validar_task_id(cls, v):
        if not v.startswith("TASK-"):
            raise ValueError(
                f"task_id deve iniciar com 'TASK-'. Recebido: '{v}'"
            )
        return v


# -------------------------------------------------------------------
# TOOL: Salvar Task no Workspace
# -------------------------------------------------------------------

def tool_salvar_task(task_id: str, task_json: str) -> dict:
    """Salva uma task contextualizada como arquivo JSON no workspace do projeto.

    Persiste o arquivo em: $WORKSPACE_OUTPUT_DIR/tasks/<task_id>.json
    Cria os diretórios automaticamente se não existirem.

    Args:
        task_id (str): Identificador da task (ex: 'TASK-001').
        task_json (str): Conteúdo JSON serializado da task completa.

    Returns:
        dict: Status da operação, caminho do arquivo gerado e erros.
    """
    try:
        dados = SalvarTaskSchema(
            task_id=task_id,
            task_json=task_json,
        )
    except ValidationError as e:
        return {"sucesso": False, "erro": str(e), "caminho": None}

    # Validar que o JSON é válido
    try:
        task_data = json.loads(dados.task_json)
    except json.JSONDecodeError as e:
        return {
            "sucesso": False,
            "erro": f"JSON inválido na task: {e}",
            "caminho": None,
        }

    workspace_root = get_workspace_root()
    output_dir = workspace_root / AGENT_DIRS["context_engineer"]
    output_file = output_dir / f"{dados.task_id}.json"

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            json.dumps(task_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(
            f"[CONTEXT ENGINEER] Task salva: {output_file.resolve()}"
        )
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(output_file.resolve()),
            "task_id": dados.task_id,
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": f"Erro ao salvar task: {e}",
            "caminho": None,
        }


# -------------------------------------------------------------------
# EXPORTANDO TOOLS PARA O ADK
# -------------------------------------------------------------------

tool_salvar_task_adk = FunctionTool(tool_salvar_task)
