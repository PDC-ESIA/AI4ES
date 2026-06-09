from pydantic import BaseModel, Field


class FinalizationOutput(BaseModel):
    requirements_met: list[str] = Field(description="IDs dos requisitos atendidos")
    files_modified: list[str] = Field(description="Arquivos criados/modificados")
    review_status: str = Field(description="APROVADO ou BLOQUEADO")
    next_steps: list[str] = Field(description="Próximos passos sugeridos")
    summary: str = Field(description="Resumo executivo em poucas linhas")
