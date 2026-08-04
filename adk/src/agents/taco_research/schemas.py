"""Schemas de saída do TacoResearchAgent.

Define a estrutura do mapa conceitual pedagógico com ordenação
por pré-requisitos para geração de jornadas de exercícios.
"""

from pydantic import BaseModel, Field


class Conceito(BaseModel):
    """Um conceito de programação mapeado com seus pré-requisitos."""

    ordem: int = Field(description="Posição na sequência pedagógica (1-indexed)")
    nome: str = Field(description="Nome do conceito (ex: 'list comprehension')")
    descricao: str = Field(
        description="Explicação breve do conceito e por que é relevante para o escopo"
    )
    pre_requisitos: list[str] = Field(
        default_factory=list,
        description="Nomes dos conceitos anteriores que este pressupõe",
    )


class MapaConceitual(BaseModel):
    """Mapa conceitual sequencial para um escopo de aprendizado."""

    escopo: str = Field(description="Escopo original solicitado pelo professor")
    nivel_alvo: str = Field(description="Nível do público-alvo (iniciante, intermediário, avançado)")
    conceitos: list[Conceito] = Field(
        description="Lista ordenada de conceitos em ordem de pré-requisito pedagógico"
    )
