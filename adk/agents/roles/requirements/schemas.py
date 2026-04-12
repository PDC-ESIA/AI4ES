from pydantic import BaseModel, Field


class PainelLogico(BaseModel):
    id_painel: str = Field(description="Identificador do painel ex.: REQ-TACO-AUTH-001")
    modulo: str = Field(description="Módulo de origem no PRD")
    titulo: str = Field(description="Título curto e acionável")
    descricao: str = Field(description="Descrição completa e autocontida")
    dependencias: list[str] = Field(default=[], description="IDs de painéis pré-requisito")
    prioridade: str = Field(description="alta, media ou baixa")
    estimativa_tokens: int = Field(default=0, description="Estimativa de tokens")
    time_responsavel: str = Field(default="time4")


class RequirementsOutput(BaseModel):
    paineis: list[PainelLogico]