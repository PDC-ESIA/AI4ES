"""Curadoria dos itens destilados — veredito ternário ancorado em evidência.

## Por que existe

Esta é a resposta à **crítica 2** que recusou o PR da camada de feedforward:
*"não há curadoria, captura nem julgamento"*. Lá os itens eram escritos à mão e
entravam na base por decisão humana implícita, sem critério verificável. Aqui
todo item destilado passa por uma política determinística antes de poder chegar
ao prompt do coder.

## Por que ternário, e não aprovado/reprovado

Do **GovMem** (*When Not to Write Memory*, arXiv 2607.02579): a política de
referência emite **promover / rejeitar / precisa-de-revisão**, e os números
justificam o terceiro estado. Em 120 candidatos reais rotulados por humano a
falsa promoção cai de 0,371 para 0,032, mas o *held-out* fica em 0,111 com
**69,2% de carga de revisão** — ou seja, a maior parte do volume real é
"precisa de revisão". E na adjudicação humana de 133 candidatos vindos de
agentes de código, **nenhum** foi considerado seguro para promoção automática.

Tratar isso como binário força a escolha entre descartar quase tudo ou promover
lixo. O `REVISAR` é a quarentena: o item fica gravado, auditável e fora do
prompt até alguém olhar.

## O sinal que usamos

O ReasoningBank julga por **auto-avaliação do LLM**, porque no domínio dele não
há verdade de campo — e o mesmo vale para ArcMemo e Dynamic Cheatsheet. Aqui há,
e é o que separa este desenho de quase todo o campo:

- `ExecutionReport` — 10 estágios determinísticos, com `error_code` por estágio;
- `ValidationVerdict` — `montar_veredito()`, sem LLM no caminho.

Então o julgamento aqui **não chama LLM nenhum**. É uma função pura sobre a
evidência que o harness já coletou, o que a torna testável e reproduzível.
"""

from __future__ import annotations

import logging

from .schemas import MemoryItem, MemoryOutcome, MemoryStatus
from .trajectory import normalizar_status

logger = logging.getLogger(__name__)

# Conteúdo abaixo disso não é lição, é fragmento — o modelo truncou ou o parser
# pegou um cabeçalho solto. O ReasoningBank pede "1-3 sentences"; 40 caracteres
# é o piso generoso abaixo do qual nem uma frase cabe.
_MIN_CONTENT = 40
_MIN_TITULO = 4


def julgar(item: MemoryItem, *, veredito_status: str = "") -> MemoryItem:
    """Atribui `status` e `judge_reason` ao item. Não chama LLM.

    `veredito_status` é o `status` do `ValidationVerdict` da run
    (`aprovado`/`reprovado`), usado só para a checagem de contra-evidência.

    A ordem das regras importa: rejeições vêm primeiro (item inválido não deve
    ser avaliado quanto à ancoragem), depois a contra-evidência, e a promoção
    é o último caso — o default é a quarentena, não a aprovação.
    """
    # --- Camada 1: forma. Item malformado não é conhecimento. --------------
    if len(item.title.strip()) < _MIN_TITULO:
        return _decidir(item, MemoryStatus.REJEITADO, "Título ausente ou curto demais.")

    if len(item.content.strip()) < _MIN_CONTENT:
        return _decidir(
            item,
            MemoryStatus.REJEITADO,
            f"Conteúdo com {len(item.content.strip())} caracteres — abaixo do "
            f"mínimo de {_MIN_CONTENT}; provável truncamento do modelo.",
        )

    if not item.description.strip():
        return _decidir(
            item, MemoryStatus.REJEITADO, "Sem descrição: o contrato exige os 3 campos."
        )

    # --- Camada 2: contra-evidência (GovMem). ------------------------------
    # O item afirma ter aprendido com um sucesso, mas o veredito determinístico
    # da run foi reprovação. A alegação contradiz a evidência: descartar.
    if (
        item.outcome == MemoryOutcome.SUCESSO
        and normalizar_status(veredito_status) == "reprovado"
    ):
        return _decidir(
            item,
            MemoryStatus.REJEITADO,
            "Item de sucesso numa run cujo veredito foi 'reprovado' — "
            "contradiz a evidência de execução.",
        )

    # --- Camada 3: ancoragem em evidência. ---------------------------------
    # Sem rastro até o ExecutionReport não há como auditar a alegação depois.
    if item.provenance is None or not item.provenance.report_path:
        return _decidir(
            item,
            MemoryStatus.REVISAR,
            "Sem rastro para um ExecutionReport: a alegação não é auditável.",
        )

    # Lição de falha só se sustenta se a máquina nomeou o que falhou. Há DOIS
    # sinais determinísticos possíveis, e exigir só o primeiro deixa de fora
    # uma classe inteira de reprovação:
    #
    #   - `error_codes` — estágio do harness que falhou;
    #   - `unmet_criteria` — critério de aceite não atendido/inconclusivo no
    #     ValidationVerdict, emitido por `montar_veredito()`, sem LLM.
    #
    # A reprovação SEMÂNTICA (run de 13/08: `overall_status: sucesso`, zero
    # estágios falhos, veredito `reprovado` com 2 critérios inconclusivos) não
    # produz error_code algum — o harness passou em tudo. Exigir error_code ali
    # quarentenava lições perfeitamente ancoradas, que inclusive citavam os
    # critérios reprovados pelo nome.
    if item.outcome == MemoryOutcome.FALHA and not (
        item.error_codes or item.unmet_criteria
    ):
        return _decidir(
            item,
            MemoryStatus.REVISAR,
            "Lição de falha sem error_code e sem critério reprovado — não "
            "ancorada em nada que a máquina tenha medido.",
        )

    # --- Camada 4: escopo (GovMem "atribui escopo"). -----------------------
    # Sem stack, o item seria injetado em qualquer projeto. É exatamente o
    # *perspective confinement* do OEP: confundir acerto local com regra geral.
    if not item.tech_stack.strip():
        return _decidir(
            item,
            MemoryStatus.REVISAR,
            "Sem tech_stack: item sem escopo seria injetado em qualquer stack.",
        )

    ancora = (
        f"error_codes={item.error_codes}"
        if item.error_codes
        else f"critérios reprovados={len(item.unmet_criteria)}"
        if item.unmet_criteria
        else "veredito aprovado"
    )
    return _decidir(
        item,
        MemoryStatus.PROMOVIDO,
        f"Ancorado em {item.provenance.report_path} "
        f"({ancora}, escopo={item.tech_stack}).",
    )


def _decidir(item: MemoryItem, status: MemoryStatus, motivo: str) -> MemoryItem:
    item.status = status
    item.judge_reason = motivo
    logger.info("[MEMORY] %s → %s: %s", item.title[:60], status.value, motivo)
    return item


def julgar_lote(
    itens: list[MemoryItem], *, veredito_status: str = ""
) -> list[MemoryItem]:
    """Julga todos os itens. Devolve a lista com `status` preenchido."""
    return [julgar(i, veredito_status=veredito_status) for i in itens]
