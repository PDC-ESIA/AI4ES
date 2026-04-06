from pydantic import BaseModel, Field


class Requirement(BaseModel):
    id: str = Field(description="Identificador (ex.: REQ-1)")
    description: str = Field(description="Descrição curta do requisito")
    acceptance_criteria: str = Field(description="Critério de aceitação em uma frase")


class RequirementsOutput(BaseModel):
    requirements: list[Requirement]
