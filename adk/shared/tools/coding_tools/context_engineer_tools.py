"""Tools do Agente Context Engineer.

Persistência de tasks contextualizadas como JSON no workspace centralizado em workspace_output/coder/tasks/.
Leitura de artefatos de requisitos via paths extraídos do manifesto pelo LLM.
Leitura de artefatos de design diretamente do workspace (fallback enquanto o Time 2 não produz manifesto).
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
    """Função interna que lê arquivos de uma pasta do workspace.
 
    Verifica existência, filtra por extensões textuais, ignora ocultos
    e limita tamanho por arquivo.
 
    Args:
        pasta_fase: Caminho absoluto da pasta a ser lida.
        workspace_root: Raiz do workspace para calcular paths relativos.
        nome_fase: Nome legível da fase para mensagens de erro.
 
    Returns:
        dict: sucesso, artefatos lidos, erros e metadados.
    """
    if not pasta_fase.exists() or not pasta_fase.is_dir():
        return {
            "sucesso": False,
            "fase": nome_fase,
            "erro": (
                "Pasta '" + nome_fase + "' não encontrada ou não é um diretorio: "
                + str(pasta_fase)
                + ". Verifique se a fase anterior concluiu com sucesso."
            ),
            "artefatos": None,
            "artefatos_minimos_presentes": False,
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
                "Pasta '" + nome_fase + "' existe, mas está vazia: "
                + str(pasta_fase)
                + ". A fase anterior pode não ter persistido seus artefatos."
            ),
            "artefatos": None,
            "artefatos_minimos_presentes": False,
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
                "path": str(arquivo.relative_to(workspace_root)),
                "nome": arquivo.name,
                "tipo": arquivo.suffix.lstrip("."),
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
            "artefatos_minimos_presentes": False,
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


def tool_salvar_task(task_id: str, task_json: str) -> dict:
    """Salva uma task contextualizada como JSON em workspace_output/coder/tasks/.

    Args:
        task_id (str): Identificador da task (ex: 'TASK-001').
        task_json (str): Conteúdo JSON serializado da task completa.

    Returns:
        dict: sucesso, erro, caminho, task_id
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


