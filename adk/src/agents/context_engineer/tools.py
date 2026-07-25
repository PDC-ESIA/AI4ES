"""Tools do Agente Context Engineer.

Persistência de tasks contextualizadas como JSON no workspace centralizado.

Leitura de artefatos de requisitos e design a partir dos paths informafos pelo manifesto de cada fase.
"""

import json
import logging
from pathlib import Path

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

class LerArtefatosManifestoSchema(BaseModel):
    paths: list[str] = Field(
        ...,
        description=(
            "Lista de paths individuais dos artefatos informados pelo manifesto da fase anterior. Cada path aponta para um arquivo especifico no workspace."
        )
    )
    fase: str = Field(
        ...,
        description="Fase de origem dos artefatos: 'requirements' ou 'design'"
    )
 
    @field_validator("paths")
    def validar_paths(cls, v):
        if not v:
            raise ValueError("A lista de paths não pode estar vazia.")
        return v
 
    @field_validator("fase")
    def validar_fase(cls, v):
        fases_validas = ("requirements", "design")
        if v not in fases_validas:
            raise ValueError(
                "fase deve ser uma de: " + str(fases_validas) + ". Recebido: " + v
            )
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

def tool_ler_artefatos_manifesto(paths: list[str], fase: str) -> dict:
    """Lê os artefatos de uma fase à partir dos paths individuais do manifesto.
 
    Deve ser chamada duas vezes antes de gerar qualquer task:
    - fase='requirements': lê HUs, RFs, RNFs, casos de uso, regras de negócio
    - fase='design': lê diagramas mermaid, relatórios e análises técnicas por HU
 
    Se qualquer path não existir no disco, a tool retorna erro e o agente
    deve PARAR — nao gerar tasks sem todos os artefatos necessários.
 
    Args:
        paths (list[str]): Paths individuais dos artefatos informados pelo manifesto.
        fase (str): Fase de origem: 'requirements' ou 'design'.
 
    Returns:
        dict: sucesso, fase, artefatos lidos com conteúdo, paths não encontrados.
    """
    try:
        dados = LerArtefatosManifestoSchema(paths=paths, fase=fase)
    except ValidationError as e:
        return {"sucesso": False, "erro": str(e), "artefatos": None}
 
    artefatos = []
    paths_nao_encontrados = []
 
    for path_str in dados.paths:
        path = Path(path_str)
 
        if not path.exists():
            paths_nao_encontrados.append(path_str)
            logger.error(
                "[CONTEXT ENGINEER] Artefato não encontrado ["
                + dados.fase + "]: " + path_str
            )
            continue
 
        try:
            conteudo = path.read_text(encoding="utf-8")
            artefatos.append({
                "path": path_str,
                "tipo": path.suffix.lstrip("."),
                "nome": path.name,
                "fase": dados.fase,
                "conteúdo": conteudo,
            })
            logger.info(
                "[CONTEXT ENGINEER] Artefato lido ["
                + dados.fase + "]: " + path_str
            )
        except Exception as e:
            paths_nao_encontrados.append(path_str)
            logger.error(
                "[CONTEXT ENGINEER] Erro ao ler ["
                + dados.fase + "] " + path_str + ": " + str(e)
            )
 
    if paths_nao_encontrados:
        return {
            "sucesso": False,
            "erro": (
                "Os seguintes artefatos da fase '" + dados.fase
                + "' não foram encontrados ou não puderam ser lidos: "
                + str(paths_nao_encontrados)
                + ". Verifique se a fase anterior concluiu corretamente."
            ),
            "artefatos": None,
            "paths_não_encontrados": paths_nao_encontrados,
        }
 
    return {
        "sucesso": True,
        "erro": None,
        "fase": dados.fase,
        "artefátos": artefatos,
        "total_lidos": len(artefatos),
    }

tool_salvar_task_adk = FunctionTool(tool_salvar_task)
tool_ler_artefatos_manifesto_adk = FunctionTool(tool_ler_artefatos_manifesto)