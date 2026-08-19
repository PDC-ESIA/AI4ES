"""Tools do Agente Context Engineer.

Persistência de tasks contextualizadas como JSON no workspace centralizado.
Leitura de artefatos de requisitos e design diretamente do workspace.
Geração de Doubt Artifact em caso de bloqueio.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, ValidationError
from google.adk.tools import FunctionTool

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
 

def tool_ler_requirements() -> dict:
    """Lê todos os artefatos de requisitos do workspace.
 
    Verifica obrigatoriamente a presença de:
    - pelo menos 1 arquivo RF-*.md em requirements/RFs/ (SEMPRE obrigatório)
 
    Informa separadamente se HUs existem via campo tem_hu — a ausência
    de HUs não é bloqueante aqui. O Passo 2.5 do prompt cruza essa
    informação com o design para determinar se é bloqueante ou não.
 
    Returns:
        dict: sucesso, artefatos lidos, artefatos_minimos_presentes,
              tem_hu, artefatos_minimos_ausentes e erros.
    """
    workspace_root = get_workspace_root()
    pasta_fase = workspace_root / "requirements"
 
    resultado = _ler_pasta_workspace(pasta_fase, workspace_root, "requirements")
    if not resultado["sucesso"]:
        return resultado
 
    pasta_hus = pasta_fase / "HUs"
    pasta_rfs = pasta_fase / "RFs"
 
    artefatos_minimos_presentes = True
    artefatos_minimos_ausentes = []
 
    tem_hu = (
        pasta_hus.exists()
        and any(
            f.name.startswith("HU-") and f.suffix == ".md"
            for f in pasta_hus.iterdir()
            if f.is_file()
        )
    )
    if not tem_hu:
        artefatos_minimos_ausentes.append(
            "Nenhum arquivo HU-*.md encontrado em requirements/HUs/ "
            "(pode ser válido — verificar consistência com design no Passo 2.5)"
        )
 
    tem_rf = (
        pasta_rfs.exists()
        and any(
            f.name.startswith("RF-") and f.suffix == ".md"
            for f in pasta_rfs.iterdir()
            if f.is_file()
        )
    )
    if not tem_rf:
        artefatos_minimos_presentes = False
        artefatos_minimos_ausentes.append(
            "Nenhum arquivo RF-*.md encontrado em requirements/RFs/"
        )
 
    resultado["artefatos_minimos_presentes"] = artefatos_minimos_presentes
    resultado["artefatos_minimos_ausentes"] = artefatos_minimos_ausentes
    resultado["tem_hu"] = tem_hu
    return resultado

 
def tool_ler_design() -> dict:
    """Lê todos os artefatos de design do workspace.
 
    Verifica obrigatoriamente a presença de:
    - pelo menos 1 arquivo analise_tecnica_*.md em design/
 
    Se o mínimo não for encontrado, retorna
    artefatos_minimos_presentes=False para que o agente gere um
    Doubt Artifact e pare a execução.
 
    Returns:
        dict: sucesso, artefatos lidos, artefatos_minimos_presentes e erros.
    """
    workspace_root = get_workspace_root()
    pasta_fase = workspace_root / "design"
 
    resultado = _ler_pasta_workspace(pasta_fase, workspace_root, "design")
    if not resultado["sucesso"]:
        return resultado
 
    # Verifica artefatos mínimos obrigatórios
    tem_analise = any(
        f.name.startswith("analise_tecnica_") and f.suffix == ".md"
        for f in pasta_fase.rglob("*.md")
        if f.is_file()
    )
 
    artefatos_minimos_ausentes = []
    if not tem_analise:
        artefatos_minimos_ausentes.append(
            "Nenhum arquivo analise_tecnica_*.md encontrado em design/"
        )
 
    resultado["artefatos_minimos_presentes"] = tem_analise
    resultado["artefatos_minimos_ausentes"] = artefatos_minimos_ausentes
    return resultado

 
def tool_gerar_doubt_artifact(
    titulo: str,
    fase_bloqueada: str,
    descricao: str,
    acao_necessaria: str,
    nome_arquivo: str = "Doubt_Artifact_context_engineer.md",
) -> dict:
    """Gera um Doubt Artifact ao detectar bloqueio no workspace.
 
    Use esta tool quando qualquer uma das condições abaixo ocorrer -todas são bloqueantes:
    - A pasta requirements/ não existir no workspace
    - A pasta design/ não existir no workspace
    - RF-*.md ausente em requirements/RFs/
    - analise_tecnica_*.md ausente em design/
    - Inconsistência entre times: analise_tecnica_HU-*.md existe em design
      mas não existe HUs/ em requirements

    A ausência de qualquer um desses artefatos, isoladamente ou em conjunto,
    impede a geração de tasks e exige intervenção humana.
    Após chamar esta tool, PARE a execução. Não gere nenhuma task.
 
    Args:
        titulo (str): Título curto do bloqueio.
        fase_bloqueada (str): Fase que causou o bloqueio ('requirements' ou 'design').
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
    path = workspace_root / dados.nome_arquivo
 
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
 

tool_salvar_task_adk = FunctionTool(tool_salvar_task)
tool_ler_requirements_adk = FunctionTool(tool_ler_requirements)
tool_ler_design_adk = FunctionTool(tool_ler_design)
tool_gerar_doubt_artifact_adk = FunctionTool(tool_gerar_doubt_artifact)


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
