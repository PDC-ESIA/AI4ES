"""Schemas Pydantic para a saída estruturada do executor (harness de execução).

O executor descreve *o que aconteceu* ao preparar, implantar e executar o
artefato gerado — organizado em estágios. Ele NÃO emite veredito de
aprovação/reprovação: o `ExecutionReport` carrega apenas evidências e o status
técnico de cada estágio. O julgamento fica a cargo do implementation_validator
(ver `implementation_validator/schemas.py`).

Nomes de campos em inglês; descrições/enums/comentários em português, seguindo
o padrão de `reviewer/schemas.py` e `validator/schemas.py`.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class StageStatus(str, Enum):
    """Resultado técnico de um estágio de execução (sem juízo de aprovação)."""

    SUCESSO = "sucesso"  # estágio concluído conforme esperado
    FALHA = "falha"  # estágio executou mas o resultado não foi o esperado
    ERRO = "erro"  # estágio abortou por erro inesperado (ex.: exceção, crash)
    PULADO = "pulado"  # estágio não executado (pré-requisito ausente, etc.)


class StageName(str, Enum):
    """Os nove estágios do harness de execução, em ordem de pipeline."""

    PREPARACAO_AMBIENTE = "preparacao_ambiente"
    IMPLANTACAO_ARTEFATO = "implantacao_artefato"
    COLETA_LOGS_IMPLANTACAO = "coleta_logs_implantacao"
    INICIALIZACAO_APLICACAO = "inicializacao_aplicacao"
    COLETA_LOGS_EXECUCAO = "coleta_logs_execucao"
    TESTES_AUTOMATIZADOS = "testes_automatizados"
    VALIDACOES_WORK_ITEM = "validacoes_work_item"
    CONSOLIDACAO_EVIDENCIAS = "consolidacao_evidencias"
    GERACAO_RELATORIO = "geracao_relatorio"


class CriterionEvidence(BaseModel):
    """Evidência bruta coletada para um critério de aceite, sem veredito.

    Registra o que foi verificado e o que foi observado. A conclusão sobre se o
    critério foi atendido é responsabilidade do implementation_validator.
    """

    criterion: str = Field(description="Critério de aceite ao qual a evidência se refere")
    check_performed: str = Field(description="Verificação/comando executado para coletar a evidência")
    observed: str = Field(description="O que foi efetivamente observado durante a execução")
    checkable: bool = Field(
        description="Indica se o critério pôde ser verificado automaticamente pelo harness"
    )


class StageResult(BaseModel):
    """Resultado de um único estágio do harness de execução."""

    stage: StageName = Field(description="Estágio ao qual este resultado se refere")
    status: StageStatus = Field(description="Status técnico do estágio")
    duration_seconds: float = Field(description="Duração do estágio em segundos")
    summary: str = Field(description="Resumo do que aconteceu no estágio")
    evidence: dict = Field(
        default_factory=dict,
        description="Evidências brutas do estágio (logs, caminhos, saídas de comando)",
    )
    error_code: Optional[str] = Field(
        default=None,
        description="Código do erro quando o estágio falhou/erro; None se sucesso",
    )


class ExecutionReport(BaseModel):
    """Relatório consolidado da execução do artefato (apenas evidências).

    Descreve toda a passagem pelo harness — estágios percorridos e evidências
    por critério — sem nenhum campo de veredito. A decisão de aprovar ou
    reprovar pertence exclusivamente ao `ValidationVerdict`.
    """

    work_item_id: str = Field(description="Identificador do work item executado")
    iteration: int = Field(description="Iteração do loop de execução (começa em 1)")
    generated_at: str = Field(description="Timestamp ISO 8601 de geração do relatório")
    acceptance_criteria: list[str] = Field(
        default_factory=list,
        description="Critérios de aceite do work item, como recebidos",
    )
    overall_status: StageStatus = Field(
        description="Status técnico agregado da execução (não é veredito de aprovação)"
    )
    stages: list[StageResult] = Field(
        default_factory=list,
        description="Resultado de cada estágio percorrido pelo harness",
    )
    criteria_evidence: list[CriterionEvidence] = Field(
        default_factory=list,
        description="Evidências coletadas por critério de aceite",
    )
    report_path: Optional[str] = Field(
        default=None,
        description="Caminho do relatório .md persistido no workspace",
    )
    total_duration_seconds: float = Field(
        default=0.0,
        description="Duração total da execução em segundos",
    )
