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

class TraceabilityLink(BaseModel):
    id_artefato_relacionado: str = Field(..., description="ID do artefato relacionado (ex: RF-005, HU-001, UC-002)")
    tipo_artefato_relacionado: str = Field(..., description="Tipo do artefato relacionado: HU, RF, RNF, RN ou UC")
    tipo_relacao: str = Field(
        ...,
        description=(
            "Natureza do relacionamento entre os dois artefatos. Valores esperados: "
            "'deriva_de' (rastreabilidade backward, ex: RF deriva de HU), "
            "'origina' (rastreabilidade forward, ex: HU origina RF/UC), "
            "'depende_de', 'sustenta', 'relaciona_com', 'restringe'."
        ),
    )

class TraceabilityMatrixItem(BaseModel):
    id_artefato: str = Field(..., description="ID único do artefato (HU-999, RF-999, RNF-999, RN-999, UC-999)")
    tipo: str = Field(..., description="Tipo do artefato: HU, RF, RNF, RN ou UC")
    descricao: str = Field(..., description="Descrição/título resumido do artefato")
    origem: str = Field(..., description="Trecho, seção do documento ou stakeholder que originou o artefato na entrada")
    motivo_inclusao: str = Field(..., description="Justificativa extraída/inferível da entrada e do CoT para a criação do artefato, ou 'Não identificado'")
    prioridade: str = Field(..., description="Alta, Média, Baixa ou 'Não identificado'")
    rastreabilidade_backward: List[TraceabilityLink] = Field(
        default_factory=list,
        description="Artefatos de origem deste artefato (ex: de qual HU este RF/UC/RN deriva). Vazio se não houver origem explícita."
    )
    rastreabilidade_forward: List[TraceabilityLink] = Field(
        default_factory=list,
        description="Artefatos derivados/dependentes deste artefato (ex: quais RFs/UCs/RNs esta HU originou). Vazio se não houver derivados."
    )
    criterios_aceitacao: List[str] = Field(default_factory=list, description="Referência aos CAs do artefato (ex: CA-1, CA-2); 'Não aplicável' para tipos sem CA próprio")
    casos_teste: str = Field(default="A definir", description="Placeholder obrigatório, não preenchido funcionalmente pelo agente de requisitos")
    id_agente_origem: str = Field(default="requirements_agent", description="Identificador do agente que gerou este item, para rastreabilidade multiagente")
    lacuna_detectada: bool = Field(default=False, description="True se este artefato apresenta lacuna de rastreabilidade (ex: RF sem HU de origem, HU sem RF associado)")
    lacuna_descricao: Optional[str] = Field(None, description="Descrição da lacuna encontrada, quando lacuna_detectada=True")

class TraceabilityMatrix(BaseModel):
    id: str = Field(..., description="ID da matriz (padrão PREFIXO-999, ex: MTR-001)")
    itens: List[TraceabilityMatrixItem] = Field(default_factory=list, description="Linhas da matriz, uma por artefato rastreado")
    lacunas_candidatas_doubt: List[str] = Field(
        default_factory=list,
        description="Lista de lacunas de rastreabilidade detectadas (ex: 'RF-005 sem HU de origem'), reportadas como candidatas a Doubt_Artifact"
    )
    markdown: str = Field(..., description="Representação completa da matriz em formato Markdown (tabela), para persistência em Outros/")

class AnalystOutput(BaseModel):
    status: str = Field(..., description="Status da execução: 'concluido' ou 'bloqueado'")
    user_stories: List[UserStory] = Field(default_factory=list)
    functional_requirements: List[FunctionalRequirement] = Field(default_factory=list)
    non_functional_requirements: List[NonFunctionalRequirement] = Field(default_factory=list)
    use_cases: List[UseCase] = Field(default_factory=list)
    business_rules: List[BusinessRule] = Field(default_factory=list)
    glossary: List[GlossaryTerm] = Field(default_factory=list)
    traceability_matrix: Optional[TraceabilityMatrix] = Field(
        None,
        description="Matriz de rastreabilidade bidirecional (forward/backward) gerada ao final do fluxo, persistida em MD e JSON"
    )
    doubt_generated: bool = Field(False, description="Indica se houve geração de Doubt Artifact")
    summary: str = Field(..., description="Resumo executivo do processamento")
