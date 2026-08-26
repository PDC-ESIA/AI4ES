from pydantic import BaseModel, Field
from typing import List

class PrototypeFile(BaseModel):
    hu_id: str = Field(description="ID da HU ex: HU-042")
    filename: str = Field(description="Arquivo HTML salvo em staging ex: prototipo_HU-042.html")
    screens: List[str] = Field(default_factory=list, description="Nomes das telas/sections representadas")
    covered_acceptance_criteria: List[str] = Field(default_factory=list, description="Critérios de aceite cobertos (texto resumido)")

class Blocker(BaseModel):
    hu_id: str = Field(description="ID da HU bloqueada ex: HU-042")
    step: str = Field(description="Passo do fluxo onde ocorreu o bloqueio")
    excerpt: str = Field(description="Trecho exato da HU que gerou a dúvida")
    category: str = Field(description="Lacuna Funcional | Lacuna de UX/Interface")
    doubt_artifact_filename: str = Field(description="Nome do Doubt Artifact gerado")

class PrototypingSpecialistOutput(BaseModel):
    batch_summary: str = Field(description="Visão consolidada do lote")
    prototype_files: List[PrototypeFile] = Field(default_factory=list)
    blockers: List[Blocker] = Field(default_factory=list)
    coverage_table_markdown: str
    gap_analysis_markdown: str