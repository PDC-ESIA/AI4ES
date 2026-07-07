from pydantic import BaseModel, Field
from typing import List, Optional

class UserStory(BaseModel):
    id: str = Field(..., description="Identificador da HU (ex: HU-001)")
    title: str = Field(..., description="Título conciso da funcionalidade")
    persona: str = Field(..., description="O 'Quem' (Ex: Como Administrador)")
    action: str = Field(..., description="O 'O quê' (Ex: Quero visualizar relatórios)")
    value: str = Field(..., description="O 'Porquê/Valor' (Ex: Para tomar decisões baseadas em dados)")
    acceptance_criteria: List[str] = Field(..., description="Lista de critérios de aceitação testáveis")

class FunctionalRequirement(BaseModel):
    id: str = Field(..., description="Identificador do RF (ex: RF-001)")
    title: str = Field(..., description="Título do requisito")
    description: str = Field(..., description="Descrição detalhada e não ambígua")
    priority: str = Field(..., description="Prioridade (Alta, Média, Baixa)")
    hu_parent: Optional[str] = Field(None, description="ID da HU relacionada para rastreabilidade")

class NonFunctionalRequirement(BaseModel):
    id: str = Field(..., description="Identificador do RNF (ex: RNF-001)")
    title: str = Field(..., description="Título do requisito")
    description: str = Field(..., description="Descrição (Performance, Usabilidade, Segurança, etc)")
    category: str = Field(..., description="Categoria conforme ISO 25010")

class BusinessRule(BaseModel):
    id: str = Field(..., description="Identificador da RN (ex: RN-001)")
    description: str = Field(..., description="Regra de negócio ou restrição lógica")

class GlossaryTerm(BaseModel):
    term: str = Field(..., description="Termo técnico ou de domínio")
    definition: str = Field(..., description="Definição clara do termo")
    source: str = Field(..., description="Onde o termo foi encontrado no documento")

class UseCase(BaseModel):
    id: str = Field(..., description="Identificador do UC (ex: UC-001)")
    title: str = Field(..., description="Título do caso de uso")
    actor: str = Field(..., description="Ator principal")
    description: str = Field(..., description="Breve descrição do fluxo")
    pre_conditions: List[str] = Field(default_factory=list, description="Pré-condições para o início")
    main_flow: List[str] = Field(..., description="Passos do fluxo principal")
    post_conditions: List[str] = Field(default_factory=list, description="Estados finais esperados")

class AnalystOutput(BaseModel):
    status: str = Field(..., description="Status da execução: 'concluido' ou 'bloqueado'")
    user_stories: List[UserStory] = Field(default_factory=list)
    functional_requirements: List[FunctionalRequirement] = Field(default_factory=list)
    non_functional_requirements: List[NonFunctionalRequirement] = Field(default_factory=list)
    use_cases: List[UseCase] = Field(default_factory=list)
    business_rules: List[BusinessRule] = Field(default_factory=list)
    glossary: List[GlossaryTerm] = Field(default_factory=list)
    doubt_generated: bool = Field(False, description="Indica se houve geração de Doubt Artifact")
    summary: str = Field(..., description="Resumo executivo do processamento")
