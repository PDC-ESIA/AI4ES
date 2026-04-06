from typing import Optional

from pydantic import BaseModel, Field


class ReviewIssue(BaseModel):
    severity: str = Field(description="critical | warning | info")
    description: str
    file: Optional[str] = Field(default=None, description="Arquivo afetado")


class ReviewOutput(BaseModel):
    status: str = Field(description="APROVADO ou BLOQUEADO")
    issues: list[ReviewIssue] = Field(default_factory=list)
    report_path: Optional[str] = Field(default=None, description="Caminho do relatório salvo")
