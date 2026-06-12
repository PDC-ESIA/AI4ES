"""
Tools do Agente CI/CD Pipeline.

Responsabilidades:
- Persistir arquivos de configuração de CI/CD (Dockerfile, docker-compose,
  workflows GitHub Actions) como arquivos no workspace do projeto.
"""

import logging
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, ValidationError
from google.adk.tools import FunctionTool

from shared.workspace import get_workspace_root, AGENT_DIRS

logger = logging.getLogger(__name__)

# Extensões e nomes de arquivo permitidos para artefatos de pipeline
_ALLOWED_EXTENSIONS = {".yml", ".yaml", ".dockerignore"}
_ALLOWED_FILENAMES = {"Dockerfile"}


# -------------------------------------------------------------------
# SCHEMA DE VALIDAÇÃO
# -------------------------------------------------------------------

class SalvarPipelineConfigSchema(BaseModel):
    """Schema de validação para salvar arquivos de pipeline."""

    filename: str = Field(
        ...,
        description=(
            "Nome do arquivo a salvar (ex: 'Dockerfile', "
            "'docker-compose.build.yml', 'ci.yml')"
        ),
    )
    content: str = Field(
        ...,
        description="Conteúdo completo do arquivo de configuração",
    )
    subdir: str = Field(
        default="",
        description=(
            "Subdiretório opcional dentro da pasta pipeline "
            "(ex: '.github/workflows' para workflows CI/CD)"
        ),
    )

    @field_validator("filename")
    def validar_filename(cls, v: str) -> str:
        """Valida que o arquivo é de um tipo permitido para pipeline."""
        name = Path(v).name

        if name in _ALLOWED_FILENAMES:
            return v

        suffix = Path(v).suffix.lower()
        if suffix in _ALLOWED_EXTENSIONS:
            return v

        raise ValueError(
            f"Arquivo '{v}' não é permitido. "
            f"Nomes permitidos: {_ALLOWED_FILENAMES}. "
            f"Extensões permitidas: {_ALLOWED_EXTENSIONS}."
        )

    @field_validator("subdir")
    def validar_subdir(cls, v: str) -> str:
        """Impede path traversal no subdiretório."""
        if ".." in v:
            raise ValueError(
                f"Path traversal não permitido no subdir: '{v}'. "
                f"Não use '..' no caminho."
            )
        return v


# -------------------------------------------------------------------
# TOOL: Salvar Arquivo de Pipeline no Workspace
# -------------------------------------------------------------------

def tool_salvar_pipeline_config(
    filename: str,
    content: str,
    subdir: str = "",
) -> dict:
    """Salva um arquivo de configuração de CI/CD no workspace do projeto.

    Persiste o arquivo em: $WORKSPACE_OUTPUT_DIR/pipeline/[subdir/]<filename>
    Cria os diretórios automaticamente se não existirem.
    Arquivos permitidos: Dockerfile, .yml, .yaml, .dockerignore.

    Args:
        filename (str): Nome do arquivo (ex: 'Dockerfile', 'docker-compose.build.yml').
        content (str): Conteúdo completo do arquivo.
        subdir (str): Subdiretório opcional (ex: '.github/workflows').

    Returns:
        dict: Status da operação com caminho do arquivo gerado.
    """
    try:
        dados = SalvarPipelineConfigSchema(
            filename=filename,
            content=content,
            subdir=subdir,
        )
    except ValidationError as e:
        return {"sucesso": False, "erro": str(e), "caminho": None}

    workspace_root = get_workspace_root()
    output_dir = workspace_root / AGENT_DIRS["cicd_agent"]

    if dados.subdir:
        output_dir = output_dir / dados.subdir

    output_file = output_dir / dados.filename

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file.write_text(dados.content, encoding="utf-8")
        logger.info(
            f"[CICD AGENT] Arquivo salvo: {output_file.resolve()}"
        )
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(output_file.resolve()),
            "filename": dados.filename,
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": f"Erro ao salvar arquivo de pipeline: {e}",
            "caminho": None,
        }


# -------------------------------------------------------------------
# EXPORTANDO TOOLS PARA O ADK
# -------------------------------------------------------------------

tool_salvar_pipeline_config_adk = FunctionTool(tool_salvar_pipeline_config)
