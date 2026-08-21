"""Schemas Pydantic do Agente de Requisitos (Time 1).

Estes modelos são a primeira barreira contra alucinação: em vez de aceitar
qualquer string, restringem o espaço de valores possíveis.

Decisões de projeto:
- `extra="forbid"`: campo inventado pelo LLM derruba a validação em vez de
  passar despercebido.
- IDs com `pattern`: cada tipo de artefato só aceita seu próprio prefixo,
  o que impede um RF de se apresentar como HU.
- `Literal` para rótulos fechados (prioridade, categoria, status), com
  normalização prévia de caixa e acento para não gerar falso negativo
  quando o LLM escreve "media" em vez de "Média".

Validações que dependem de contexto externo (cruzamento com os arquivos
efetivamente gravados, integridade referencial entre coleções) ficam em
`validation.py` — aqui só entra o que é verificável olhando um único objeto.
"""

from __future__ import annotations

import re
import unicodedata
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Padrões de ID por tipo de artefato.
PADRAO_ID_HU = r"^HU-\d{3}$"
PADRAO_ID_RF = r"^RF-\d{3}$"
PADRAO_ID_RNF = r"^RNF-\d{3}$"
PADRAO_ID_RN = r"^RN-\d{3}$"
PADRAO_ID_UC = r"^UC-\d{3}$"
PADRAO_ID_QUALQUER = r"^(HU|RF|RNF|RN|UC)-\d{3}$"

Prioridade = Literal["Alta", "Média", "Baixa", "Não identificado"]

# União das categorias citadas no few-shot com as características da ISO 25010.
CategoriaRNF = Literal[
    "Desempenho",
    "Segurança",
    "Disponibilidade",
    "Usabilidade",
    "Manutenibilidade",
    "Escalabilidade",
    "Confiabilidade",
    "Portabilidade",
    "Compatibilidade",
    "Interoperabilidade",
    "Implantação",
    "Adequação Funcional",
]

StatusExecucao = Literal["concluido", "bloqueado"]


def chave_normalizada(valor: str) -> str:
    """Normaliza um rótulo para comparação: sem acento, minúsculo, sem bordas."""
    sem_acento = unicodedata.normalize("NFKD", valor.strip().lower())
    return sem_acento.encode("ascii", "ignore").decode("ascii")


def _normalizador(mapa: dict[str, str]):
    """Cria um validador `mode='before'` que canoniza rótulos conhecidos.

    Valores desconhecidos passam intactos para que o `Literal` os rejeite
    com uma mensagem de erro útil.
    """

    def _aplicar(valor: object) -> object:
        if not isinstance(valor, str):
            return valor
        return mapa.get(chave_normalizada(valor), valor)

    return _aplicar


_MAPA_PRIORIDADE = {
    "alta": "Alta",
    "media": "Média",
    "baixa": "Baixa",
    "nao identificado": "Não identificado",
}

_MAPA_CATEGORIA = {
    "desempenho": "Desempenho",
    "performance": "Desempenho",
    "eficiencia de desempenho": "Desempenho",
    "seguranca": "Segurança",
    "disponibilidade": "Disponibilidade",
    "usabilidade": "Usabilidade",
    "manutenibilidade": "Manutenibilidade",
    "escalabilidade": "Escalabilidade",
    "confiabilidade": "Confiabilidade",
    "portabilidade": "Portabilidade",
    "compatibilidade": "Compatibilidade",
    "interoperabilidade": "Interoperabilidade",
    "implantacao": "Implantação",
    "instalacao": "Implantação",
    "adequacao funcional": "Adequação Funcional",
}

_MAPA_STATUS = {
    "concluido": "concluido",
    "bloqueado": "bloqueado",
    "completo": "concluido",
    "finalizado": "concluido",
}


