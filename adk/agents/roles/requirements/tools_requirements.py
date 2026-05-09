"""
Tools do Agente Requirements
 
Responsabilidades:
- Ler PRDs brutos de arquivo quando necessário
- Gerar Doubt Artifact ao detectar inconsistencias ou ambiguidades
- Persistir requisitos como JSON no workspace
"""
 
import json
import logging
import os
from datetime import datetime
from pathlib import Path
 
from pydantic import BaseModel, Field, field_validator, ValidationError
from google.adk.tools import FunctionTool

from shared.factory.workspace import get_workspace_root, AGENT_DIRS
 
logger = logging.getLogger(__name__)
 
 
# -------------------------------------------------------------------
# SCHEMAS DE VALIDACAO (Pydantic)
# -------------------------------------------------------------------
 
class LeituraPRDSchema(BaseModel):
    caminho: str = Field(..., description="Caminho do arquivo de PRD (.md ou .txt)")
 
    @field_validator("caminho")
    def validar_caminho(cls, v):
        path = Path(v)
        if not path.is_absolute() and ".." in path.parts:
            raise ValueError("Caminho relativo não pode conter '..' (path traversal).")
        if path.suffix not in (".md", ".txt"):
            raise ValueError("O PRD deve ser um arquivo .md ou .txt.")
        return v
 
 
class DoubtArtifactSchema(BaseModel):
    titulo: str = Field(..., description="Título curto da inconsistencia encontrada")
    secao: str = Field(..., description="Seção ou módulo onde a inconsistencia foi detectada")
    descricao: str = Field(..., description="Descrição detalhada do problema encontrado")
    impacto: str = Field(..., description="Qual agente ou componente é impactado")
    sugestao: str = Field(
        default="Aguardando esclarecimento e intervenção.",
        description="Sugestão de resolução"
    )
    nome_arquivo: str = Field(default="Doubt_Artifact_requirements.md")
 
    @field_validator("nome_arquivo")
    def validar_extensao(cls, v):
        if not v.endswith(".md"):
            raise ValueError("O Doubt Artifact deve ser um arquivo .md.")
        return v
 
 
# -------------------------------------------------------------------
# TOOL 1: Ler PRD de Arquivo
# -------------------------------------------------------------------
 
def tool_ler_prd_arquivo(caminho: str) -> dict:
    """Lê o conteúdo bruto de um PRD a partir de um arquivo .md ou .txt.
 
    Use esta tool quando o usuário informar um caminho de arquivo no prompt.
    Para entradas de texto direto no terminal, não é necessario usar esta tool.
 
    Args:
        caminho (str): Caminho absoluto ou relativo ao arquivo de PRD.
 
    Returns:
        dict: Status, conteúdo bruto do PRD, número de linhas e erros.
    """
    try:
        dados = LeituraPRDSchema(caminho=caminho)
    except ValidationError as e:
        return {"sucesso": False, "erro": str(e), "conteúdo": None}
 
    path = Path(dados.caminho)
 
    if not path.exists():
        return {
            "sucesso": False,
            "erro": "Arquivo nao encontrado: " + caminho,
            "conteúdo": None,
        }
 
    try:
        conteudo = path.read_text(encoding="utf-8")
        return {
            "sucesso": True,
            "erro": None,
            "conteúdo": conteudo,
            "total_linhas": len(conteudo.splitlines()),
            "total_caracteres": len(conteudo),
            "caminho_absoluto": str(path.resolve()),
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": "Erro ao ler o arquivo: " + str(e),
            "conteúdo": None,
        }
 
 
# -------------------------------------------------------------------
# TOOL 2: Gerar Doubt Artifact
# -------------------------------------------------------------------
 
