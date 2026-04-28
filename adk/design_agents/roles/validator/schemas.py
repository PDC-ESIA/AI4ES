from pydantic import BaseModel, Field
from typing import List
from enum import Enum


class VerdictStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class ArtifactVerdict(BaseModel):
    filename: str
    artifact_type: str = Field(description="mmd | md")
    status: VerdictStatus
    errors: List[str] = Field(
        default_factory=list,
        description="Lista de erros encontrados. Vazio se aprovado."
    )
    routed_to: str = Field(
        default="",
        description="Agente acionado para correção se reprovado"
    )


class ValidatorOutput(BaseModel):
    verdicts: List[ArtifactVerdict]
    approved_count: int
    rejected_count: int