"""Schemas de saída do TacoArchitectAgent.

Define a estrutura de uma jornada de exercícios encadeados,
prontos para inserção direta no banco de dados do TACO.
"""

from pydantic import BaseModel, Field


class Exemplo(BaseModel):
    """Par de entrada/saída executável para teste automático."""

    stdin: str = Field(description="Entrada fornecida ao programa")
    stdout: str = Field(description="Saída esperada do programa")


class Exercicio(BaseModel):
    """Um exercício completo da jornada, pronto para o banco do TACO."""

    ordem: int = Field(description="Posição na sequência (1-indexed)")
    titulo: str = Field(description="Título curto e descritivo do exercício")
    enunciado: str = Field(
        description=(
            "Enunciado completo em Markdown rico (com listas, blocos de código, "
            "ênfase). Deve ser autocontido e claro para o aluno."
        )
    )
    dificuldade: str = Field(description="'easy' | 'medium' | 'hard'")
    tags: list[str] = Field(description="Tags de conceitos cobertos")
    bibliotecas_permitidas: list[str] = Field(
        default_factory=list,
        description="Bibliotecas Python permitidas além da stdlib",
    )
    formato_entrada: str = Field(description="Descrição do formato de stdin")
    formato_saida: str = Field(description="Descrição do formato de stdout")
    exemplos: list[Exemplo] = Field(
        description="Pelo menos 2 exemplos executáveis de entrada/saída"
    )
    objetivo_pedagogico: str = Field(
        description="Conceito ou habilidade que este exercício visa desenvolver"
    )
    depende_de: list[int] = Field(
        default_factory=list,
        description="Lista de números de ordem dos exercícios pré-requisito",
    )


class JornadaOutput(BaseModel):
    """Envelope de saída com a jornada completa de exercícios."""

    titulo_jornada: str = Field(description="Título descritivo da jornada")
    racional_pedagogico: str = Field(
        description=(
            "Explicação da lógica pedagógica da sequência: por que os "
            "exercícios estão nessa ordem e como se conectam"
        )
    )
    exercicios: list[Exercicio] = Field(
        description="Lista ordenada de exercícios encadeados"
    )
