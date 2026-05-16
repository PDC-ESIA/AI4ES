from pydantic import BaseModel, Field
from typing import Optional


class SaveRequest(BaseModel):
    filename: str = Field(description="Nome do arquivo a persistir")
    content: str = Field(description="Conteúdo textual do artefato")


class SaveResult(BaseModel):
    status: str = Field(description="ok | error")
    path: Optional[str] = Field(default=None, description="Caminho final em staging")
    versioned_backup: Optional[str] = Field(
        default=None,
        description="Caminho da versão anterior se houve sobrescrita"
    )
    timestamp: Optional[str] = None
    error: Optional[str] = Field(default=None, description="Mensagem de erro se status=error")