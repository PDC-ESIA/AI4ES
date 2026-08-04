"""Schemas de saída do TacoReviewerAgent.

Define a estrutura de feedback pedagógico formativo para submissões
de alunos, incluindo pontos fortes, problemas, sugestões e rubrica.
"""

from pydantic import BaseModel, Field


class Problema(BaseModel):
    """Issue individual identificada na submissão do aluno."""

    tipo: str = Field(
        description="Categoria do problema: 'estilo' | 'corretude' | 'complexidade' | 'lógica'"
    )
    gravidade: str = Field(
        description="Nível de gravidade: 'alta' | 'média' | 'baixa'"
    )
    descricao: str = Field(
        description=(
            "Descrição formativa do problema — aponta o que está errado "
            "sem entregar a solução pronta"
        )
    )
    linha_aproximada: int | None = Field(
        default=None,
        description="Linha aproximada do código onde o problema ocorre",
    )


class Rubrica(BaseModel):
    """Avaliação quantitativa em 3 eixos pedagógicos (0-100)."""

    corretude: int = Field(description="Nota de corretude funcional (0-100)")
    estilo: int = Field(description="Nota de estilo e idiomaticidade Python (0-100)")
    eficiencia: int = Field(description="Nota de eficiência algorítmica (0-100)")


class TacoReviewOutput(BaseModel):
    """Saída completa do review pedagógico de uma submissão."""

    pontos_fortes: list[str] = Field(
        description="Lista de aspectos positivos da submissão"
    )
    problemas_encontrados: list[Problema] = Field(
        description="Lista de problemas identificados com tipo e gravidade"
    )
    sugestoes_de_melhoria: list[str] = Field(
        description=(
            "Sugestões formativas: perguntas norteadoras e direções "
            "de investigação, nunca respostas prontas"
        )
    )
    avaliacao_geral: Rubrica = Field(
        description="Rubrica quantitativa em 3 eixos"
    )
