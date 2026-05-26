from pydantic import BaseModel, Field
from typing import List, Optional


class Component(BaseModel):
    name: str = Field(description="Nome do componente")
    responsibility: str = Field(description="Responsabilidade principal")
    dependencies: List[str] = Field(default_factory=list, description="Dependências diretas")


class Blocker(BaseModel):
    hu_id: str = Field(description="ID da HU bloqueada ex: HU-042")
    step: str = Field(description="Passo do fluxo onde ocorreu o bloqueio")
    excerpt: str = Field(description="Trecho exato da HU que gerou a dúvida")


class HUAnalysis(BaseModel):
    hu_id: str = Field(description="ID da HU ex: HU-042")
    actor: str = Field(description="Ator principal da HU")
    action: str = Field(description="Ação central que o sistema deve executar")
    diagram_type: str = Field(description="Tipo de diagrama Mermaid escolhido")
    diagram_justification: str = Field(description="Justificativa técnica da escolha")
    components: List[Component] = Field(description="Componentes identificados para o diagrama")


class ArchitectureDecision(BaseModel):
    decision_id: int
    name: str
    hu_ids: List[str]
    context: str
    chosen_alternative: str
    justification: str
    reversibility: str = Field(description="Alta | Média | Baixa")


class DesignArchitectOutput(BaseModel):
    batch_summary: str = Field(description="Visão consolidada do lote de HUs")
    decisions: List[ArchitectureDecision]
    analyses: List[HUAnalysis] = Field(description="Uma entrada por HU sem bloqueio")
    blockers: List[Blocker] = Field(default_factory=list)