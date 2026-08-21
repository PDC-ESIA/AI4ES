"""Política de continuidade do loop `coder ↔ executor` (issue #394).

Substitui o teto fixo de iterações como critério primário de parada. A regra,
em uma frase: **continuar enquanto a melhor nota já alcançada estiver subindo;
parar quando ela empacar.**

Por que a MELHOR nota e não a última: uma correção às vezes conserta uma coisa e
quebra outra, derrubando a nota momentaneamente. Olhar só a última rodada leria
esse vale como travamento e cortaria a tarefa no meio de um avanço. Comparar
contra a melhor já vista tolera o vale — e a tolerância se renova assim que a
entrega supera o próprio recorde.

Três gatilhos de parada, com uma assimetria deliberada entre eles:

1. **Platô da nota** — único gatilho autônomo. Nenhuma melhora por
   `janela_sem_progresso` rodadas seguidas.
2. **Sem alteração de arquivos** — o coder devolveu o turno sem tocar no
   workspace.
3. **Erro repetido** — a mesma assinatura de falha da rodada anterior.

Os gatilhos 2 e 3 NÃO param o loop sozinhos: exigem que a ausência de progresso
já tenha PERSISTIDO por `rodadas_para_acelerar` rodadas. Eles aceleram o platô
(disparam antes de a janela inteira se esgotar), mas nunca interrompem uma
entrega sobre um único tropeço.

Essa persistência é o que impede o falso positivo mais caro: a nota cai numa
rodada (a correção que conserta A e quebra B), o coder por acaso não edita nada,
e a task morre justamente quando a rodada seguinte voltaria a subir. Exigir só
"não melhorou AGORA" derrubava esse caso — e a nota ter se movido sem alteração
de arquivo é, se alguma coisa, evidência de NÃO-DETERMINISMO (teste instável,
serviço lento, julgamento do validador), não de travamento.

O próprio protocolo que esta política substitui já era cauteloso aqui: o prompt
do executor mandava rodar o harness mais uma vez antes de declarar estagnação,
porque "o ambiente pode ter mudado". Uma versão determinística não pode ser
MENOS cautelosa que o mecanismo frágil que ela aposenta.

O teto de iterações do `LoopAgent` continua existindo, mas muda de papel: deixa
de ser o controle esperado e passa a ser rede de segurança contra um defeito
NESTA política. São dois mecanismos independentes, compostos com OR pelo próprio
ADK — e a redundância é a propriedade desejada, não duplicação a eliminar.
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
from dataclasses import dataclass
from typing import Any, Optional

from shared.execution.workspace_fingerprint import fingerprint_workspace
from shared.tools.coding_tools.harness_schemas import StageName
from shared.workspace import get_agent_workspace

from .progress_score import contagem_de_testes, estagios_por_nome

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Chaves de ciclo no session state
# ---------------------------------------------------------------------------

CHAVE_HISTORICO = "progress_score_history"
CHAVE_DETALHES = "progress_score_details"
CHAVE_ASSINATURA = "progress_last_error_signature"
CHAVE_FINGERPRINT = "progress_last_fingerprint"
CHAVE_MOTIVO_PARADA = "loop_stop_reason"

# Exportadas para o `TaskIterator` limpar entre tasks. Ficam AQUI, e não
# duplicadas lá, porque quem cria as chaves é este módulo: uma chave nova que
# escapasse da limpeza faria a task seguinte herdar o histórico da anterior — a
# primeira rodada dela seria lida como "sem alteração" e poderia ser cortada
# antes de qualquer tentativa real.
CHAVES_DE_CICLO: tuple[str, ...] = (
    CHAVE_HISTORICO,
    CHAVE_DETALHES,
    CHAVE_ASSINATURA,
    CHAVE_FINGERPRINT,
    CHAVE_MOTIVO_PARADA,
)


# ---------------------------------------------------------------------------
# Parâmetros — placeholders configuráveis, calibração fora do escopo da issue
# ---------------------------------------------------------------------------


def _config(nome: str, padrao: float, minimo: float) -> float:
    """Lê um parâmetro fracionário do ambiente, caindo para o padrão se inutilizável.

    Um valor inválido não pode derrubar o import do módulo nem, pior, desligar
    silenciosamente a política: o padrão vale e o problema fica registrado no log.

    `nan` e `inf` precisam de checagem PRÓPRIA e não são cobertos pela comparação
    de mínimo: `float("nan") < minimo` é False e `float("inf") < minimo` também,
    então ambos passariam adiante como se fossem válidos. Um `nan` desligaria a
    política em silêncio (toda comparação com ele é False) e um `inf` estouraria
    na conversão para inteiro.
    """
    bruto = os.environ.get(nome)
    if bruto is None:
        return padrao
    try:
        valor = float(bruto)
    except TypeError, ValueError:
        logger.warning(
            "[LOOP_POLICY] %s=%r não é numérico; usando o padrão %s.",
            nome,
            bruto,
            padrao,
        )
        return padrao
    if not math.isfinite(valor):
        logger.warning(
            "[LOOP_POLICY] %s=%r não é finito; usando o padrão %s.",
            nome,
            bruto,
            padrao,
        )
        return padrao
    if valor < minimo:
        logger.warning(
            "[LOOP_POLICY] %s=%s abaixo do mínimo %s; usando o padrão %s.",
            nome,
            valor,
            minimo,
            padrao,
        )
        return padrao
    return valor


def config_inteiro(nome: str, padrao: int, minimo: int) -> int:
    """Lê um parâmetro INTEIRO do ambiente — usada também pelo teto do LoopAgent.

    Parseia com `int()` em vez de reaproveitar `_config`, de propósito: passar
    por `float` aceitaria `"3.9"` e truncaria para `3` silenciosamente, entregando
    um limite diferente do que foi configurado. Aqui um valor fracionário é
    recusado e o padrão vale, o que é honesto e visível no log.

    O teto de segurança precisa dessa robustez tanto quanto a política: um valor
    inválido não pode derrubar o import nem desligar o limite — um `0` que
    virasse "ilimitado" no LoopAgent transformaria a rede de segurança em
    ausência de rede.
    """
    bruto = os.environ.get(nome)
    if bruto is None:
        return padrao
    try:
        valor = int(bruto.strip())
    except TypeError, ValueError, AttributeError:
        logger.warning(
            "[LOOP_POLICY] %s=%r não é um inteiro; usando o padrão %s.",
            nome,
            bruto,
            padrao,
        )
        return padrao
    if valor < minimo:
        logger.warning(
            "[LOOP_POLICY] %s=%s abaixo do mínimo %s; usando o padrão %s.",
            nome,
            valor,
            minimo,
            padrao,
        )
        return padrao
    return valor


def _ajustar_rodadas_para_acelerar(
    janela_sem_progresso: int, rodadas_configuradas: int
) -> int:
    """Mantém o acelerador abaixo da janela autônoma de platô."""
    if rodadas_configuradas < janela_sem_progresso:
        return rodadas_configuradas
    ajustado = janela_sem_progresso - 1
    logger.warning(
        "[LOOP_POLICY] AI4ES_RODADAS_PARA_ACELERAR=%s precisa ser menor que "
        "AI4ES_JANELA_SEM_PROGRESSO=%s; usando %s.",
        rodadas_configuradas,
        janela_sem_progresso,
        ajustado,
    )
    return ajustado


# Rodadas consecutivas sem melhora que caracterizam platô. Precisa ser >= 3:
# uma rodada absorve o vale temporário e outra permite que os aceleradores
# detectem persistência antes do platô, sem se tornarem código morto.
JANELA_SEM_PROGRESSO: int = config_inteiro("AI4ES_JANELA_SEM_PROGRESSO", 3, minimo=3)

# Ganho mínimo para uma rodada contar como progresso. Absorve ruído de ponto
# flutuante e melhoras cosméticas irrelevantes, sem exigir salto grande.
MARGEM_MELHORA: float = _config("AI4ES_MARGEM_MELHORA", 0.01, minimo=0.0)

# Rodadas sem progresso exigidas antes que os gatilhos ACELERADORES (sem
# alteração de arquivos, erro repetido) possam encerrar o loop. Precisa ser >= 2
# pelo mesmo motivo da janela de platô: com 1, um único vale encerraria a task.
# Fica ABAIXO de `JANELA_SEM_PROGRESSO` de propósito — é essa diferença que dá
# aos aceleradores a sua razão de existir; se fossem iguais, eles nunca
# disparariam antes do platô e seriam código morto.
_rodadas_para_acelerar = config_inteiro(
    "AI4ES_RODADAS_PARA_ACELERAR", 2, minimo=2
)
RODADAS_PARA_ACELERAR: int = _ajustar_rodadas_para_acelerar(
    JANELA_SEM_PROGRESSO, _rodadas_para_acelerar
)


# ---------------------------------------------------------------------------
# Decisão
# ---------------------------------------------------------------------------

MOTIVO_PLATO = "plato_nota"
MOTIVO_SEM_ALTERACAO = "sem_alteracao_arquivos"
MOTIVO_ERRO_REPETIDO = "erro_repetido"
MOTIVOS_PARADA = frozenset(
    {MOTIVO_PLATO, MOTIVO_SEM_ALTERACAO, MOTIVO_ERRO_REPETIDO}
)


@dataclass(frozen=True)
class DecisaoContinuidade:
    """Se o loop deve parar nesta rodada e por quê."""

    parar: bool
    motivo: Optional[str] = None


def contar_rodadas_sem_progresso(
    historico: list[float], margem: float = MARGEM_MELHORA
) -> int:
    """Rodadas consecutivas, ao final do histórico, sem superar o recorde.

    Percorre o histórico inteiro reconstruindo o recorde rodada a rodada, em vez
    de comparar apenas com `max(historico)`. A diferença importa: `max` diz QUAL
    foi a melhor nota, mas não HÁ QUANTAS RODADAS ela não é superada — e é essa
    contagem que caracteriza platô.

    Escrita como função pura sobre a lista (e não como contador incremental no
    state) para poder ser testada com qualquer sequência, inclusive as
    adversariais, sem simular chamadas sucessivas.

    Exemplo — `[0.50, 0.42, 0.48, 0.53]` devolve 0: o vale de 0.42/0.48 consome
    tolerância, mas 0.53 supera o recorde e a janela recomeça.
    """
    recorde = float("-inf")
    sem_progresso = 0
    for nota in historico:
        if nota > recorde + margem:
            recorde = nota
            sem_progresso = 0
        else:
            sem_progresso += 1
    return sem_progresso


def avaliar_continuidade(
    historico_notas: list[float],
    arquivos_mudaram: bool,
    assinatura_erro_atual: Optional[str] = None,
    assinatura_erro_anterior: Optional[str] = None,
    *,
    janela_sem_progresso: int = JANELA_SEM_PROGRESSO,
    margem_melhora: float = MARGEM_MELHORA,
    rodadas_para_acelerar: int = RODADAS_PARA_ACELERAR,
) -> DecisaoContinuidade:
    """Decide se o loop para nesta rodada.

    Args:
        historico_notas: Notas de todas as rodadas da task, em ordem, INCLUINDO
            a atual.
        arquivos_mudaram: Se o workspace do coder mudou desde a rodada anterior.
        assinatura_erro_atual: Assinatura da falha desta rodada; `None` quando
            não há `ExecutionReport` (ex.: rodada recusada pelo gate estrutural).
        assinatura_erro_anterior: Assinatura da rodada anterior, se houver.

    Returns:
        `DecisaoContinuidade`. Só `parar=True` traz `motivo`.
    """
    sem_progresso = contar_rodadas_sem_progresso(historico_notas, margem_melhora)

    if sem_progresso >= janela_sem_progresso:
        return DecisaoContinuidade(True, MOTIVO_PLATO)

    # Guard compartilhado pelos gatilhos 2 e 3.
    #
    # A versão anterior exigia apenas `sem_progresso >= 1` — ou seja, bastava UMA
    # rodada abaixo do recorde. Isso contradizia o que este módulo promete: a
    # sequência 0.50 → 0.42 (vale) com o coder sem editar nada encerrava a task
    # na hora, mesmo quando a rodada seguinte voltaria a subir. O vale isolado é
    # justamente o caso que a issue manda tolerar, e ele é ainda mais suspeito
    # quando o código não mudou: a nota ter se movido sem alteração de arquivo é
    # evidência de não-determinismo (teste instável, serviço lento, julgamento do
    # validador), não de travamento.
    #
    # Agora os aceleradores exigem que a ausência de progresso já tenha PERSISTIDO
    # por `rodadas_para_acelerar` rodadas. Eles seguem disparando antes da janela
    # cheia do platô — que é a razão de existirem —, mas nunca sobre um único
    # tropeço.
    if sem_progresso < rodadas_para_acelerar:
        return DecisaoContinuidade(False)

    if not arquivos_mudaram:
        return DecisaoContinuidade(True, MOTIVO_SEM_ALTERACAO)

    if (
        assinatura_erro_atual is not None
        and assinatura_erro_atual == assinatura_erro_anterior
    ):
        return DecisaoContinuidade(True, MOTIVO_ERRO_REPETIDO)

    return DecisaoContinuidade(False)


# ---------------------------------------------------------------------------
# Assinatura de erro
# ---------------------------------------------------------------------------

_STATUS_COM_FALHA = ("falha", "erro")


def assinatura_erro(execution_report: Any, validation: Any) -> str:
    """Impressão digital da FALHA desta rodada, para detectar repetição.

    Precisa ser fina o bastante para distinguir "a mesma falha de novo" de "a
    mesma falha, porém menor". O `blocking_reason` da Camada 2 do validador é
    uma string FIXA ("Ao menos um critério ficou nao_atendido ou inconclusivo.")
    — não varia com quantos critérios mudaram. Uma assinatura baseada só nele
    trataria 10/30 e 28/30 testes passando como idênticas, e o gatilho de erro
    repetido poderia encerrar um avanço real.

    Compõem a assinatura:
      - `(estágio, error_code)` de cada estágio com `falha`/`erro`;
      - `(criterion, status)` de cada critério julgado — o `status`, nunca o
        `reasoning`: este é texto livre do LLM e muda de redação mesmo quando o
        resultado é o mesmo, o que faria a assinatura nunca repetir e desligaria
        o gatilho na prática;
      - a contagem de testes (passaram/falharam/erros).

    Returns:
        Hash hexadecimal. Usado só para comparação de igualdade entre rodadas.
    """
    report = execution_report if isinstance(execution_report, dict) else {}
    verdict = validation if isinstance(validation, dict) else {}

    partes: list[str] = []

    estagios = estagios_por_nome(report)
    for nome in sorted(estagios):
        estagio = estagios[nome]
        if estagio.get("status") in _STATUS_COM_FALHA:
            partes.append(
                f"stage:{nome}:{estagio.get('status')}:{estagio.get('error_code')}"
            )

    vereditos = verdict.get("criteria_verdicts")
    for item in vereditos if isinstance(vereditos, list) else []:
        if isinstance(item, dict):
            partes.append(f"criterio:{item.get('criterion')}:{item.get('status')}")

    passaram, falharam, erros = contagem_de_testes(
        estagios.get(StageName.TESTES_AUTOMATIZADOS)
    )
    partes.append(f"testes:{passaram}:{falharam}:{erros}")

    return hashlib.sha256("\n".join(partes).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Registro no state e avaliação — ponto único usado pelos dois callbacks
# ---------------------------------------------------------------------------


def fingerprint_mudou(state: dict) -> bool:
    """Se o workspace do coder mudou desde a rodada anterior; atualiza o state.

    Na PRIMEIRA rodada não há com o que comparar e a resposta é `True`: sem
    rodada anterior não existe estagnação a declarar, e responder `False` aqui
    permitiria encerrar a task antes da primeira tentativa real.
    """
    try:
        atual = fingerprint_workspace(get_agent_workspace("cr_coder"))
    except Exception:  # noqa: BLE001 — medida auxiliar não derruba a rodada
        logger.exception(
            "[LOOP_POLICY] Falha ao calcular o fingerprint do workspace; "
            "assumindo que houve alteração (conservador)."
        )
        return True

    anterior = state.get(CHAVE_FINGERPRINT)
    state[CHAVE_FINGERPRINT] = atual
    if not isinstance(anterior, str):
        return True
    return atual != anterior


def registrar_rodada(
    state: dict, nota_total: float, nota_detalhe: Optional[dict]
) -> list[float]:
    """Acrescenta a rodada ao histórico de notas e devolve o histórico completo.

    Separada de `registrar_e_avaliar` por causa do caminho de APROVAÇÃO: a
    rodada aprovada precisa entrar no histórico (o critério de aceite pede que a
    nota final fique registrada), mas não pode passar pela política — uma task
    concluída com sucesso não pode terminar marcada com motivo de parada por
    platô, o que confundiria a classificação do desfecho no `TaskIterator`.

    Args:
        nota_detalhe: Score por degrau da rodada, ou `None` no caminho do gate
            estrutural, onde não há `NotaProgresso` (nada foi executado).
    """
    # As listas são RECRIADAS e reatribuídas, nunca mutadas no lugar: o `state`
    # do callback rastreia delta por atribuição de chave, e um `append` numa
    # lista aninhada poderia não ser persistido fora desta invocação.
    historico = list(state.get(CHAVE_HISTORICO) or [])
    historico.append(nota_total)
    state[CHAVE_HISTORICO] = historico

    detalhes = list(state.get(CHAVE_DETALHES) or [])
    detalhes.append(nota_detalhe)
    state[CHAVE_DETALHES] = detalhes

    return historico


def registrar_e_avaliar(
    state: dict,
    nota_total: float,
    nota_detalhe: Optional[dict],
    arquivos_mudaram: bool,
    assinatura_erro_atual: Optional[str] = None,
) -> DecisaoContinuidade:
    """Registra a rodada no histórico e devolve a decisão de continuidade.

    Chamada pelos DOIS callbacks do executor — o `after_agent_callback` (rodada
    normal, com harness executado) e o `before_agent_callback` do gate
    estrutural (rodada recusada por falta do mínimo executável). Ter um ponto
    único é o que garante que rodadas recusadas também sejam avaliadas: sem
    isso, um coder que trava antes de produzir manifesto válido nunca dispararia
    o platô e só pararia no teto de segurança.

    Quem seta `escalate` é cada chamador, porque cada callback tem o seu próprio
    `callback_context` — aqui só se decide.
    """
    historico = registrar_rodada(state, nota_total, nota_detalhe)

    decisao = avaliar_continuidade(
        historico_notas=historico,
        arquivos_mudaram=arquivos_mudaram,
        assinatura_erro_atual=assinatura_erro_atual,
        assinatura_erro_anterior=state.get(CHAVE_ASSINATURA),
    )

    if assinatura_erro_atual is not None:
        state[CHAVE_ASSINATURA] = assinatura_erro_atual

    if decisao.parar:
        state[CHAVE_MOTIVO_PARADA] = decisao.motivo
        logger.info(
            "[LOOP_POLICY] Encerrando o loop por %s na rodada %d (histórico=%s).",
            decisao.motivo,
            len(historico),
            historico,
        )

    return decisao
