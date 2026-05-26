from pydantic import BaseModel, Field
from typing import Optional


class MermaidOutput(BaseModel):
    hu_id: str = Field(description="ID da HU ex: HU-042")
    filename: str = Field(description="Nome do arquivo ex: diagrama_HU-042_processo_compra.mmd")
    diagram_type: str = Field(description="Tipo Mermaid usado")
    content: str = Field(description="Conteúdo completo do arquivo .mmd incluindo cabeçalho")
    doubt_artifact_path: Optional[str] = Field(
        default=None,
        description="Caminho do Doubt_Artifact gerado se houve bloqueio"
    )