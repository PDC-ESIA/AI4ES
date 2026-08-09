"""Tools do Agente Context Engineer.
 
Persistência de tasks contextualizadas como JSON no workspace centralizado.
Leitura de artefatos de requisitos via manifesto (obrigatório) e de design
via manifesto (com fallback para leitura direta do workspace).
Geração de Doubt Artifact em caso de bloqueio.
"""
 
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
 
from pydantic import BaseModel, Field, field_validator, ValidationError
from google.adk.tools import FunctionTool
 
from shared.workspace import get_agent_workspace, get_workspace_root
 
logger = logging.getLogger(__name__)
 
EXTENSOES_TEXTUAIS = {".md", ".txt", ".json", ".yml", ".yaml", ".mmd", ".mermaid"}
TAMANHO_MAXIMO = 500_000
 
 
# -------------------------------------------------------------------
# SCHEMAS
# -------------------------------------------------------------------
 
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
 
 
# -------------------------------------------------------------------
# FUNÇÃO AUXILIAR: leitura de arquivo individual do workspace
# -------------------------------------------------------------------
 
def _ler_arquivo(path: Path, workspace_root: Path) -> Optional[dict]:
    """Lê um arquivo do workspace e retorna seu conteúdo como dicionário."""
    if not path.exists() or not path.is_file():
        return None
    try:
        conteudo = path.read_text(encoding="utf-8", errors="replace")
        return {
            "path": str(path.relative_to(workspace_root)),
            "nome": path.name,
            "tipo": path.suffix.lstrip("."),
            "conteudo": conteudo,
        }
    except Exception as e:
        logger.error("[CONTEXT ENGINEER] Erro ao ler " + str(path) + ": " + str(e))
        return None
 
 
# -------------------------------------------------------------------
# FUNÇÃO AUXILIAR: leitura genérica de pasta do workspace
# -------------------------------------------------------------------
 
def _ler_pasta_workspace(pasta_fase: Path, workspace_root: Path, nome_fase: str) -> dict:
    """Função interna que lê arquivos de uma pasta do workspace."""
    if not pasta_fase.exists() or not pasta_fase.is_dir():
        return {
            "sucesso": False,
            "fase": nome_fase,
            "erro": (
                "Pasta '" + nome_fase + "' não encontrada ou não é um diretório: "
                + str(pasta_fase)
                + ". Verifique se a fase anterior concluiu com sucesso."
            ),
            "artefatos": None,
            "artefatos_minimos_presentes": False,
            "caminho_esperado": str(pasta_fase),
        }
 
    arquivos = sorted(
        [
            a for a in pasta_fase.rglob("*")
            if a.is_file()
            and a.suffix.lower() in EXTENSOES_TEXTUAIS
            and not any(part.startswith(".") for part in a.relative_to(pasta_fase).parts)
            and a.stat().st_size <= TAMANHO_MAXIMO
        ],
        key=lambda p: str(p.relative_to(pasta_fase)),
    )
 
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
            "artefatos_minimos_presentes": False,
            "caminho_esperado": str(pasta_fase),
        }
 
    artefatos = []
    erros = []
 
    for arquivo in arquivos:
        try:
            conteudo = arquivo.read_text(encoding="utf-8", errors="replace")
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
 
 
# -------------------------------------------------------------------
# TOOL 1: Salvar Task
# -------------------------------------------------------------------
 
def tool_salvar_task(task_id: str, task_json: str) -> dict:
    """Salva uma task contextualizada como JSON em workspace/tasks/.
 
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
 

# -------------------------------------------------------------------
# TOOL 2: Salvar Task CR (workflow coding_review — coder/tasks/)
# -------------------------------------------------------------------
 
def tool_salvar_task_cr(task_id: str, task_json: str) -> dict:
    """Salva task contextualizada em workspace_output/coder/tasks/.
 
    Mesma lógica do tool_salvar_task canônico, mas escreve no subdir
    consolidado do workflow coding_review.
 
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