class _Base(BaseModel):
    """Base comum: proíbe campos não declarados no schema."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class UserStory(_Base):
    id: str = Field(..., pattern=PADRAO_ID_HU, description="Identificador da HU (ex: HU-001)")
    title: str = Field(..., min_length=3, description="Título conciso da funcionalidade")
    persona: str = Field(..., min_length=2, description="O 'Quem' (Ex: Como Administrador)")
    action: str = Field(..., min_length=3, description="O 'O quê' (Ex: Quero visualizar relatórios)")
    value: str = Field(..., min_length=3, description="O 'Porquê/Valor' (Ex: Para tomar decisões baseadas em dados)")
    acceptance_criteria: List[str] = Field(..., min_length=1, description="Lista de critérios de aceitação testáveis")


class FunctionalRequirement(_Base):
    id: str = Field(..., pattern=PADRAO_ID_RF, description="Identificador do RF (ex: RF-001)")
    title: str = Field(..., min_length=3, description="Título do requisito")
    description: str = Field(..., min_length=10, description="Descrição detalhada e não ambígua")
    priority: Prioridade = Field(..., description="Prioridade (Alta, Média, Baixa)")
    hu_parent: Optional[str] = Field(None, description="ID da HU relacionada para rastreabilidade")

    _norm_priority = field_validator("priority", mode="before")(_normalizador(_MAPA_PRIORIDADE))

    @field_validator("hu_parent", mode="before")
    @classmethod
    def _hu_parent_ausente_vira_none(cls, valor: object) -> object:
        """Aceita ausência de HU de origem expressa como texto livre."""
        if isinstance(valor, str) and chave_normalizada(valor) in {
            "", "nao identificado", "nao aplicavel", "n/a", "none", "null", "-",
        }:
            return None
        return valor

    @field_validator("hu_parent")
    @classmethod
    def _hu_parent_bem_formado(cls, valor: Optional[str]) -> Optional[str]:
        if valor is not None and not re.fullmatch(PADRAO_ID_HU, valor):
            raise ValueError(f"hu_parent '{valor}' não segue o padrão HU-999")
        return valor


class NonFunctionalRequirement(_Base):
    id: str = Field(..., pattern=PADRAO_ID_RNF, description="Identificador do RNF (ex: RNF-001)")
    title: str = Field(..., min_length=3, description="Título do requisito")
    description: str = Field(..., min_length=10, description="Descrição (Performance, Usabilidade, Segurança, etc)")
    category: CategoriaRNF = Field(..., description="Categoria conforme ISO 25010")

    _norm_category = field_validator("category", mode="before")(_normalizador(_MAPA_CATEGORIA))


class BusinessRule(_Base):
    id: str = Field(..., pattern=PADRAO_ID_RN, description="Identificador da RN (ex: RN-001)")
    description: str = Field(..., min_length=10, description="Regra de negócio ou restrição lógica")


class GlossaryTerm(_Base):
    term: str = Field(..., min_length=1, description="Termo técnico ou de domínio")
    definition: str = Field(..., min_length=10, description="Definição clara do termo")
    source: str = Field(..., min_length=1, description="Onde o termo foi encontrado no documento")


class UseCase(_Base):
    id: str = Field(..., pattern=PADRAO_ID_UC, description="Identificador do UC (ex: UC-001)")
    title: str = Field(..., min_length=3, description="Título do caso de uso")
    actor: str = Field(..., min_length=2, description="Ator principal")
    description: str = Field(..., min_length=10, description="Breve descrição do fluxo")
    pre_conditions: List[str] = Field(default_factory=list, description="Pré-condições para o início")
    main_flow: List[str] = Field(..., min_length=1, description="Passos do fluxo principal")
    post_conditions: List[str] = Field(default_factory=list, description="Estados finais esperados")


# A matriz é escrita livremente pelo LLM: nenhum campo abaixo é restringido, para
# não reprovar a fase inteira por um vocabulário que o modelo enriqueceu.
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
    markdown: str = Field(..., description="Representação completa da matriz em formato Markdown (tabela), persistida via tool_salvar_artefato_requisito com tipo RASTREABILIDADE (não mapeado explicitamente pela tool, será salvo em Outros/ do repositório estruturado)")


class AnalystOutput(_Base):
    status: StatusExecucao = Field(..., description="Status da execução: 'concluido' ou 'bloqueado'")
    user_stories: List[UserStory] = Field(default_factory=list)
    functional_requirements: List[FunctionalRequirement] = Field(default_factory=list)
    non_functional_requirements: List[NonFunctionalRequirement] = Field(default_factory=list)
    use_cases: List[UseCase] = Field(default_factory=list)
    business_rules: List[BusinessRule] = Field(
        ...,
        min_length=1,
        description=(
            "Regras de negócio da fase. Obrigatória e não-vazia: a RN é o "
            "artefato que o modelo mais deixa escapar, porque a entrada "
            "raramente traz uma seção rotulada como tal. Exigir ao menos um "
            "item faz a ausência virar erro de schema na auditoria em vez de "
            "passar como coleção opcional vazia."
        ),
    )
    glossary: List[GlossaryTerm] = Field(default_factory=list)
    traceability_matrix: Optional[TraceabilityMatrix] = Field(
        None,
        description=(
            "Matriz de rastreabilidade bidirecional (forward/backward) gerada ao "
            "final do fluxo pelo próprio agente, persistida em MD e JSON"
        ),
    )
    doubt_generated: bool = Field(False, description="Indica se houve geração de Doubt Artifact")
    summary: str = Field(..., min_length=10, description="Resumo executivo do processamento")

    _norm_status = field_validator("status", mode="before")(_normalizador(_MAPA_STATUS))
