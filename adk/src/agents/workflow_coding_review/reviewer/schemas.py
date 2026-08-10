"""Schemas Pydantic da saída estruturada do Reviewer do workflow coding_review.

Define ReviewIssue (issue individual com severidade e camada de verificação)
e ReviewOutput (envelope com status APROVADO/BLOQUEADO + lista de issues).
Autocontido para o workflow coding_review.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ReviewIssue(BaseModel):
    """Issue individual identificada pelo reviewer durante uma das 4 camadas."""

    severity: str = Field(description="critical | warning | info")
    description: str = Field(description="Descrição do problema encontrado")
    file: Optional[str] = Field(default=None, description="Arquivo afetado")
    layer: str = Field(description="completude | arquitetura | corretude | testes")


class ReviewOutput(BaseModel):
    """Output completo do reviewer: status global + issues classificadas."""

    status: str = Field(description="APROVADO ou BLOQUEADO")
    issues: list[ReviewIssue] = Field(default_factory=list)
    report_path: Optional[str] = Field(
        default=None,
        description="Caminho do relatório .md salvo via tool_salvar_relatorio",
    )
