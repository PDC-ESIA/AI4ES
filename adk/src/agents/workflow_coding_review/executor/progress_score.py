"""Nota de progresso (0..1) da entrega de um work item — cálculo determinístico.

Motivação (issue #394): o loop `coder ↔ executor` encerrava por um teto fixo de
iterações, cego ao que estava acontecendo — cortava soluções que ainda
avançavam e insistia em soluções já travadas. Este módulo produz a MEDIDA que
substitui esse teto como critério primário: uma nota de 0 a 1 que diz o quanto a
entrega subiu por uma "escada de capacidades".

Princípio: a nota não pede NADA ao LLM. Ela é derivada de dois artefatos que o
fluxo já produz a cada rodada — o `ExecutionReport` do harness e o
`ValidationVerdict` do `implementation_validator`. Dado o mesmo par de
artefatos, a nota é sempre a mesma; é auditável e testável isoladamente.

(Ressalva honesta de escopo: os `criteria_verdicts` que alimentam o degrau
`CRITERIOS_ATENDIDOS` nascem de um julgamento do LLM dentro do validador — só a
agregação é determinística lá. Logo, a nota é reprodutível A PARTIR DOS
ARTEFATOS de uma rodada, mas duas rodadas idênticas do zero podem divergir
levemente. O que este módulo garante é que ele próprio não acrescenta nenhuma
não-determinação.)

Este módulo NÃO decide se o loop continua — isso é `loop_policy.py`. Ele também
NÃO emite veredito de aprovação: quem aprova continua sendo exclusivamente o
`ValidationVerdict`. Aqui só se mede o caminho percorrido.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from shared.tools.coding_tools.harness_schemas import StageName, StageStatus


class Degrau(str, Enum):
    """Os degraus da escada de capacidades, em ordem de progresso.

    Os cinco primeiros compõem a "versão mínima que funciona"; o último mede o
    quanto a entrega está de fato completa.
    """

    MINIMO_PARA_RODAR = "minimo_para_rodar"
    AMBIENTE_PREPARADO = "ambiente_preparado"
    BUILD_CONCLUIDO = "build_concluido"
    APP_INICIOU = "app_iniciou"
    TESTES_PASSARAM = "testes_passaram"
    CRITERIOS_ATENDIDOS = "criterios_atendidos"


# Pesos-base dos degraus. Somam 1.0 quando TODOS se aplicam; quando algum não se
# aplica ao tipo de projeto, `redistribuir_pesos` renormaliza para que o teto
# continue sendo 1.0 (ver docstring de lá).
#
# ATENÇÃO — estes valores são um PONTO DE PARTIDA, não uma calibração. A issue
# #394 deixa explicitamente a calibração fora de escopo: ajuste-os com base em
# execuções reais (comparar o histórico de notas contra o desfecho observado).
_PESOS_BASE: dict[Degrau, float] = {
    Degrau.MINIMO_PARA_RODAR: 0.05,
    Degrau.AMBIENTE_PREPARADO: 0.10,
    Degrau.BUILD_CONCLUIDO: 0.15,
    Degrau.APP_INICIOU: 0.15,
    Degrau.TESTES_PASSARAM: 0.20,
    Degrau.CRITERIOS_ATENDIDOS: 0.35,
}

# Degraus cujo score sai do status técnico de UM estágio do harness (binário).
# Os demais degraus têm regra própria: MINIMO_PARA_RODAR (ver `calcular_nota`),
# TESTES_PASSARAM e CRITERIOS_ATENDIDOS (fracionários).
_ESTAGIO_DO_DEGRAU: dict[Degrau, StageName] = {
    Degrau.AMBIENTE_PREPARADO: StageName.PREPARACAO_AMBIENTE,
    Degrau.BUILD_CONCLUIDO: StageName.IMPLANTACAO_ARTEFATO,
    Degrau.APP_INICIOU: StageName.INICIALIZACAO_APLICACAO,
}

# Superfície declarada no `run.json` que dispensa o degrau APP_INICIOU: não há
# serviço nem comando de topo a inicializar (biblioteca, etc.).
_SURFACE_SEM_APP = "none"

# Casas decimais da nota. Evita que ruído de ponto flutuante (0.30000000000004)
# apareça no histórico e atrapalhe as comparações de margem em `loop_policy`.
_CASAS_DECIMAIS = 6


@dataclass(frozen=True)
class NotaProgresso:
    """A nota de uma rodada, com o detalhamento que a torna auditável.

    Attributes:
        total: Nota agregada em [0, 1].
        por_degrau: Score bruto (0..1) de cada degrau APLICÁVEL, antes do peso.
        degraus_aplicaveis: Degraus que fazem sentido para este projeto.
        pesos_efetivos: Peso de cada degrau aplicável após a redistribuição;
            soma 1.0.
    """

    total: float
    por_degrau: dict[Degrau, float]
    degraus_aplicaveis: frozenset[Degrau]
    pesos_efetivos: dict[Degrau, float]

    def como_dict(self) -> dict[str, float]:
        """Detalhamento serializável para o histórico no session state.

        Chaves como `str` (o valor do enum), não como membro do enum: o dict vai
        para `session.state` e pode ser serializado em JSON.
        """
        return {degrau.value: score for degrau, score in self.por_degrau.items()}


# ---------------------------------------------------------------------------
# Leitura defensiva do ExecutionReport
# ---------------------------------------------------------------------------


def _inteiro(valor: Any) -> int:
    """Converte para int não-negativo; qualquer coisa estranha vira 0.

    O `evidence` do harness é um dict livre (`dict` sem schema): nada garante
    que os contadores sejam inteiros se algum caminho futuro os escrever
    diferente. Contar errado aqui distorceria a nota silenciosamente.
    """
    if isinstance(valor, bool):  # bool é subclasse de int — não é contagem
        return 0
    if isinstance(valor, int):
        return max(0, valor)
    return 0


def estagios_por_nome(report: dict) -> dict[str, dict]:
    """Indexa `report['stages']` por nome do estágio, ignorando itens inválidos.

    Se o mesmo estágio aparecer duas vezes, a ÚLTIMA ocorrência vence — é a que
    reflete o estado final da passagem pelo harness.

    Pública porque `loop_policy` também percorre os estágios, para montar a
    assinatura de erro a partir dos mesmos dados.
    """
    indexado: dict[str, dict] = {}
    for item in report.get("stages") or []:
        if not isinstance(item, dict):
            continue
        nome = item.get("stage")
        if isinstance(nome, str):
            indexado[nome] = item
    return indexado


def _contexto_do_manifesto(
    estagios: dict[str, dict],
) -> tuple[Optional[str], list[str]]:
    """Extrai `surface` e `test_commands` do estágio de preparação do ambiente.

    A aplicabilidade dos degraus vem do MANIFESTO (`run.json`), não do resultado
    da execução — ver `graus_aplicaveis`. O harness ecoa ambos no `evidence` do
    estágio 1 (`_estagio_preparacao`, no branch de sucesso).

    Returns:
        `(surface, test_commands)`. `surface` é `None` quando o estágio 1 não
        chegou a registrar a evidência (ex.: falhou antes, por manifesto ausente
        ou inválido) — nesse caso a aplicabilidade degrada para o conservador.
    """
    estagio = estagios.get(StageName.PREPARACAO_AMBIENTE)
    evidencia = (estagio or {}).get("evidence")
    if not isinstance(evidencia, dict):
        return None, []

    surface = evidencia.get("surface")
    surface = surface if isinstance(surface, str) else None

    comandos = evidencia.get("test_commands")
    comandos = (
        [c for c in comandos if isinstance(c, str)]
        if isinstance(comandos, list)
        else []
    )

    return surface, comandos


# ---------------------------------------------------------------------------
# Aplicabilidade e pesos
# ---------------------------------------------------------------------------


def graus_aplicaveis(
    surface: Optional[str], test_commands: list[str]
) -> frozenset[Degrau]:
    """Degraus que fazem sentido para este projeto, a partir do manifesto.

    Puramente declarativo: NÃO consulta o resultado de nenhum estágio. Isso é
    deliberado — o harness usa `StageStatus.PULADO` para duas coisas bem
    diferentes: "não se aplica a este projeto" (ex.: `surface=none` não
    inicializa aplicação) e "não executei porque algo antes falhou". Deduzir
    aplicabilidade do status confundiria as duas, e um degrau pulado por falha
    upstream teria seu peso redistribuído em vez de contar como não alcançado —
    inflando a nota justamente na rodada que fracassou.

    Args:
        surface: Superfície declarada no `run.json` (`service`/`command`/`none`),
            ou `None` quando ainda não se sabe.
        test_commands: Comandos de teste declarados no manifesto.

    Returns:
        Conjunto de degraus aplicáveis. Com `surface=None` (desconhecida), todos
        entram — conservador: sem evidência de que um degrau é dispensável,
        redistribuir o peso dele inflaria a nota.
    """
    aplicaveis = {
        Degrau.MINIMO_PARA_RODAR,
        Degrau.AMBIENTE_PREPARADO,
        Degrau.BUILD_CONCLUIDO,
        Degrau.CRITERIOS_ATENDIDOS,
    }
    if surface is None or surface != _SURFACE_SEM_APP:
        aplicaveis.add(Degrau.APP_INICIOU)
    if surface is None or test_commands:
        aplicaveis.add(Degrau.TESTES_PASSARAM)
    return frozenset(aplicaveis)


def redistribuir_pesos(
    aplicaveis: frozenset[Degrau] | set[Degrau],
    pesos_base: Optional[dict[Degrau, float]] = None,
) -> dict[Degrau, float]:
    """Renormaliza os pesos-base sobre os degraus aplicáveis (soma sempre 1.0).

    O peso de um degrau que não se aplica é diluído PROPORCIONALMENTE entre os
    demais, e não redistribuído em partes iguais: isso preserva a importância
    relativa entre os degraus que restaram. Assim a nota máxima possível
    continua sendo 1.0 para qualquer tipo de projeto.

    Returns:
        Pesos efetivos por degrau aplicável. Dict vazio se nenhum degrau
        conhecido se aplicar (a nota resultante é 0.0 — ver `calcular_nota`).
    """
    base = pesos_base if pesos_base is not None else _PESOS_BASE
    considerados = frozenset(aplicaveis) & frozenset(base)
    if not considerados:
        return {}

    soma = sum(base[degrau] for degrau in considerados)
    if soma <= 0:
        # Configuração degenerada (pesos zerados/negativos): cai para uniforme
        # em vez de dividir por zero. Não deve acontecer com `_PESOS_BASE`.
        uniforme = 1.0 / len(considerados)
        return {degrau: uniforme for degrau in considerados}

    return {degrau: base[degrau] / soma for degrau in considerados}


# ---------------------------------------------------------------------------
# Score de cada degrau
# ---------------------------------------------------------------------------


def contagem_de_testes(estagio: Optional[dict]) -> tuple[int, int, int]:
    """Soma `(passaram, falharam, erros)` do estágio de testes automatizados.

    O harness registra um `resumo` POR COMANDO em
    `evidence['resultados'][*]['resumo']` e não persiste um agregado — o total
    que aparece no `summary` do estágio é só texto. A soma é feita aqui.

    Pública porque `loop_policy` também precisa dela: a assinatura de erro usa
    a contagem para distinguir "mesma falha de novo" de "mesma falha, porém com
    menos testes quebrados" — sem isso, uma rodada que vai de 10/30 para 28/30
    teria assinatura idêntica e poderia ser lida como travamento.
    """
    if not isinstance(estagio, dict):
        return 0, 0, 0

    evidencia = estagio.get("evidence")
    resultados = evidencia.get("resultados") if isinstance(evidencia, dict) else None

    passaram = falharam = erros = 0
    for resultado in resultados or []:
        resumo = resultado.get("resumo") if isinstance(resultado, dict) else None
        if not isinstance(resumo, dict):
            continue
        passaram += _inteiro(resumo.get("passaram"))
        falharam += _inteiro(resumo.get("falharam"))
        erros += _inteiro(resumo.get("erros"))

    return passaram, falharam, erros


def _score_estagio_binario(estagio: Optional[dict]) -> float:
    """1.0 se o estágio concluiu com sucesso; 0.0 em qualquer outro caso.

    Ausente, `falha`, `erro` e `pulado` valem 0.0 igualmente: se o degrau chegou
    até aqui é porque `graus_aplicaveis` o considerou aplicável, então um
    `pulado` só pode ser cascata de falha anterior — que é ausência de
    progresso, não dispensa.
    """
    if not isinstance(estagio, dict):
        return 0.0
    return 1.0 if estagio.get("status") == StageStatus.SUCESSO else 0.0


def _score_testes(estagio: Optional[dict]) -> float:
    """Fração de testes que passaram, com queda para o status quando não dá.

    Fracionário de propósito: se este degrau fosse binário (1.0 só com a suíte
    inteira verde), a nota ficaria CEGA durante a fase mais comum de iteração —
    consertar testes um a um. O loop leria "sem progresso" enquanto o coder vai
    de 2/10 para 8/10 e cortaria a tarefa no meio de um avanço real.

    Os contadores vêm do parsing best-effort que o harness faz da saída dos
    testes, por comando, em `evidence['resultados'][*]['resumo']` — somados
    aqui, porque o harness não persiste um agregado (o total que aparece no
    `summary` do estágio é só texto).

    Esse parsing só reconhece saída no formato pytest (`N passed` / `N failed` /
    `N error`). Para Jest, Maven, Go test e afins os contadores vêm todos zerados
    mesmo com a suíte inteira verde — daí a queda para o `status` do estágio, que
    é derivado do exit code e não depende de regex nenhum. Sem essa queda,
    zeraríamos um degrau conquistado só porque a stack não é Python.
    """
    if not isinstance(estagio, dict):
        return 0.0

    passaram, falharam, erros = contagem_de_testes(estagio)
    total = passaram + falharam + erros
    if total > 0:
        return passaram / total

    return 1.0 if estagio.get("status") == StageStatus.SUCESSO else 0.0


def _score_criterios(validation: dict) -> float:
    """Fração dos critérios de aceite com veredito 'atendido'.

    Lê o `ValidationVerdict` apenas como MEDIDA; o contrato binário que decide
    aprovação (`montar_veredito`) não é afetado nem reinterpretado aqui.
    Sem critérios julgados a fração é 0.0 — mesma postura conservadora do
    validador, que também reprova lista vazia em vez de aprovar no vácuo.
    """
    vereditos = validation.get("criteria_verdicts")
    if not isinstance(vereditos, list) or not vereditos:
        return 0.0

    considerados = [item for item in vereditos if isinstance(item, dict)]
    if not considerados:
        return 0.0

    atendidos = sum(1 for item in considerados if item.get("status") == "atendido")
    return atendidos / len(considerados)


# ---------------------------------------------------------------------------
# Cálculo da nota
# ---------------------------------------------------------------------------


def calcular_nota(execution_report: Any, validation: Any) -> NotaProgresso:
    """Calcula a nota de progresso de UMA rodada do loop.

    Args:
        execution_report: `ExecutionReport` do harness, como dict. Entradas
            inválidas/ausentes degradam para "nada foi alcançado" em vez de
            levantar — o chamador é um callback no meio do fluxo, e derrubá-lo
            custaria a rodada inteira.
        validation: `ValidationVerdict` como dict (`state['validation']`).

    Returns:
        `NotaProgresso` com o total em [0, 1] e o detalhamento por degrau.
    """
    report = execution_report if isinstance(execution_report, dict) else {}
    verdict = validation if isinstance(validation, dict) else {}

    estagios = estagios_por_nome(report)
    surface, test_commands = _contexto_do_manifesto(estagios)
    aplicaveis = graus_aplicaveis(surface, test_commands)
    pesos = redistribuir_pesos(aplicaveis)

    por_degrau: dict[Degrau, float] = {}
    for degrau in aplicaveis:
        if degrau is Degrau.MINIMO_PARA_RODAR:
            # Sempre 1.0 aqui, e isso é intencional: `calcular_nota` só roda
            # depois que o harness executou, o que só acontece quando o gate
            # `recusar_execucao_incompleta` já deixou passar. Quem registra a
            # falha DESTE degrau é o próprio gate, gravando nota 0.0 na rodada
            # que ele recusa (ver `loop_policy.registrar_e_avaliar`).
            por_degrau[degrau] = 1.0
        elif degrau is Degrau.TESTES_PASSARAM:
            por_degrau[degrau] = _score_testes(
                estagios.get(StageName.TESTES_AUTOMATIZADOS)
            )
        elif degrau is Degrau.CRITERIOS_ATENDIDOS:
            por_degrau[degrau] = _score_criterios(verdict)
        else:
            por_degrau[degrau] = _score_estagio_binario(
                estagios.get(_ESTAGIO_DO_DEGRAU[degrau])
            )

    total = sum(por_degrau[degrau] * pesos.get(degrau, 0.0) for degrau in aplicaveis)

    return NotaProgresso(
        total=round(total, _CASAS_DECIMAIS),
        por_degrau={d: round(s, _CASAS_DECIMAIS) for d, s in por_degrau.items()},
        degraus_aplicaveis=aplicaveis,
        pesos_efetivos={d: round(p, _CASAS_DECIMAIS) for d, p in pesos.items()},
    )
