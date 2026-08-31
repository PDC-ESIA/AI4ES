"""Nota de aceite (0..1) e cobertura de critérios — cálculo determinístico.

Responde a uma pergunta que a nota de progresso (`progress_score.py`)
deliberadamente NÃO responde: "dos critérios de aceite que dava para verificar,
quantos a entrega atende?".

As duas notas medem coisas diferentes e por isso vivem separadas:

  - `progress_score`  → "o sistema gerado funciona, e o quanto?" (ambiente,
    build, inicialização, testes). É ela que a `loop_policy` usa para decidir
    continuidade, e nada aqui pode contaminá-la.
  - este módulo        → "a entrega faz o que o Work Item pediu?", medido só
    sobre o que foi COMPROVADO por teste vinculado ao critério.

## Por que a nota exclui os critérios não comprovados

Uma versão anterior tinha um degrau `CRITERIOS_ATENDIDOS` dentro da nota
técnica, alimentado pelo julgamento que o LLM fazia de cada critério. Como o
harness não instrumenta jornada de interface, esse julgamento era honestamente
`inconclusivo` rodada após rodada, o degrau ficava travado em zero, e a nota
teto caía para ~0.65 — nenhuma task jamais aprovava. O degrau media a CEGUEIRA
do validador, não a qualidade do código (ver `progress_score.py`).

A correção é separar as duas perguntas em dois números:

    nota      = atendidos / (atendidos + nao_atendidos)   ← só o que foi decidido
    cobertura = (atendidos + nao_atendidos) / total       ← quanto deu para decidir

Um critério que ninguém conseguiu verificar sai do numerador E do denominador da
NOTA, e reaparece na COBERTURA. Assim a nota nunca pune a entrega por um limite
da ferramenta — e o limite, em vez de sumir, ganha um número próprio.

Ler a cobertura: ela é uma métrica sobre o HARNESS e sobre a redação dos
critérios, não sobre o código gerado. Cobertura baixa é item de backlog da
plataforma (falta instrumentação) ou da autoria da task (critério não
verificável), nunca defeito do artefato.

## Nada aqui pede nada a um LLM

Como em `progress_score`, a entrada é só o `ExecutionReport` — o resultado
determinístico que o estágio 7 derivou dos testes vinculados. Os
`criteria_verdicts` do `implementation_validator` NÃO entram: são julgamento
semântico, e um número objetivo não pode depender de algo que varia entre
rodadas para a mesma evidência.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from shared.tools.coding_tools.harness_schemas import (
    OUTCOMES_ENDERECAVEIS,
    CriterionOutcome,
)

# Casas decimais — mesma razão de `progress_score`: evitar que ruído de ponto
# flutuante apareça no histórico e no relatório.
_CASAS_DECIMAIS = 6

# Chaves de ciclo publicadas no session state. Exportadas para o `TaskIterator`
# limpá-las entre tasks: sem isso, a task seguinte herdaria a nota de aceite da
# anterior — e, pior, o aviso de cobertura já consumido, que nunca mais seria
# emitido para nenhuma outra task.
CHAVE_ACEITE = "acceptance_score"
CHAVE_AVISO_COBERTURA = "acceptance_coverage_notice_used"

CHAVES_DE_CICLO: tuple[str, ...] = (CHAVE_ACEITE, CHAVE_AVISO_COBERTURA)


@dataclass(frozen=True)
class NotaAceite:
    """Resultado do cálculo, com o detalhamento que o torna auditável.

    Attributes:
        nota: `atendidos / (atendidos + nao_atendidos)` em [0, 1], ou `None`
            quando nenhum critério pôde ser decidido — o que é diferente de
            zero: zero significa "verifiquei e não atende"; `None` significa
            "não consegui verificar".
        cobertura: Fração dos critérios que puderam ser decididos, em [0, 1].
        total: Quantos critérios a Task declara.
        por_resultado: Contagem por `CriterionOutcome`, para o relatório.
        criterios_enderecaveis: Ids dos critérios cuja falta de cobertura o
            CODER pode fechar (sem teste declarado, ou teste declarado que não
            executou). Exclui os não automatizáveis de propósito.
    """

    nota: Optional[float]
    cobertura: float
    total: int
    por_resultado: dict[str, int]
    criterios_enderecaveis: list[str]

    @property
    def atendidos(self) -> int:
        return self.por_resultado.get(CriterionOutcome.ATENDIDO.value, 0)

    @property
    def nao_atendidos(self) -> int:
        return self.por_resultado.get(CriterionOutcome.NAO_ATENDIDO.value, 0)

    @property
    def decididos(self) -> int:
        return self.atendidos + self.nao_atendidos

    def como_dict(self) -> dict:
        """Forma serializável para o session state e para o relatório."""
        return {
            "nota": self.nota,
            "cobertura": self.cobertura,
            "total": self.total,
            "atendidos": self.atendidos,
            "nao_atendidos": self.nao_atendidos,
            "decididos": self.decididos,
            "por_resultado": dict(self.por_resultado),
            "criterios_enderecaveis": list(self.criterios_enderecaveis),
        }


def _evidencias(execution_report: Any) -> list[dict]:
    """Extrai `criteria_evidence` do report, ignorando o que não for utilizável."""
    if not isinstance(execution_report, dict):
        return []
    bruto = execution_report.get("criteria_evidence")
    if not isinstance(bruto, list):
        return []
    return [e for e in bruto if isinstance(e, dict)]


def _outcome(evidencia: dict) -> Optional[CriterionOutcome]:
    """O resultado da evidência, ou `None` se ausente/desconhecido.

    Report antigo (anterior ao campo) e valor fora do enum caem em `None` e são
    contados como não decididos — a direção segura: uma evidência que não sei
    ler nunca vira atendimento.
    """
    bruto = evidencia.get("outcome")
    if not isinstance(bruto, str):
        return None
    try:
        return CriterionOutcome(bruto)
    except ValueError:
        return None


def calcular_nota_aceite(execution_report: Any) -> NotaAceite:
    """Calcula a nota de aceite e a cobertura de UMA execução.

    Args:
        execution_report: `ExecutionReport` do harness, como dict. Entradas
            inválidas degradam para "nada foi verificado" em vez de levantar —
            o chamador é um callback no meio do fluxo, e derrubá-lo custaria a
            rodada inteira (mesma postura de `progress_score.calcular_nota`).

    Returns:
        `NotaAceite`. Com zero critérios, devolve `nota=None` e `cobertura=0.0`:
        não há dimensão de aceite a medir, e quem compõe a nota final trata isso
        redistribuindo o peso (ver `nota_unificada`).
    """
    evidencias = _evidencias(execution_report)

    por_resultado: dict[str, int] = {}
    enderecaveis: list[str] = []
    atendidos = nao_atendidos = 0

    for evidencia in evidencias:
        outcome = _outcome(evidencia)
        chave = outcome.value if outcome is not None else "desconhecido"
        por_resultado[chave] = por_resultado.get(chave, 0) + 1

        if outcome is CriterionOutcome.ATENDIDO:
            atendidos += 1
        elif outcome is CriterionOutcome.NAO_ATENDIDO:
            nao_atendidos += 1
        elif outcome in OUTCOMES_ENDERECAVEIS:
            identificador = evidencia.get("criterion_id")
            enderecaveis.append(
                identificador
                if isinstance(identificador, str) and identificador
                else str(evidencia.get("criterion", ""))
            )

    total = len(evidencias)
    decididos = atendidos + nao_atendidos

    return NotaAceite(
        nota=(round(atendidos / decididos, _CASAS_DECIMAIS) if decididos else None),
        cobertura=(round(decididos / total, _CASAS_DECIMAIS) if total else 0.0),
        total=total,
        por_resultado=por_resultado,
        criterios_enderecaveis=enderecaveis,
    )


# A composição `S = 0.65·técnica + 0.35·aceite` (`nota_unificada`/`PESO_TECNICO`)
# viveu aqui e foi REMOVIDA na PoC da issue #394. Ela existia porque o aceite não
# tinha como ser medido de verdade e precisava de uma dimensão separada, ponderada
# por fora, para não capar a nota técnica.
#
# Com o QA navegando a aplicação (ver `qa_criterios/`), o aceite virou evidência
# executável como qualquer outra, e passou a caber na MESMA escada de capacidades
# — como o degrau `CRITERIOS_ATENDIDOS` de `progress_score`. Duas notas
# compostas por fora eram uma duplicação da mesma ideia de ponderação, e faziam
# a `loop_policy` operar sobre uma nota que não incluía a dimensão de aceite.
#
# O que sobrou aqui é o que continua sendo só desta dimensão: a CONTAGEM (quem
# foi decidido, quem não), a COBERTURA e a lista de critérios endereçáveis.
