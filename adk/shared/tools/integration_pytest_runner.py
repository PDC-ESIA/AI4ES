"""Execução em lote dos arquivos criados pelo construtor de testes de integração."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from shared.tools.pytest_runner import executar_pytest_tool


class ExecutarTestesIntegracaoInput(BaseModel):
    """Contrato de entrada da tool de execução de testes de integração."""

    arquivos_gerados: list[str] = Field(
        min_length=1,
        description=(
            "Caminhos dos arquivos pytest gerados em "
            "workspace_output/tests/integration_tests/."
        ),
    )

    @field_validator("arquivos_gerados")
    @classmethod
    def validar_caminhos(cls, caminhos: list[str]) -> list[str]:
        normalizados = [caminho.strip() for caminho in caminhos if caminho.strip()]
        if len(normalizados) != len(caminhos):
            raise ValueError("arquivos_gerados deve conter apenas caminhos não vazios.")
        return normalizados


class ResumoExecucaoIntegracao(BaseModel):
    """Contadores consolidados da execução."""

    total: int = Field(ge=0)
    sucessos: int = Field(ge=0)
    falhas: int = Field(ge=0)


class ExecutarTestesIntegracaoOutput(BaseModel):
    """Contrato de saída da tool de execução de testes de integração."""

    status: Literal["sucesso", "falha"]
    tipo_teste: Literal["integracao"]
    resumo: ResumoExecucaoIntegracao
    resultados: list[dict[str, Any]] = Field(
        description="Relatórios individuais produzidos por executar_pytest_tool."
    )


def executar_testes_de_integracao(arquivos_gerados: list[str]) -> dict[str, Any]:
    """Executa testes de integração e retorna um relatório Pydantic consolidado.

    Entrada: ``ExecutarTestesIntegracaoInput``.
    Saída: ``ExecutarTestesIntegracaoOutput``.
    """
    entrada = ExecutarTestesIntegracaoInput(arquivos_gerados=arquivos_gerados)
    resultados = [executar_pytest_tool(caminho) for caminho in entrada.arquivos_gerados]
    sucessos = sum(1 for resultado in resultados if resultado.get("status") == "sucesso")
    saida = ExecutarTestesIntegracaoOutput(
        status="sucesso" if sucessos == len(resultados) else "falha",
        tipo_teste="integracao",
        resumo=ResumoExecucaoIntegracao(
            total=len(resultados),
            sucessos=sucessos,
            falhas=len(resultados) - sucessos,
        ),
        resultados=resultados,
    )
    return saida.model_dump()
