"""Schemas de saída do TacoGabaritoAgent.

Define a estrutura de N soluções de referência com variações pedagógicas,
validação simulada contra exemplos e metadados de conceitos exercitados.
"""

from pydantic import BaseModel, Field


class ValidacaoExemplo(BaseModel):
    """Resultado da validação simulada de um exemplo de entrada/saída."""

    stdin: str = Field(description="Entrada fornecida ao programa")
    esperado: str = Field(description="Saída esperada conforme enunciado")
    obtido: str = Field(description="Saída obtida pela execução simulada do código")
    passou: bool = Field(description="True se obtido == esperado")


class SolucaoVariacao(BaseModel):
    """Uma solução de referência para uma variação específica do exercício."""

    rotulo_variacao: str = Field(
        description="Rótulo identificador da variação (ex: 'iterativa-com-listas')"
    )
    resumo_abordagem: str = Field(
        description=(
            "Explicação em texto da estratégia algorítmica, estruturas de dados "
            "usadas e complexidade esperada"
        )
    )
    codigo: str = Field(
        description=(
            "Código Python completo e executável no Pyodide. "
            "Sem placeholders, sem TODO, sem pseudocódigo."
        )
    )
    conceitos_exercitados: list[str] = Field(
        description="Lista de conceitos de Python exercitados nesta variação"
    )
    validacao_exemplos: list[ValidacaoExemplo] = Field(
        description="Validação simulada contra cada exemplo do enunciado"
    )


class GabaritoOutput(BaseModel):
    """Envelope de saída contendo todas as variações solicitadas."""

    solucoes: list[SolucaoVariacao] = Field(
        description="Lista com N soluções, uma por variação solicitada"
    )
