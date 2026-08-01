"""Schemas Pydantic para a saída estruturada do implementation_validator.

Este é o único ponto do fluxo que carrega veredito de aprovação/reprovação. Ele
consome as evidências produzidas pelo executor (ver `executor/schemas.py`) e
decide, critério a critério, se a implementação atende ao work item.

Nomes de campos em inglês; descrições/enums/comentários em português, seguindo
o padrão de `reviewer/schemas.py` e `validator/schemas.py`.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class VerdictStatus(str, Enum):
    """Veredito global da validação da implementação."""

    APROVADO = "aprovado"
    REPROVADO = "reprovado"


class CriterionStatus(str, Enum):
    """Situação de um critério de aceite individual após a validação."""

    ATENDIDO = "atendido"
    NAO_ATENDIDO = "nao_atendido"
    INCONCLUSIVO = "inconclusivo"  # evidência insuficiente para decidir


class CriterionVerdict(BaseModel):
    """Veredito para um único critério de aceite, com justificativa e evidência."""

    criterion: str = Field(description="Critério de aceite avaliado")
    status: CriterionStatus = Field(description="Situação do critério após a avaliação")
    reasoning: str = Field(description="Justificativa da decisão para este critério")
    evidence_ref: Optional[str] = Field(
        default=None,
        description="Referência à evidência do executor que embasa a decisão",
    )


class ValidationVerdict(BaseModel):
    """Veredito consolidado da validação da implementação de um work item."""

    work_item_id: str = Field(description="Identificador do work item validado")
    status: VerdictStatus = Field(description="Veredito global: aprovado ou reprovado")
    criteria_verdicts: list[CriterionVerdict] = Field(
        default_factory=list,
        description="Veredito por critério de aceite",
    )
    blocking_reason: Optional[str] = Field(
        default=None,
        description="Motivo do bloqueio quando reprovado; None se aprovado",
    )
    summary: str = Field(description="Resumo textual do veredito")
