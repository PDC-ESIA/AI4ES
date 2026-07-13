"""Modelo de contrato comum: Manifesto de Fase.

Cada Time persiste um manifesto pequeno no `session.state` (via state_delta)
listando apenas metadados dos artefatos. O conteúdo volumoso fica em arquivos
no workspace (`workspace_output/sessions/<session_id>/<time>/`).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class PhaseStatus(str, Enum):
    """Status possíveis de uma fase do SDLC."""

    OK = "ok"
    BLOCKED = "blocked"
    PARTIAL = "partial"


class ArtifactItem(BaseModel):
    """Metadados de um artefato persistido no workspace."""

    tipo: str
    id: str
    path: str


class DoubtItem(BaseModel):
    """Metadados de uma dúvida aberta por um Time."""

    id: str
    severidade: Literal["alta", "media", "baixa"]
    bloqueante: bool
    path: str


class PhaseManifest(BaseModel):
    """Manifesto leve emitido ao final de cada fase do SDLC.

    Invariantes:
      - status=ok  ⇒ nenhuma dúvida bloqueante.
      - status=blocked ⇒ ao menos uma dúvida bloqueante.
    """

    phase: str
    status: PhaseStatus
    artifacts: list[ArtifactItem] = Field(default_factory=list)
    doubts: list[DoubtItem] = Field(default_factory=list)
    summary: str = ""

    @field_validator("summary")
    @classmethod
    def _limitar_summary(cls, valor: str) -> str:
        """summary deve ser curto (≤ 500 tokens ~ 4000 chars de segurança)."""
        if len(valor) > 4000:
            raise ValueError("summary excede o limite de ~500 tokens")
        return valor

    @model_validator(mode="after")
    def _checar_invariantes(self) -> PhaseManifest:
        tem_bloqueante = any(d.bloqueante for d in self.doubts)
        if self.status == PhaseStatus.OK and tem_bloqueante:
            raise ValueError(
                "status=ok não permite dúvidas bloqueantes"
            )
        if self.status == PhaseStatus.BLOCKED and not tem_bloqueante:
            raise ValueError(
                "status=blocked exige ao menos uma dúvida bloqueante"
            )
        return self

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Serialização compatível com state_delta do ADK."""
        return super().model_dump(**kwargs)