def tool_gerar_doubt_artifact(
    titulo: str,
    secao: str,
    descricao: str,
    impacto: str,
    sugestao: str = "Aguardando esclarecimento e intervenção.",
    nome_arquivo: str = "Doubt_Artifact_requirements.md",
) -> dict:
    """Gera um Doubt Artifact ao detectar inconsistencias ou ambiguidades no requisito.
 
    ATENÇÃO: use esta tool sempre que encontrar requisitos contraditórios,
    ambiguidades que impeçam a análise ou entradas incompletas.
    A execução deve ser PAUSADA após gerar este arquivo.
 
    Args:
        título (str): Título curto da inconsistencia.
        seção (str): Seção ou módulo onde o problema foi encontrado.
        descrição (str): Descrição detalhada do problema.
        impacto (str): Qual componente ou agente é impactado.
        sugestão (str): Sugestão de resolução ou próximo passo.
        nome_arquivo (str): Nome do arquivo de saída.
 
    Returns:
        dict: Status, caminho do arquivo gerado e mensagem de pausa.
    """
    try:
        dados = DoubtArtifactSchema(
            titulo=titulo,
            secao=secao,
            descricao=descricao,
            impacto=impacto,
            sugestao=sugestao,
            nome_arquivo=nome_arquivo,
        )
    except ValidationError as e:
        return {"sucesso": False, "erro": str(e), "caminho": None}
 
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 
    conteudo = f"""
# Doubt Artifact — {dados.titulo}

> EXECUÇÃO PAUSADA — INTERVENÇÃO NECESSÁRIA
> Gerado pelo requirements_agent em {timestamp}

---

## Localização
Seção / Módulo afetado: {dados.secao}

## Descrição do Problema
{dados.descricao}

## Impacto
{dados.impacto}

## Sugestão de Resolução
{dados.sugestao}

---

## Checklist de Resolução
- [ ] Inconsistência notificada
- [ ] Decisão tomada e documentada
- [ ] Requisito corrigido ou esclarecido
- [ ] Agente pode retomar a análise

Responsável: Líder Operacional
Status: Pendente
"""
 
    path = Path(dados.nome_arquivo)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(conteudo, encoding="utf-8")
        logger.warning("[DOUBT ARTIFACT] " + dados.titulo + " — secao: " + dados.secao)
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(path.resolve()),
            "título": dados.titulo,
            "status": "EXECUÇÃO PAUSADA — aguardando intervenção",
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": "Erro ao salvar Doubt Artifact: " + str(e),
            "caminho": None,
        }
 
 
class SalvarRequisitoSchema(BaseModel):
    req_id: str = Field(..., description="ID do requisito (ex: 'REQ-001')")
    req_json: str = Field(..., description="Conteúdo JSON serializado do requisito")

    @field_validator("req_id")
    def validar_req_id(cls, v):
        if not v.startswith("REQ-"):
            raise ValueError(f"req_id deve iniciar com 'REQ-'. Recebido: '{v}'")
        return v


# -------------------------------------------------------------------
# TOOL 3: Salvar Requisito no Workspace
# -------------------------------------------------------------------

def tool_salvar_requisito(req_id: str, req_json: str) -> dict:
    """Salva um requisito como arquivo JSON no workspace do projeto.

    Persiste o arquivo em: $WORKSPACE_OUTPUT_DIR/requirements/<req_id>.json
    Cria os diretórios automaticamente se não existirem.

    Args:
        req_id (str): Identificador do requisito (ex: 'REQ-001').
        req_json (str): Conteúdo JSON serializado do requisito completo.

    Returns:
        dict: Status da operação, caminho do arquivo gerado e erros.
    """
    try:
        dados = SalvarRequisitoSchema(req_id=req_id, req_json=req_json)
    except ValidationError as e:
        return {"sucesso": False, "erro": str(e), "caminho": None}

    try:
        req_data = json.loads(dados.req_json)
    except json.JSONDecodeError as e:
        return {
            "sucesso": False,
            "erro": f"JSON inválido no requisito: {e}",
            "caminho": None,
        }

    workspace_root = get_workspace_root()
    output_dir = workspace_root / AGENT_DIRS["requirements_agent"]
    output_file = output_dir / f"{dados.req_id}.json"

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            json.dumps(req_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(f"[REQUIREMENTS] Requisito salvo: {output_file.resolve()}")
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(output_file.resolve()),
            "req_id": dados.req_id,
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": f"Erro ao salvar requisito: {e}",
            "caminho": None,
        }


# -------------------------------------------------------------------
# EXPORTANDO TOOLS PARA O ADK
# -------------------------------------------------------------------
 
tool_ler_prd_arquivo_adk = FunctionTool(tool_ler_prd_arquivo)
tool_gerar_doubt_artifact_adk = FunctionTool(tool_gerar_doubt_artifact)
tool_salvar_requisito_adk = FunctionTool(tool_salvar_requisito)
