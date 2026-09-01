"""Tools do Agente Context Engineer.

Persistência de tasks contextualizadas como JSON no workspace:
  - tool_salvar_task    → workspace_output/tasks/ (canônico)
  - tool_salvar_task_cr → workspace_output/coder/tasks/ (workflow coding_review)
Leitura de artefatos das fases anteriores via tool_ler_artefatos — única tool
para requirements e design, com suporte a leitura via paths do manifesto ou
fallback direto no workspace.
Geração de Doubt Artifact e pausa HITL em caso de bloqueio.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, ValidationError
from google.adk.tools import FunctionTool, LongRunningFunctionTool, ToolContext

from shared.workspace import get_agent_workspace, get_workspace_root

logger = logging.getLogger(__name__)

EXTENSOES_TEXTUAIS = {".md", ".txt", ".json", ".yml", ".yaml", ".mmd", ".mermaid"}
TAMANHO_MAXIMO = 500_000


class SalvarTaskSchema(BaseModel):
    task_id: str = Field(..., description="ID da task (ex: 'TASK-001')")
    task_json: str = Field(..., description="Conteúdo JSON serializado da task")

    @field_validator("task_id")
    def validar_task_id(cls, v):
        if not v.startswith("TASK-"):
            raise ValueError("task_id deve iniciar com 'TASK-'. Recebido: " + v)
        return v

class DoubtArtifactSchema(BaseModel):
    titulo: str = Field(..., description="Título curto do bloqueio encontrado")
    fase_bloqueada: str = Field(..., description="Fase que causou o bloqueio: 'requirements' ou 'design'")
    descricao: str = Field(..., description="Descrição detalhada do problema")
    acao_necessaria: str = Field(..., description="O que precisa ser feito para desbloquear")
    nome_arquivo: str = Field(default="Doubt_Artifact_context_engineer.md")
 
    @field_validator("nome_arquivo")
    def validar_extensao(cls, v):
        if not v.endswith(".md"):
            raise ValueError("O Doubt Artifact deve ser um arquivo .md.")
        return v

def _ler_arquivo(path: Path, workspace_root: Path) -> Optional[dict]:
    """Lê um arquivo do workspace e retorna seu conteúdo como dicionário."""
    if not path.exists() or not path.is_file():
        return None
    try:
        conteudo = path.read_text(encoding="utf-8", errors="replace")
        return {
            "path": str(path.relative_to(workspace_root)).replace("\\", "/"),
            "nome": path.name,
            "tipo": path.suffix.lstrip("."),
            "conteudo": conteudo,
        }
    except Exception as e:
        logger.error("[CONTEXT ENGINEER] Erro ao ler " + str(path) + ": " + str(e))
        return None


def _ler_pasta_workspace(pasta_fase: Path, workspace_root: Path, nome_fase: str) -> dict:
    """Lê todos os arquivos textuais de uma pasta do workspace.
 
    Verifica existência, filtra por extensões textuais, ignora ocultos
    e limita tamanho por arquivo.
    """
    if not pasta_fase.exists() or not pasta_fase.is_dir():
        return {
            "sucesso": False,
            "fase": nome_fase,
            "erro": (
                "Pasta '" + nome_fase + "' não encontrada: "
                + str(pasta_fase)
                + ". Verifique se a fase anterior concluiu com sucesso."
            ),
            "artefatos": None,
            "total_lidos": 0,
            "caminho_esperado": str(pasta_fase),
        }
 
    arquivos = []
    for a in pasta_fase.rglob("*"):
        if not a.is_file():
            continue
        if a.suffix.lower() not in EXTENSOES_TEXTUAIS:
            continue
        if any(part.startswith(".") for part in a.relative_to(pasta_fase).parts):
            continue
        try:
            if a.stat().st_size > TAMANHO_MAXIMO:
                continue
        except OSError as e:
            logger.warning(
                "[CONTEXT ENGINEER] Ignorando arquivo inacessível: "
                + str(a)
                + " ("
                + str(e)
                + ")"
            )
            continue
        arquivos.append(a)

    arquivos = sorted(arquivos, key=lambda p: str(p.relative_to(pasta_fase)))
 
    if not arquivos:
        return {
            "sucesso": False,
            "fase": nome_fase,
            "erro": (
                "Pasta '" + nome_fase + "' existe mas está vazia: "
                + str(pasta_fase)
                + ". A fase anterior pode não ter persistido seus artefatos."
            ),
            "artefatos": None,
            "total_lidos": 0,
            "caminho_esperado": str(pasta_fase),
        }
 
    artefatos = []
    erros = []
 
    for arquivo in arquivos:
        try:
            conteudo = arquivo.read_text(encoding="utf-8", errors="replace")
            if len(conteudo) > 50_000:
                conteudo = conteudo[:50_000] + "\n...[TRUNCADO]..."
            artefatos.append({
                "path": str(arquivo.relative_to(workspace_root)).replace("\\", "/"),
                "nome": arquivo.name,
                "tipo": arquivo.suffix.lstrip("."),
                "tipo_manifesto": "",
                "conteudo": conteudo,
            })
            logger.info("[CONTEXT ENGINEER] Artefato lido [" + nome_fase + "]: " + str(arquivo))
        except Exception as e:
            erros.append(str(arquivo) + ": " + str(e))
            logger.error("[CONTEXT ENGINEER] Erro ao ler " + str(arquivo) + ": " + str(e))
 
    if erros:
        return {
            "sucesso": False,
            "fase": nome_fase,
            "erro": "Erros ao ler artefatos: " + str(erros),
            "artefatos": artefatos if artefatos else None,
            "total_lidos": len(artefatos),
            "caminho_pasta": str(pasta_fase),
        }
 
    return {
        "sucesso": True,
        "erro": None,
        "fase": nome_fase,
        "artefatos": artefatos,
        "total_lidos": len(artefatos),
        "caminho_pasta": str(pasta_fase),
    }

def tool_ler_artefatos(
    paths_json: str,
    fase: str,
    pasta_fallback: str = "",
) -> dict:
    """Lê artefatos de uma fase via paths do manifesto ou fallback no workspace.
 
    Dois caminhos de leitura:
    1. Manifesto presente (paths_json não vazio): lê os arquivos pelos paths
       extraídos do manifesto repassado pelo orquestrador no contexto acumulado.
    2. Manifesto ausente (paths_json vazio ou "[]"): fallback de leitura direta
       da pasta da fase no workspace (pasta_fallback).
 
    Nenhuma validação por nome de arquivo ou tipo é feita — todos os artefatos
    são retornados com conteúdo completo e o campo tipo_manifesto para que o LLM
    classifique semanticamente o que cada um representa.
 
    Args:
        paths_json (str): JSON serializado com lista de paths dos artefatos
                          extraídos do manifesto. Use "[]" para acionar o fallback.
                          Formato: ["requirements/HUs/HU-001.md", ...]
        fase (str): Nome da fase para logs e retorno (ex: "requirements", "design").
        pasta_fallback (str): Pasta relativa ao workspace root para leitura direta
                              quando paths_json estiver vazio (ex: "workspace_output/requirements",
                              "workspace_output/design").
 
    Returns:
        dict: sucesso, fase, artefatos (com path, nome, tipo_manifesto, conteudo),
              total_lidos, fallback e erros.
    """
    workspace_root = get_workspace_root()
 
    # --- Caminho 1: leitura via paths do manifesto ---
    try:
        paths_list = json.loads(paths_json) if paths_json else []
    except json.JSONDecodeError as e:
        return {
            "sucesso": False,
            "fase": fase,
            "erro": "paths_json inválido — JSON malformado: " + str(e),
            "artefatos": None,
            "total_lidos": 0,
            "fallback": False,
        }
 
    if paths_list:
        artefatos = []
        erros = []
 
        for item in paths_list:
            if isinstance(item, dict):
                path_rel = str(item.get("path", "")).replace("\\", "/")
                if path_rel.startswith("workspace_output/"):
                    path_rel = path_rel[len("workspace_output/"):]
                tipo_manifesto = item.get("tipo", "")
            else:
                path_rel = str(item).replace("\\", "/")
                if path_rel.startswith("workspace_output/"):
                    path_rel = path_rel[len("workspace_output/"):]
                tipo_manifesto = ""
 
            rel_path = Path(path_rel)
            if rel_path.is_absolute() or ".." in rel_path.parts:
                erros.append("Path inválido: " + path_rel)
                logger.warning("[CONTEXT ENGINEER] Path inválido: " + path_rel)
                continue
 
            path_abs = workspace_root / rel_path
            conteudo = _ler_arquivo(path_abs, workspace_root)
            if conteudo:
                conteudo["tipo_manifesto"] = tipo_manifesto
                artefatos.append(conteudo)
            else:
                erros.append("Arquivo não encontrado: " + path_rel)
                logger.warning("[CONTEXT ENGINEER] Artefato ausente: " + path_rel)
 
        return {
            "sucesso": True,
            "fase": fase,
            "erro": None,
            "artefatos": artefatos,
            "total_lidos": len(artefatos),
            "erros_leitura": erros if erros else None,
            "fallback": False,
        }
 
    # --- Caminho 2: fallback de leitura direta do workspace ---
    if not pasta_fallback:
        return {
            "sucesso": False,
            "fase": fase,
            "erro": (
                "Nenhum path fornecido e pasta_fallback não definida. "
                "Forneça paths_json ou pasta_fallback para leitura direta."
            ),
            "artefatos": None,
            "total_lidos": 0,
            "fallback": True,
        }
 
    pasta_fase = workspace_root / pasta_fallback
    resultado = _ler_pasta_workspace(pasta_fase, workspace_root, fase)
    resultado["fallback"] = True
    return resultado
 
def tool_gerar_doubt_artifact(
    titulo: str,
    fase_bloqueada: str,
    descricao: str,
    acao_necessaria: str,
    nome_arquivo: str = "Doubt_Artifact_context_engineer.md",
    subdir: str = "",
) -> dict:
    """Gera um Doubt Artifact ao detectar bloqueio.
 
    Use quando o LLM determinar que não há conteúdo suficiente para gerar tasks
    de codificação com qualidade. O bloqueio é por ausência de CONTEÚDO,
    nunca por nome de arquivo ou nomenclatura.
 
    Após chamar esta tool, chame tool_emitir_manifesto_bloqueado e
    aguardar_resolucao_bloqueio. Não gere nenhuma task.
    """
    try:
        dados = DoubtArtifactSchema(
            titulo=titulo,
            fase_bloqueada=fase_bloqueada,
            descricao=descricao,
            acao_necessaria=acao_necessaria,
            nome_arquivo=nome_arquivo,
        )
    except ValidationError as e:
        return {"sucesso": False, "erro": str(e), "caminho": None}

    if subdir:
        subdir_path = Path(subdir)
        if subdir_path.is_absolute() or ".." in subdir_path.parts:
            return {
                "sucesso": False,
                "erro": "subdir inválido: " + subdir,
                "caminho": None,
            }
 
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 
    conteudo = (
        "# Doubt Artifact — " + dados.titulo + "\n"
        "\n"
        "> EXECUÇÃO PAUSADA — INTERVENÇÃO NECESSÁRIA\n"
        "> Gerado pelo context_engineer em " + timestamp + "\n"
        "\n"
        "---\n"
        "\n"
        "## Fase Bloqueada\n"
        "**" + dados.fase_bloqueada + "**\n"
        "\n"
        "## Descrição do Problema\n"
        + dados.descricao + "\n"
        "\n"
        "## Ação Necessária\n"
        + dados.acao_necessaria + "\n"
        "\n"
        "---\n"
        "\n"
        "## Checklist de Resolução\n"
        "- [ ] Fase '" + dados.fase_bloqueada + "' reprocessada com os artefatos corretos\n"
        "- [ ] Artefatos mínimos presentes no workspace\n"
        "- [ ] Pipeline pode ser reiniciado\n"
        "\n"
        "Status: Pendente\n"
    )
 
    workspace_root = get_workspace_root()
    pasta_destino = workspace_root / subdir if subdir else workspace_root
    path = pasta_destino / dados.nome_arquivo
 
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(conteudo, encoding="utf-8")
        logger.warning(
            "[CONTEXT ENGINEER] Doubt Artifact gerado: "
            + dados.titulo)
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(path.resolve()),
            "titulo": dados.titulo,
            "fase_bloqueada": dados.fase_bloqueada,
            "status": "EXECUÇÃO PAUSADA — aguardando resolução",
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": "Erro ao salvar Doubt Artifact: " + str(e),
            "caminho": None,
        }

def tool_emitir_manifesto_bloqueado(
    motivo: str,
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """Emite manifesto com status=blocked no state e em disco.

    Use após tool_gerar_doubt_artifact e antes de aguardar_resolucao_bloqueio.
    Garante que o manifesto seja gravado no state mesmo com pipeline pausado.
    """
    from src.agents.workflow_coding_review.manifest import (
        PHASE_NAME,
        STATE_KEY,
        _scan_artifacts,
        _scan_doubts,
    )

    ws_root = get_workspace_root()
    coder_ws = get_agent_workspace("coder")

    artifacts = _scan_artifacts(coder_ws, ws_root)
    doubts = _scan_doubts(coder_ws, ws_root)

    if not any(d.get("bloqueante") for d in doubts):
        synthetic_path = coder_ws / "Doubt_Artifact_manifesto_bloqueado.md"
        synthetic_path.parent.mkdir(parents=True, exist_ok=True)
        synthetic_path.write_text(
            "# Doubt Artifact — Bloqueio do context_engineer\n\n"
            "> EXECUÇÃO PAUSADA — INTERVENÇÃO NECESSÁRIA\n\n"
            "## Fase Bloqueada\n**coding**\n\n"
            "## Descrição do Problema\n" + motivo + "\n\n"
            "## Ação Necessária\n"
            "Resolver o bloqueio e reprocessar a fase.\n\n"
            "**Bloqueante:** Sim\n",
            encoding="utf-8",
        )
        doubts = _scan_doubts(coder_ws, ws_root)

    manifest: dict = {
        "phase":     PHASE_NAME,
        "status":    "blocked",
        "artifacts": artifacts,
        "doubts":    doubts,
        "summary":   motivo,
    }

    if tool_context is not None:
        tool_context.state[STATE_KEY] = manifest
        manifests = list(tool_context.state.get("phase_manifests", []) or [])
        manifests.append(manifest)
        tool_context.state["phase_manifests"] = manifests

    manifest_path = coder_ws / "manifest.json"
    try:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        logger.info(
            "[CONTEXT ENGINEER] Manifesto bloqueado emitido: " + str(manifest_path)
        )
        return {
            "sucesso": True,
            "status": "blocked",
            "caminho": str(manifest_path.resolve()),
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": "Erro ao emitir manifesto bloqueado: " + str(e),
            "caminho": None,
        }


async def aguardar_resolucao_bloqueio(
    fase_bloqueada: str,
    motivo: str,
    acao_necessaria: str,
) -> Optional[dict[str, Any]]:
    """Pausa o pipeline até que o bloqueio seja resolvido.

    Use APÓS tool_emitir_manifesto_bloqueado. O ADK interpreta retorno
    None como função pendente, pausando o SequentialAgent e impedindo
    o avanço para o coder.
    """
    _ = (fase_bloqueada, motivo, acao_necessaria)
    return None

def tool_salvar_task_cr(task_id: str, task_json: str) -> dict:
    """Salva task contextualizada em workspace_output/coder/tasks/.
    """
    try:
        dados = SalvarTaskSchema(task_id=task_id, task_json=task_json)
    except ValidationError as e:
        return {"sucesso": False, "erro": str(e), "caminho": None}

    try:
        task_data = json.loads(dados.task_json)
    except json.JSONDecodeError as e:
        return {"sucesso": False, "erro": "JSON inválido: " + str(e), "caminho": None}

    id_no_conteudo = task_data.get("id") if isinstance(task_data, dict) else None
    if id_no_conteudo is not None and id_no_conteudo != dados.task_id:
        return {
            "sucesso": False,
            "erro": (
                "Divergência de id: task_id='" + dados.task_id + "' mas o JSON "
                "contém id='" + str(id_no_conteudo) + "'. Salve cada task com o "
                "task_id correspondente ao seu conteúdo."
            ),
            "caminho": None,
        }

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


MACRO_CONTEXT_FILENAME = "_macro_context.json"


def tool_salvar_macro_context_cr(macro_context_json: str) -> dict:
    """Persiste o contexto macro em workspace_output/coder/tasks/_macro_context.json.

    O contexto macro (summary, product_type, tech_stack, global_rules) é global
    à sessão e vive fora das tasks individuais. O harness precisa do
    `product_type` para escolher a superfície/perfil de execução, mas apenas as
    Tasks são persistidas por tool_salvar_task_cr. Esta tool grava o contexto
    macro num arquivo separado (NÃO denormalizado na Task), tornando o
    product_type resolvível pelos estágios downstream.

    Args:
        macro_context_json: JSON serializado do MacroContext.

    Returns:
        dict: {sucesso, erro, caminho, product_type}
    """
    try:
        macro = json.loads(macro_context_json)
    except json.JSONDecodeError as e:
        return {"sucesso": False, "erro": "JSON inválido: " + str(e), "caminho": None}

    if not isinstance(macro, dict):
        return {
            "sucesso": False,
            "erro": "macro_context deve ser um objeto JSON.",
            "caminho": None,
        }

    product_type = macro.get("product_type") or "a definir"
    macro["product_type"] = product_type

    output_dir = get_agent_workspace("cr_context_engineer")
    output_file = output_dir / MACRO_CONTEXT_FILENAME
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            json.dumps(macro, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(
            "[CR CONTEXT ENGINEER] Macro context salvo: " + str(output_file.resolve())
        )
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(output_file.resolve()),
            "product_type": product_type,
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": "Erro ao salvar macro context: " + str(e),
            "caminho": None,
        }
tool_ler_artefatos_adk = FunctionTool(tool_ler_artefatos)
tool_gerar_doubt_artifact_adk = FunctionTool(tool_gerar_doubt_artifact)
tool_emitir_manifesto_bloqueado_adk = FunctionTool(tool_emitir_manifesto_bloqueado)
tool_aguardar_resolucao_bloqueio_adk = LongRunningFunctionTool(aguardar_resolucao_bloqueio)
tool_salvar_task_cr_adk = FunctionTool(tool_salvar_task_cr)
tool_salvar_macro_context_cr_adk = FunctionTool(tool_salvar_macro_context_cr)