# -------------------------------------------------------------------
# TOOL 3: Ler Artefatos de Requisitos via Manifesto (sem fallback)
# -------------------------------------------------------------------
 
def tool_ler_requirements() -> dict:
    workspace_root = get_workspace_root()

    manifest_path = workspace_root / "requirements" / "manifest.json"

    if not manifest_path.exists():
        return {
            "sucesso": False,
            "fase": "requirements",
            "erro": (
                "Manifesto de requirements não encontrado em requirements/manifest.json. "
                "A fase de requisitos deve ter concluído e emitido seu manifesto "
                "antes do context_engineer ser executado."
            ),
            "artefatos": None,
            "artefatos_minimos_presentes": False,
            "tem_hu": False,
        }

    try:
        manifesto = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {
            "sucesso": False,
            "fase": "requirements",
            "erro": "Manifesto de requirements inválido — JSON malformado: " + str(e),
            "artefatos": None,
            "artefatos_minimos_presentes": False,
            "tem_hu": False,
        }
 
    status_manifesto = manifesto.get("status", "unknown")
 
    # Manifesto bloqueado — repassa o bloqueio
    if status_manifesto == "blocked":
        return {
            "sucesso": False,
            "fase": "requirements",
            "status_manifesto": status_manifesto,
            "erro": (
                "A fase de requisitos está bloqueada (status=blocked). "
                "Verifique os doubts: "
                + str([d.get("id") for d in manifesto.get("doubts", [])])
            ),
            "artefatos": None,
            "artefatos_minimos_presentes": False,
            "tem_hu": False,
        }
 
    # Lê os artefatos pelos paths do manifesto
    artefatos = []
    erros = []
    tem_hu = False
    tem_rf = False
 
    for item in manifesto.get("artifacts", []):
        path_rel = str(item.get("path", ""))
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
            "Nenhum arquivo RF-*.md encontrado nos artefatos do manifesto"
        )
    if not tem_hu:
        artefatos_minimos_ausentes.append(
            "Nenhum arquivo HU-*.md encontrado nos artefatos do manifesto "
            "(pode ser válido — verificar consistência com design no Passo 2.5)"
        )
 
    return {
        "sucesso": True,
        "fase": "requirements",
        "status_manifesto": status_manifesto,
        "erro": None,
        "artefatos": artefatos,
        "total_lidos": len(artefatos),
        "artefatos_minimos_presentes": artefatos_minimos_presentes,
        "artefatos_minimos_ausentes": artefatos_minimos_ausentes,
        "tem_hu": tem_hu,
        "erros_leitura": erros if erros else None,
    }
 
 
# -------------------------------------------------------------------
# TOOL 4: Ler Artefatos de Design via Manifesto (com fallback)
# -------------------------------------------------------------------
 
