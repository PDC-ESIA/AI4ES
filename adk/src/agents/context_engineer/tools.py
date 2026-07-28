"""Tools do Agente Context Engineer.

Persistência de tasks contextualizadas como JSON no workspace centralizado.
Leitura de artefatos de requisitos e design diretamente do workspace.

"""

import json
import logging

from pydantic import BaseModel, Field, field_validator, ValidationError
from google.adk.tools import FunctionTool

from shared.workspace import get_agent_workspace, get_workspace_root

logger = logging.getLogger(__name__)


class SalvarTaskSchema(BaseModel):
    task_id: str = Field(..., description="ID da task (ex: 'TASK-001')")
    task_json: str = Field(..., description="Conteúdo JSON serializado da task")

    @field_validator("task_id")
    def validar_task_id(cls, v):
        if not v.startswith("TASK-"):
            raise ValueError(f"task_id deve iniciar com 'TASK-'. Recebido: '{v}'")
        return v

class LerWorkspaceFaseSchema(BaseModel):
    fase: str = Field(
        ...,
        description="Fase cujos artefatos serão lidos: 'requirements' ou 'design'"
    )
 
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
        return {"sucesso": False, "erro": "JSON inválido: " + str(e), "caminho": None}

    output_dir = get_agent_workspace("context_engineer")
    output_file = output_dir / (dados.task_id + ".json")
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            json.dumps(task_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("[CONTEXT ENGINEER] Task salva: " + str(output_file.resolve()))
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(output_file.resolve()),
            "task_id": dados.task_id,
        }
    except Exception as e:
        return {"sucesso": False, "erro": "Erro ao salvar task: " + str(e), "caminho": None}

def tool_ler_workspace_fase(fase: str) -> dict:
    """Lê todos os artefatos de uma fase diretamente do workspace.
 
    Deve ser chamada duas vezes antes de gerar qualquer task:
    - fase='requirements': lê RFs, RNFs, HUs e demais artefatos do Time de Requisitos
    - fase='design': lê diagramas, relatórios e análises técnicas do Time de Design
 
    Se a pasta da fase não existir ou estiver vazia, retorna erro e o
    agente deve PARAR — não gerar tasks sem os artefatos necessários.
 
    Args:
        fase (str): Fase cujos artefatos serão lidos: 'requirements' ou 'design'.
 
    Returns:
        dict: sucesso, fase, artefatos lidos com conteúdo, caminho e erros.
    """
    try:
        dados = LerWorkspaceFaseSchema(fase=fase)
    except ValidationError as e:
        return {"sucesso": False, "erro": str(e), "fase": fase, "artefatos": None}
 
    workspace_root = get_workspace_root()
    mapeamento_fases = {
        "requirements": "requirements",
        "design": "design",
    }
    pasta_fase = workspace_root / mapeamento_fases[dados.fase]
 
    if not pasta_fase.exists():
        return {
            "sucesso": False,
            "erro": (
                "Pasta da fase '" + dados.fase + "' não encontrada em: "
                + str(pasta_fase)
                + ". Verifique se a fase anterior concluiu com sucesso."
            ),
            "artefatos": None,
            "caminho_esperado": str(pasta_fase),
        }
 
    arquivos = sorted(
         [
             a
             for a in pasta_fase.rglob("*")
             if a.is_file()
             and a.suffix.lower() in {".md", ".txt", ".json", ".yml", ".yaml", ".mmd", ".mermaid"}
             and not any(part.startswith(".") for part in a.relative_to(pasta_fase).parts)
             and a.stat().st_size <= 500_000
         ],
         key=lambda p: str(p.relative_to(pasta_fase)),
     )
 
    if not arquivos:
        return {
            "sucesso": False,
            "erro": (
                "Pasta da fase '" + dados.fase + "' existe mas está vazia: "
                + str(pasta_fase)
                + ". A fase anterior pode não ter persistido seus artefatos."
            ),
            "artefatos": None,
            "caminho_esperado": str(pasta_fase),
        }
 
    artefatos = []
    erros = []
 
    for arquivo in arquivos:
        try:
            conteudo = arquivo.read_text(encoding="utf-8", errors="replace")
            max_chars = 50_000
            if len(conteudo) > max_chars:
                conteudo = conteudo[:max_chars] + "\n...[TRUNCADO]..."
            artefatos.append({
                "path": str(arquivo.relative_to(workspace_root)),
                "nome": arquivo.name,
                "tipo": arquivo.suffix.lstrip("."),
                "conteudo": conteudo,
            })
            logger.info(
                "[CONTEXT ENGINEER] Artefato lido ["
                + dados.fase + "]: " + str(arquivo)
            )
        except Exception as e:
            erros.append(str(arquivo) + ": " + str(e))
            logger.error(
                "[CONTEXT ENGINEER] Erro ao ler " + str(arquivo) + ": " + str(e)
            )
 
    if erros:
        return {
            "sucesso": False,
            "erro": "Erros ao ler artefatos: " + str(erros),
            "artefatos": artefatos if artefatos else None,
        }
 
    return {
        "sucesso": True,
        "erro": None,
        "fase": dados.fase,
        "artefatos": artefatos,
        "total_lidos": len(artefatos),
        "caminho_pasta": str(pasta_fase),
    }

tool_salvar_task_adk = FunctionTool(tool_salvar_task)
tool_ler_workspace_fase_adk = FunctionTool(tool_ler_workspace_fase)