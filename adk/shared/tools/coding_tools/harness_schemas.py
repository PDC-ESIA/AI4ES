"""Schemas Pydantic da saída do harness de execução.

O harness descreve *o que aconteceu* ao preparar, implantar e executar o
artefato gerado — organizado em estágios. Ele NÃO emite veredito de
aprovação/reprovação: o `ExecutionReport` carrega apenas evidências e o status
técnico de cada estágio. O julgamento fica a cargo do implementation_validator
(ver `implementation_validator/schemas.py`).

Estes schemas são propriedade do harness (ferramenta compartilhada) e vivem
junto dele em `shared/tools/coding_tools/`, sem acoplar a nenhum pacote de
agente. Nomes de campos em inglês; descrições/enums/comentários em português.
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


class TestOutcome(str, Enum):
    """Desfecho de UM teste individual da suíte do artefato.

    Distinto de `StageStatus`, que fala do estágio inteiro: aqui a unidade é um
    teste nomeado, e o vocabulário existe para casar o resultado da suíte com o
    critério de aceite que aquele teste comprova (o mapa `acceptance_tests` do
    manifesto).

    `PULADO` cobre tanto o skip explícito quanto o `xfail` — em ambos o teste
    não comprovou o comportamento, e essa é a leitura que importa para
    cobertura. Um `xpass` conta como `PASSOU`: o comportamento funcionou, ainda
    que a suíte esperasse o contrário.
    """

    PASSOU = "passou"
    FALHOU = "falhou"
    ERRO = "erro"
    PULADO = "pulado"


class CriterionOutcome(str, Enum):
    """Estado da avaliação de um critério de aceite.

    O harness atual coleta evidências técnicas, mas deliberadamente não infere
    atendimento semântico a partir dos testes escritos pelo próprio coder.
    `NAO_AVALIADO` é, portanto, o único estado emitido para relatórios novos.

    Os demais valores permanecem para leitura compatível de relatórios antigos:
      - `ATENDIDO` / `NAO_ATENDIDO`: uma versão anterior inferiu atendimento a
        partir de testes vinculados.
      - `SEM_TESTE_MAPEADO`: o critério era automatizável e o coder não declarou
        teste nenhum.
      - `TESTE_NAO_EXECUTADO`: o vínculo foi declarado, mas nenhum resultado
        para aquele teste apareceu na saída da suíte.
      - `NAO_AUTOMATIZAVEL`: está fora do que se consegue comprovar com teste de
        código.
    """

    NAO_AVALIADO = "nao_avaliado"
    ATENDIDO = "atendido"
    NAO_ATENDIDO = "nao_atendido"
    SEM_TESTE_MAPEADO = "sem_teste_mapeado"
    TESTE_NAO_EXECUTADO = "teste_nao_executado"
    NAO_AUTOMATIZAVEL = "nao_automatizavel"


# Resultados que representam uma verificação CONCLUÍDA — os únicos que entram no
# numerador/denominador da nota de aceite. O harness atual não emite nenhum
# deles (ver `NAO_AVALIADO`), então na prática só relatórios antigos os trazem.
OUTCOMES_DECIDIDOS = frozenset(
    {CriterionOutcome.ATENDIDO, CriterionOutcome.NAO_ATENDIDO}
)

# Lacunas que o coder podia fechar escrevendo ou corrigindo teste — base do
# aviso de cobertura do executor. `NAO_AUTOMATIZAVEL` ficava de fora de
# propósito: cobrar dele o impossível é a patologia que este desenho existe para
# não repetir.
#
# Com o harness atual nenhum desses valores é emitido, então o aviso não dispara
# — e isso é deliberado: mais testes do coder não convertem critério em aceite,
# logo uma rodada extra pedindo teste seria loop sem desfecho. O conjunto segue
# aqui para os relatórios antigos e para quando a avaliação de aceite voltar.
OUTCOMES_ENDERECAVEIS = frozenset(
    {CriterionOutcome.SEM_TESTE_MAPEADO, CriterionOutcome.TESTE_NAO_EXECUTADO}
)


class CriterionEvidence(BaseModel):
    """Evidência bruta coletada para um critério de aceite, sem veredito.

    Registra o que foi verificado e o que foi observado. A conclusão sobre se o
    Work Item deve ser aprovado é responsabilidade do implementation_validator.
    """

    criterion: str = Field(description="Critério de aceite ao qual a evidência se refere")
    check_performed: str = Field(description="Verificação/comando executado para coletar a evidência")
    observed: str = Field(description="O que foi efetivamente observado durante a execução")
    checkable: bool = Field(
        description=(
            "Houve sondagem determinística do harness (ex.: requisição HTTP) "
            "registrada em `observed`. Não significa atendimento: quem julga o "
            "critério é o validador"
        )
    )
    criterion_id: str = Field(
        default="",
        description=(
            "Id do critério na Task (CA-01...). Vazio só em reports antigos, "
            "gerados antes de o critério ter identidade."
        ),
    )
    automatable: bool = Field(
        default=True,
        description=(
            "Classificação declarada na Task: o critério é comprovável por "
            "teste automatizado com as capacidades atuais do fluxo?"
        ),
    )
    outcome: CriterionOutcome = Field(
        default=CriterionOutcome.NAO_AVALIADO,
        description="Estado da avaliação do critério; não inferido dos testes técnicos",
    )
    linked_tests: list[str] = Field(
        default_factory=list,
        description="Testes declarados no manifesto como cobertura deste critério",
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
        description="Caminho do relatório .json (ExecutionReport) persistido no workspace",
    )
    total_duration_seconds: float = Field(
        default=0.0,
        description="Duração total da execução em segundos",
    )