def tool_ler_design(manifesto_json: Optional[str] = None) -> dict:
    """Lê artefatos de design a partir do manifesto da fase.
 
    O manifesto de design é opcional — quando ausente, usa fallback para
    leitura direta do workspace/design/. Quando presente e com status
    bloqueado, retorna erro para que o agente gere Doubt Artifact e pare.
 
    Args:
        manifesto_json (str): JSON serializado do manifesto de design.
                              Opcional — sem ele usa fallback para workspace.
 
    Returns:
        dict: sucesso, status_manifesto, fase, artefatos lidos,
              artefatos_minimos_presentes e erros.
    """
    workspace_root = get_workspace_root()
 
    # Sem manifesto → fallback: lê workspace/design/ diretamente
    if not manifesto_json:
        logger.info(
            "[CONTEXT ENGINEER] Manifesto de design ausente — "
            "usando fallback para leitura direta do workspace."
        )
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
 
        resultado["artefatos_minimos_presentes"] = tem_analise
        resultado["artefatos_minimos_ausentes"] = artefatos_minimos_ausentes
        resultado["status_manifesto"] = None
        resultado["fallback"] = True
        return resultado
 
    # Parse do manifesto
    try:
        manifesto = json.loads(manifesto_json)
    except json.JSONDecodeError as e:
        return {
            "sucesso": False,
            "fase": "design",
            "erro": "Manifesto de design inválido — JSON malformado: " + str(e),
            "artefatos": None,
            "artefatos_minimos_presentes": False,
        }
 
    status_manifesto = manifesto.get("status", "unknown")
 
    # Manifesto bloqueado — repassa o bloqueio
    if status_manifesto == "blocked":
        return {
            "sucesso": False,
            "fase": "design",
            "status_manifesto": status_manifesto,
            "erro": (
                "A fase de design está bloqueada (status=blocked). "
                "Verifique os doubts: "
                + str([d.get("id") for d in manifesto.get("doubts", [])])
            ),
            "artefatos": None,
            "artefatos_minimos_presentes": False,
        }
 
    # Lê os artefatos pelos paths do manifesto
    artefatos = []
    erros = []
    tem_analise = False
 
    for item in manifesto.get("artifacts", []):
        path_rel = item.get("path", "")
        path_abs = workspace_root / path_rel
 
        conteudo = _ler_arquivo(path_abs, workspace_root)
        if conteudo:
            artefatos.append(conteudo)
            nome = Path(path_rel).name
            if nome.startswith("analise_tecnica_") and nome.endswith(".md"):
                tem_analise = True
        else:
            erros.append("Arquivo não encontrado: " + path_rel)
            logger.warning("[CONTEXT ENGINEER] Artefato ausente: " + path_rel)
 
    artefatos_minimos_ausentes = []
    if not tem_analise:
        artefatos_minimos_ausentes.append(
            "Nenhum arquivo analise_tecnica_*.md encontrado nos artefatos do manifesto"
        )
 
    return {
        "sucesso": True,
        "fase": "design",
        "status_manifesto": status_manifesto,
        "erro": None,
        "artefatos": artefatos,
        "total_lidos": len(artefatos),
        "artefatos_minimos_presentes": tem_analise,
        "artefatos_minimos_ausentes": artefatos_minimos_ausentes,
        "erros_leitura": erros if erros else None,
        "fallback": False,
    }
 
 
# -------------------------------------------------------------------
# TOOL 5: Gerar Doubt Artifact
# -------------------------------------------------------------------
 
def tool_gerar_doubt_artifact(
    titulo: str,
    fase_bloqueada: str,
    descricao: str,
    acao_necessaria: str,
    nome_arquivo: str = "Doubt_Artifact_context_engineer.md",
    subdir: str = "",
) -> dict:
    """Gera um Doubt Artifact ao detectar bloqueio no workspace ou no manifesto.
 
    Use esta tool quando qualquer uma das condições abaixo ocorrer —
    todas são bloqueantes e impedem a geração de tasks:
    - Manifesto de requirements ausente ou com status=blocked
    - Manifesto de design com status=blocked
    - RF-*.md ausente nos artefatos do manifesto de requirements
    - analise_tecnica_*.md ausente nos artefatos do manifesto de design
      (ou no workspace/design/ no caso de fallback)
    - Inconsistência entre times: analise_tecnica_HU-*.md existe mas
      não existem HUs nos artefatos de requirements
 
    Após chamar esta tool, PARE a execução. Não gere nenhuma task.
 
    Args:
        titulo (str): Título curto do bloqueio.
        fase_bloqueada (str): Fase que causou o bloqueio.
        descricao (str): Descrição detalhada do problema encontrado.
        acao_necessaria (str): O que precisa ser feito para desbloquear.
        nome_arquivo (str): Nome do arquivo de saída.
 
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
 
 
# -------------------------------------------------------------------
# EXPORTANDO TOOLS PARA O ADK
# -------------------------------------------------------------------
 
tool_salvar_task_adk = FunctionTool(tool_salvar_task)
tool_salvar_task_cr_adk = FunctionTool(tool_salvar_task_cr)
tool_ler_requirements_adk = FunctionTool(tool_ler_requirements)
tool_ler_design_adk = FunctionTool(tool_ler_design)
tool_gerar_doubt_artifact_adk = FunctionTool(tool_gerar_doubt_artifact)
 