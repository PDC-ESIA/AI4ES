from pydantic import BaseModel, Field


class Module(BaseModel):
    name: str = Field(description="Nome do módulo/classe")
    path: str = Field(description="Caminho relativo no projeto")
    responsibility: str = Field(description="Responsabilidade em uma frase")


class ArchitectureOutput(BaseModel):
    directory_structure: str = Field(description="Árvore de diretórios proposta")
    modules: list[Module]
    technical_decisions: list[str] = Field(description="Decisões técnicas relevantes")
