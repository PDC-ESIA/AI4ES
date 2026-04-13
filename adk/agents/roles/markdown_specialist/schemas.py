from pydantic import BaseModel, Field
from typing import Optional


class MarkdownOutput(BaseModel):
    hu_id: str = Field(description="ID da HU ex: HU-042")
    filename: str = Field(description="Nome do arquivo ex: relatorio_HU-042_2025-01-01.md")
    content: str = Field(description="Conteúdo completo do relatório .md")
    mmd_reference: str = Field(description="Nome do arquivo .mmd incorporado")
    doubt_artifact_path: Optional[str] = Field(
        default=None,
        description="Caminho do Doubt_Artifact gerado se houve bloqueio"
    )