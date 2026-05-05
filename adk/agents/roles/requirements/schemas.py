from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class AnalystOutput(BaseModel):
    """Saída consolidada orientada a skills, preservando os templates Markdown."""

    status: Literal["concluido", "concluído", "bloqueado"] = Field(
        "concluido", description="Status final da execução"
    )
    hu_markdown: Optional[str] = Field(
        None,
        description="Saída da skill gerar-historia-usuario no template Markdown da própria skill",
    )
    rf_markdown: Optional[str] = Field(
        None,
        description="Saída da skill gerar-requisito-funcional no template Markdown da própria skill",
    )
    rnf_markdown: Optional[str] = Field(
        None,
        description="Saída da skill gerar-requisito-nao-funcional no template Markdown da própria skill",
    )
    rn_markdown: Optional[str] = Field(
        None,
        description="Saída da skill gerar-regra-negocio no template Markdown da própria skill",
    )
    uc_markdown: Optional[str] = Field(
        None,
        description="Saída da skill gerar-caso-uso no template Markdown da própria skill",
    )
    glossary_markdown: Optional[str] = Field(
        None,
        description="Resumo do glossário técnico quando aplicável",
    )
    doubt_generated: bool = Field(
        False, description="Indica se houve geração de Doubt Artifact"
    )
    summary: Optional[str] = Field(
        None, description="Resumo executivo do processamento"
    )

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value):
        if value is None:
            return "concluido"
        if not isinstance(value, str):
            return value

        normalized = value.strip().lower()
        success_values = {"ok", "done", "completed", "success", "sucesso", "concluido"}
        blocked_values = {"blocked", "bloqueado", "block", "error", "erro"}

        if normalized in success_values:
            return "concluido"
        if normalized in blocked_values:
            return "bloqueado"
        return value
