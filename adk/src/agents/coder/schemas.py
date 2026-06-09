from pydantic import BaseModel, Field


class FileCreated(BaseModel):
    path: str = Field(description="Caminho do arquivo criado/modificado")
    purpose: str = Field(description="Finalidade do arquivo em uma frase")


class ImplementationOutput(BaseModel):
    files_created: list[FileCreated]
    git_status: str = Field(description="Estado do git após as operações")
    summary: str = Field(description="Resumo do que foi implementado")
