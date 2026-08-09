"""Schemas do ErrorReport — saída determinística do cr_executor para o coder.

Cópia local (independência de módulo — o workflow coding_review não depende do
pacote `executor/`) dos schemas de relatório de erro. Estruturalmente idênticos
aos de `executor/schemas.py`: um teste de contrato afirma essa equivalência.

O ErrorReport é montado DETERMINISTICAMENTE pelo `after_agent_callback` do
cr_executor a partir de duas fontes que já existem — o ValidationVerdict real
(state['validation']) e o ExecutionReport persistido pelo harness. O LLM do
executor não redige este objeto. Ele diz o QUE falhou e mostra a EVIDÊNCIA BRUTA
do POR QUÊ; NÃO prescreve correção (diagnóstico e mudança são do coder).
"""

from typing import Optional

from pydantic import BaseModel, Field


class FailedCriterion(BaseModel):
    """Critério de aceite que não ficou 'atendido' no veredito real.

    Cópia fiel do CriterionVerdict emitido pelo Agente de Validação — nenhum
    campo é sintetizado, reinterpretado ou acrescentado aqui.
    """

    criterion: str = Field(description="Critério de aceite, verbatim do ValidationVerdict")
    status: str = Field(description="Situação do critério: nao_atendido | inconclusivo")
    reasoning: str = Field(description="Justificativa do validador, verbatim")
    evidence_ref: Optional[str] = Field(
        default=None,
        description="Referência de evidência, verbatim do CriterionVerdict",
    )


class FailedStage(BaseModel):
    """Estágio do harness que falhou, com a evidência BRUTA que ele coletou.

    A evidência é repassada como o harness a produziu (logs, tracebacks, saída
    de testes). Nada é diagnosticado: interpretar o traceback e decidir o que
    mudar é trabalho do coder.
    """

    stage: str = Field(description="Nome do estágio, como no ExecutionReport")
    status: str = Field(description="Status técnico do estágio: falha | erro")
    error_code: Optional[str] = Field(
        default=None, description="Código do erro do estágio, quando houver"
    )
    summary: str = Field(default="", description="Resumo do estágio, verbatim do harness")
    evidence: dict = Field(
        default_factory=dict,
        description="Evidência bruta coletada pelo estágio (logs, tracebacks, saída)",
    )


class ErrorReport(BaseModel):
    """Relatório de erro entregue ao coder quando o veredito é 'reprovado'.

    Montado DETERMINISTICAMENTE pelo `after_agent_callback` do executor a partir
    de duas fontes já existentes — o ValidationVerdict real (state['validation'])
    e o ExecutionReport persistido pelo harness. O LLM do executor não redige
    este objeto.

    Contém o QUE falhou (veredito por critério) e a EVIDÊNCIA BRUTA de por quê
    (estágios em falha, com seus logs). NÃO contém prescrição de correção —
    diagnosticar causa raiz, escolher arquivos e decidir a mudança é do coder.
    """

    work_item_id: str = Field(description="Identificador do work item")
    iteration: Optional[int] = Field(
        default=None, description="Iteração do loop, como no ExecutionReport"
    )
    verdict_status: str = Field(description="Veredito global, verbatim: 'reprovado'")
    blocking_reason: Optional[str] = Field(
        default=None, description="Motivo do bloqueio, verbatim do ValidationVerdict"
    )
    failed_criteria: list[FailedCriterion] = Field(
        default_factory=list,
        description="Um item por critério não atendido/inconclusivo do veredito real",
    )
    failed_stages: list[FailedStage] = Field(
        default_factory=list,
        description="Estágios com falha/erro e sua evidência bruta",
    )
    report_path: Optional[str] = Field(
        default=None, description="Caminho do ExecutionReport completo em disco"
    )