def tool_ler_requirements(paths_json: str) -> dict:
    """Lê artefatos de requisitos a partir dos paths extraídos do manifesto.

    O LLM extrai os paths do manifesto de requirements recebido no texto
    do prompt (repassado pelo orquestrador) e passa para esta tool como
    JSON serializado. A tool lê os arquivos do workspace e verifica os
    artefatos mínimos obrigatórios.
    
    RF é sempre obrigatório — sem RF não há o que transformar em task.
    HU é informada separadamente via campo tem_hu — ausência não bloqueia
    sozinha. O Passo 2.5 do prompt cruza com o design para determinar
    se é bloqueante.

    Args:
        paths_json (str): JSON serializado com lista de dicionários contendo
                          os paths dos artefatos extraídos do manifesto.
                          Formato: [{"path": "requirements/HUs/HU-001.md"}, ...]

    Returns:
        dict: sucesso, fase, artefatos lidos, artefatos_minimos_presentes,
              tem_hu, artefatos_minimos_ausentes e erros.
    """
    workspace_root = get_workspace_root()

    try:
        paths_list = json.loads(paths_json)
    except json.JSONDecodeError as e:
        return {
            "sucesso": False,
            "fase": "requirements",
            "erro": "paths_json inválido — JSON malformado: " + str(e),
            "artefatos": None,
            "artefatos_minimos_presentes": False,
            "tem_hu": False,
        }

    if not paths_list:
        return {
            "sucesso": False,
            "fase": "requirements",
            "erro": (
                "Nenhum path de artefato fornecido. "
                "Extraia os paths do manifesto de requirements recebido no prompt."
            ),
            "artefatos": None,
            "artefatos_minimos_presentes": False,
            "tem_hu": False,
        }

    artefatos = []
    erros = []
    tem_hu = False
    tem_rf = False

    for item in paths_list:
        path_rel = str(item.get("path", "") if isinstance(item, dict) else item).replace("\\", "/")
        rel_path = Path(path_rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            erros.append("Path inválido no manifesto: " + path_rel)
            logger.warning("[CONTEXT ENGINEER] Path inválido no manifesto: " + path_rel)
            continue
        path_abs = workspace_root / rel_path
        conteudo = _ler_arquivo(path_abs, workspace_root)
        if conteudo:
            artefatos.append(conteudo)
            nome = Path(path_rel).name
            if nome.startswith("HU-") and nome.endswith(".md"):
                tem_hu = True
            if nome.startswith("RF-") and nome.endswith(".md"):
                tem_rf = True
        else:
            erros.append("Arquivo não encontrado: " + path_rel)
            logger.warning("[CONTEXT ENGINEER] Artefato ausente: " + path_rel)

    artefatos_minimos_presentes = tem_rf
    artefatos_minimos_ausentes = []

    if not tem_rf:
        artefatos_minimos_ausentes.append(
            "Nenhum arquivo RF-*.md encontrado nos paths fornecidos"
        )
    if not tem_hu:
        artefatos_minimos_ausentes.append(
            "Nenhum arquivo HU-*.md encontrado nos paths fornecidos "
            "(pode ser válido — verificar consistência com design no Passo 2.5)"
        )

    return {
        "sucesso": True,
        "fase": "requirements",
        "erro": None,
        "artefatos": artefatos,
        "total_lidos": len(artefatos),
        "artefatos_minimos_presentes": artefatos_minimos_presentes,
        "artefatos_minimos_ausentes": artefatos_minimos_ausentes,
        "tem_hu": tem_hu,
        "erros_leitura": erros if erros else None,
    }

 
def tool_ler_design(tem_hu: bool = True) -> dict:
    """Lê todos os artefatos de design do workspace.
 
    Fallback enquanto o Time 2 não produz manifesto. Quando o manifesto
    de design for implementado, esta tool será atualizada para consumir
    os paths do manifesto via mesmo padrão da tool_ler_requirements.
 
    Verifica obrigatoriamente a presença de:
    - pelo menos 1 arquivo analise_tecnica_*.md em design/
 
    Returns:
        dict: sucesso, fase, artefatos lidos, artefatos_minimos_presentes e erros.
    """
    workspace_root = get_workspace_root()
    pasta_fase = workspace_root / "design"
 
    resultado = _ler_pasta_workspace(pasta_fase, workspace_root, "design")
    if not resultado["sucesso"]:
        return resultado
 
    tem_analise = any(
        a["nome"].startswith("analise_tecnica_") and a["nome"].endswith(".md")
        for a in resultado.get("artefatos", [])
    )
 
    artefatos_minimos_ausentes = []
    if not tem_analise:
        artefatos_minimos_ausentes.append(
            "Nenhum arquivo analise_tecnica_*.md encontrado em design/"
        )
 
    # Verifica inconsistência entre times
    inconsistencia = False
    if not tem_hu:
        tem_analise_hu = any(
            a["nome"].startswith("analise_tecnica_HU-") and a["nome"].endswith(".md")
            for a in resultado.get("artefatos", [])
        )
        if tem_analise_hu:
            inconsistencia = True

    resultado["artefatos_minimos_presentes"] = tem_analise
    resultado["artefatos_minimos_ausentes"] = artefatos_minimos_ausentes
    resultado["inconsistencia_detectada"] = inconsistencia
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
 
    Use esta tool quando qualquer uma das condições abaixo ocorrer, todas são bloqueantes e impedem a geração de tasks:
    - Manifesto de requirements com status=blocked ou ausente no prompt
    - RF-*.md ausente nos paths fornecidos
    - analise_tecnica_*.md ausente no workspace de design
    - Inconsistência entre times

    Após chamar esta tool, chame aguardar_resolucao_bloqueio para
    pausar o pipeline via HITL. Não gere nenhuma task.
 
    Args:
        titulo (str): Título curto do bloqueio.
        fase_bloqueada (str): Fase que causou o bloqueio.
        descricao (str): Descrição detalhada do problema encontrado.
        acao_necessaria (str): O que precisa ser feito para desbloquear.
        nome_arquivo (str): Nome do arquivo de saída.
        subdir (str): Subdiretório do workspace onde salvar (ex: 'coder').
 
    Returns:
        dict: sucesso, caminho do arquivo gerado e status de bloqueio.
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
                "erro": "subdir inválido — não use paths absolutos ou '..': " + subdir,
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
            + dados.titulo + " — fase: " + dados.fase_bloqueada
        )
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
    tool_context: ToolContext,
) -> dict:
    """Emite manifesto com status=blocked no state e em disco.

    Use após tool_gerar_doubt_artifact e antes de aguardar_resolucao_bloqueio.
    Garante que o manifesto seja gravado no state mesmo com pipeline pausado.

    Args:
        motivo (str): Motivo do bloqueio — usado como summary do manifesto.
        tool_context (ToolContext): Injetado automaticamente pelo ADK.

    Returns:
        dict: sucesso, status, caminho do manifesto gravado.
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
    doubts    = _scan_doubts(coder_ws, ws_root)

    manifest: dict = {
        "phase":     PHASE_NAME,
        "status":    "blocked",
        "artifacts": artifacts,
        "doubts":    doubts,
        "summary":   motivo,
    }

    if tool_context is not None:
        tool_context.state[STATE_KEY] = manifest

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


tool_salvar_task_adk = FunctionTool(tool_salvar_task)
tool_ler_requirements_adk = FunctionTool(tool_ler_requirements)
tool_ler_design_adk = FunctionTool(tool_ler_design)
tool_gerar_doubt_artifact_adk = FunctionTool(tool_gerar_doubt_artifact)
tool_emitir_manifesto_bloqueado_adk = FunctionTool(tool_emitir_manifesto_bloqueado)
tool_aguardar_resolucao_bloqueio_adk = LongRunningFunctionTool(aguardar_resolucao_bloqueio)


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

    # O nome do arquivo vem de `task_id` e o conteúdo de `task_json`, que são
    # argumentos independentes. Sem esta checagem, TASK-003.json poderia conter
    # a TASK-004 — e quem resolve a task pelo nome do arquivo (o coder) leria o
    # contrato errado sem nenhum sinal de erro.
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


# Nome do arquivo que carrega o contexto macro para os estágios downstream
# (harness/executor). Prefixo '_' evita colisão com os arquivos TASK-*.json.
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

    # Garante product_type sempre presente para o harness (default do schema).
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


tool_salvar_task_cr_adk = FunctionTool(tool_salvar_task_cr)
tool_salvar_macro_context_cr_adk = FunctionTool(tool_salvar_macro_context_cr)
