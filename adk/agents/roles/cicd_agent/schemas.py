"""Schemas de saída do agente de CI/CD Pipeline."""

from pydantic import BaseModel, Field


class GeneratedFile(BaseModel):
    """Um arquivo de configuração gerado pelo agente de CI/CD."""

    path: str = Field(
        description="Caminho relativo do arquivo gerado (ex: 'Dockerfile')"
    )
    content: str = Field(
        description="Conteúdo completo do arquivo gerado"
    )
    description: str = Field(
        description="Descrição curta do propósito deste arquivo"
    )


class PipelineOutput(BaseModel):
    """Saída completa do agente de CI/CD Pipeline."""

    dockerfile: GeneratedFile = Field(
        description="Dockerfile para build da imagem do sistema gerado"
    )
    docker_compose: GeneratedFile = Field(
        description="docker-compose.build.yml para orquestração do build"
    )
    ci_workflows: list[GeneratedFile] = Field(
        description=(
            "Workflows de CI/CD para GitHub Actions "
            "(.github/workflows/*.yml)"
        )
    )
    summary: str = Field(
        description="Resumo executivo das configurações de CI/CD geradas"
    )
    stack_used: list[str] = Field(
        description=(
            "Stack tecnológica considerada na geração dos artefatos "
            "(ex: ['Python 3.12', 'FastAPI', 'SQLite'])"
        )
    )
