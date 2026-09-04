"""Política de continuidade do loop `coder ↔ executor` (issue #394).

Substitui o teto fixo de iterações como critério primário de parada. A regra,
em uma frase: **continuar enquanto o coder estiver avançando; parar quando ele
empacar no mesmo problema.**

O que conta como AVANÇO são duas coisas, e a segunda é o que dá nome à política:

1. **Recorde de nota** — a entrega subiu na escada de capacidades.
2. **Falha inédita nesta task** — o coder derrubou um problema e destravou o
   próximo.

O item 2 existe porque a nota é um sinal grosseiro DENTRO de um degrau:
`build_concluido` é binário, então consertar um erro de import, depois uma
dependência faltando, depois um erro de sintaxe — três avanços reais — não mexe
nela. Uma política que olhasse só a nota declararia platô no meio dessa
sequência e mataria tasks que terminariam. Foi o que se observou em execução
real, e é o motivo de a tolerância ser contada desde o último avanço dos DOIS
tipos (`contar_rodadas_sem_avanco`), e não só sobre a nota.

Por que o recorde e não a última nota: uma correção às vezes conserta uma coisa
e quebra outra, derrubando a nota momentaneamente. Olhar só a última rodada
leria esse vale como travamento e cortaria a tarefa no meio de um avanço.

Quatro gatilhos de parada, com assimetrias deliberadas entre eles:

1. **Orçamento de falhas distintas** — teto de falhas DIFERENTES por task. É o
   freio da novidade: trocar de erro indefinidamente deixa de ser avanço e vira
   sintoma de que o coder está tateando. Verificado antes de todos os outros,
   porque a rodada que estoura o orçamento é justamente uma de falha inédita.
2. **Sem alteração de arquivos** — o coder devolveu o turno sem tocar no
   workspace. Medido contra a NOTA, não contra o avanço híbrido: sem edição não
   há correção, e uma assinatura que muda sozinha aí é ruído de execução (teste
   instável, serviço lento), não avanço.
3. **Platô** — nenhum avanço, de nenhum tipo, por `janela_sem_progresso`
   rodadas seguidas.
4. **Erro repetido** — a mesma assinatura de falha da rodada anterior.

Os gatilhos 2 e 4 NÃO param o loop sozinhos: exigem que a ausência de avanço já
tenha PERSISTIDO por `rodadas_para_acelerar` rodadas. Eles aceleram o platô
(disparam antes de a janela inteira se esgotar), mas nunca interrompem uma
entrega sobre um único tropeço.

Essa persistência é o que impede o falso positivo mais caro: a nota cai numa
rodada (a correção que conserta A e quebra B), o coder por acaso não edita nada,
e a task morre justamente quando a rodada seguinte voltaria a subir. Exigir só
"não melhorou AGORA" derrubava esse caso.

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
import re
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
CHAVE_HISTORICO_ASSINATURAS = "progress_error_signature_history"
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
    CHAVE_HISTORICO_ASSINATURAS,
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
    except (TypeError, ValueError):
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
    except (TypeError, ValueError, AttributeError):
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

# Quantas falhas DISTINTAS uma task pode atravessar antes de o loop desistir.
#
# É o freio da política orientada a causa: uma assinatura inédita renova a
# tolerância (o coder está atravessando problemas diferentes, ainda que a nota
# não enxergue isso), mas novidade infinita não pode significar loop infinito.
# Precisa ser >= 2 para que a política exista de fato: com 1, a primeira falha
# nova já esgotaria o orçamento e o comportamento degeneraria para o platô puro.
ORCAMENTO_FALHAS_DISTINTAS: int = config_inteiro(
    "AI4ES_ORCAMENTO_FALHAS_DISTINTAS", 6, minimo=2
)


# ---------------------------------------------------------------------------
# Decisão
# ---------------------------------------------------------------------------

MOTIVO_PLATO = "plato_nota"
MOTIVO_SEM_ALTERACAO = "sem_alteracao_arquivos"
MOTIVO_ERRO_REPETIDO = "erro_repetido"
MOTIVO_ORCAMENTO_FALHAS = "orcamento_de_falhas_distintas"
MOTIVOS_PARADA = frozenset(
    {
        MOTIVO_PLATO,
        MOTIVO_SEM_ALTERACAO,
        MOTIVO_ERRO_REPETIDO,
        MOTIVO_ORCAMENTO_FALHAS,
    }
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


def contar_rodadas_sem_avanco(
    historico_notas: list[float],
    historico_assinaturas: Optional[list[Optional[str]]] = None,
    margem: float = MARGEM_MELHORA,
) -> int:
    """Rodadas ao final SEM avanço — nem na nota, nem em falha inédita.

    É o contador que a política de continuidade usa, e a diferença para
    `contar_rodadas_sem_progresso` é o ponto inteiro desta política: a nota é
    cega DENTRO de um degrau (`build_concluido` é binário), então derrubar três
    erros seguidos não mexe nela. Uma falha que nunca apareceu nesta task é
    avanço, e zera a contagem exatamente como um recorde de nota zeraria.

    Sem isso, a novidade só valeria para a rodada em que aparece: o platô
    acumulado das rodadas anteriores continuaria de pé e encerraria a task no
    primeiro retry da falha nova — matando a tarefa justamente depois de ela ter
    avançado. Contar desde o último avanço é o que faz "renovar a tolerância"
    significar o que diz.

    Escrita como função pura sobre as duas listas (e não como contador no state)
    pelo mesmo motivo de `contar_rodadas_sem_progresso`: qualquer sequência,
    inclusive as adversariais, pode ser testada sem simular chamadas sucessivas.

    Args:
        historico_notas: Notas de todas as rodadas da task, em ordem.
        historico_assinaturas: Assinatura de falha de cada rodada, ALINHADA com
            `historico_notas`. `None` numa posição significa rodada sem
            `ExecutionReport` (ex.: recusada pelo gate estrutural), que não conta
            como falha inédita. Ausente por completo degrada para a contagem
            baseada só na nota.
    """
    assinaturas = list(historico_assinaturas or ())
    recorde = float("-inf")
    vistas: set[str] = set()
    sem_avanco = 0

    for indice, nota in enumerate(historico_notas):
        avancou = False

        if nota > recorde + margem:
            recorde = nota
            avancou = True

        assinatura = assinaturas[indice] if indice < len(assinaturas) else None
        if assinatura is not None and assinatura not in vistas:
            vistas.add(assinatura)
            avancou = True

        sem_avanco = 0 if avancou else sem_avanco + 1

    return sem_avanco


def falhas_distintas(historico_assinaturas: Optional[list[Optional[str]]]) -> int:
    """Quantas falhas DIFERENTES a task já atravessou (ignora rodadas sem report)."""
    return len({a for a in (historico_assinaturas or ()) if isinstance(a, str)})


def avaliar_continuidade(
    historico_notas: list[float],
    arquivos_mudaram: bool,
    assinatura_erro_atual: Optional[str] = None,
    assinatura_erro_anterior: Optional[str] = None,
    historico_assinaturas: Optional[list[Optional[str]]] = None,
    *,
    janela_sem_progresso: int = JANELA_SEM_PROGRESSO,
    margem_melhora: float = MARGEM_MELHORA,
    rodadas_para_acelerar: int = RODADAS_PARA_ACELERAR,
    orcamento_de_falhas_distintas: int = ORCAMENTO_FALHAS_DISTINTAS,
) -> DecisaoContinuidade:
    """Decide se o loop para nesta rodada.

    A pergunta que esta função responde NÃO é "a nota subiu?", e sim "o coder
    está preso no MESMO problema?". A diferença entre as duas é o motivo desta
    política existir na forma atual.

    A nota é um sinal grosseiro DENTRO de um degrau: `build_concluido` é binário,
    então o coder pode consertar um erro de import, descobrir uma dependência
    faltando, consertar, descobrir um erro de sintaxe — três avanços reais — com
    a nota parada o tempo todo. Uma política que olhasse só a nota declararia
    platô no meio dessa sequência e mataria uma task que ia terminar. Foi o que
    se observou: tasks reprovadas que o coder resolveria com mais algumas
    rodadas.

    Por isso a tolerância é contada desde o último AVANÇO — recorde de nota ou
    falha inédita, o que vier por último (`contar_rodadas_sem_avanco`). O freio é
    o ORÇAMENTO: uma task pode atravessar `orcamento_de_falhas_distintas` falhas
    diferentes; passando disso, trocar de erro deixou de ser sinal de avanço e
    virou sintoma de que o coder está tateando.

    Args:
        historico_notas: Notas de todas as rodadas da task, em ordem, INCLUINDO
            a atual.
        arquivos_mudaram: Se o workspace do coder mudou desde a rodada anterior.
        assinatura_erro_atual: Assinatura da falha desta rodada; `None` quando
            não há `ExecutionReport` (ex.: rodada recusada pelo gate estrutural).
        assinatura_erro_anterior: Última assinatura NÃO-NULA anterior. Usada só
            pelo gatilho de erro repetido — daí ser passada à parte, e não lida
            do histórico: uma rodada recusada pelo gate no meio do caminho não
            deve apagar a memória da falha que se está tentando corrigir.
        historico_assinaturas: Assinatura de cada rodada, ALINHADA com
            `historico_notas`. É o que permite distinguir "erro novo" de "erro
            que já apareceu e voltou" — comparar só com a anterior deixaria
            passar a oscilação A → B → A.

    Returns:
        `DecisaoContinuidade`. Só `parar=True` traz `motivo`.
    """
    # Teto de falhas distintas. Verificado ANTES de tudo, inclusive do avanço:
    # a rodada que estoura o orçamento é justamente uma rodada de falha inédita,
    # e sem esta precedência a novidade a faria continuar para sempre.
    if falhas_distintas(historico_assinaturas) > orcamento_de_falhas_distintas:
        return DecisaoContinuidade(True, MOTIVO_ORCAMENTO_FALHAS)

    # O coder devolveu o turno sem tocar no workspace. Medido contra a NOTA, e
    # não contra o avanço híbrido, de propósito: sem edição não há correção, e
    # uma assinatura que muda sozinha aí é ruído de execução (teste instável,
    # serviço lento), não avanço — não pode renovar tolerância nenhuma.
    if (
        contar_rodadas_sem_progresso(historico_notas, margem_melhora)
        >= rodadas_para_acelerar
        and not arquivos_mudaram
    ):
        return DecisaoContinuidade(True, MOTIVO_SEM_ALTERACAO)

    sem_avanco = contar_rodadas_sem_avanco(
        historico_notas, historico_assinaturas, margem_melhora
    )

    # Houve avanço nesta rodada — nota nova ou falha inédita. Tolerância zerada.
    if sem_avanco == 0:
        return DecisaoContinuidade(False)

    if sem_avanco >= janela_sem_progresso:
        return DecisaoContinuidade(True, MOTIVO_PLATO)

    if sem_avanco < rodadas_para_acelerar:
        return DecisaoContinuidade(False)

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

# Chaves de `evidence` que carregam a CAUSA da falha. Whitelist, e não o
# `evidence` inteiro: o dict é livre e traz também medidas de tempo e outros
# campos que variam entre rodadas idênticas, o que faria a assinatura nunca
# repetir e desligaria o gatilho de erro repetido na prática.
_CHAVES_EVIDENCIA_CAUSAL = (
    "comando_falho",
    "exit_code",
    "timed_out",
    "build_logs_tail",
    "run_command",
    "saida_tail",
    "healthcheck_url",
    "ultimo_erro",
)

# Campos de cada comando dentro de `evidence['resultados']` (estágio de testes).
# `resumo` fica de fora: os contadores já entram agregados na assinatura.
_CHAVES_RESULTADO_DE_TESTE = ("comando", "exit_code", "timed_out", "saida_tail")

# Normalização CONSERVADORA da saída antes do hash. Só remove o que é
# inequivocamente volátil entre execuções da mesma causa.
#
# O que NÃO está aqui é tão importante quanto o que está: caminhos relativos,
# nomes de módulo, portas e números de linha PERMANECEM. Um `ModuleNotFoundError`
# em `app/modulo_a.py` e outro em `app/modulo_b.py` são causas DIFERENTES, e
# apagar o caminho os faria colidir — recriando, por outra via, exatamente o
# defeito que esta função corrige.
#
# Na dúvida, preserve: duas ocorrências da mesma falha com assinaturas
# diferentes custam uma rodada extra; duas causas diferentes com a mesma
# assinatura encerram a task antes da hora.
_SUBSTITUICOES_VOLATEIS = (
    (re.compile(r"\x1b\[[0-9;]*[A-Za-z]"), ""),  # códigos ANSI de cor
    (
        re.compile(
            r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"
            r"(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?"
        ),
        "<TS>",
    ),
    (re.compile(r"\b\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\b"), "<HORA>"),
    # Diretório temporário DO SANDBOX (`ai4se-sandbox-<uuid>` /
    # `ai4se-docker-<uuid>`, ver `shared/execution/sandbox.py`), que muda a cada
    # execução. Casa apenas esses prefixos conhecidos, e não "o primeiro
    # diretório sob /tmp": este último apagaria também nomes escolhidos pelo
    # projeto — `/tmp/projeto-a/config.py` e `/tmp/projeto-b/config.py` viravam
    # o mesmo caminho, colidindo duas causas distintas. O caminho RELATIVO
    # depois do prefixo é sempre preservado.
    (
        re.compile(r"(?:/[^/\s]+)*/ai4se-(?:sandbox|docker)-[^/\s]+/"),
        "<SANDBOX>/",
    ),
    # Identificadores efêmeros do sandbox Docker fora de forma de caminho: a
    # imagem sai como `ai4se-sandbox:<uuid>` e o container como
    # `ai4se-sandbox-<uuid>`, e ambos aparecem em exceções da lib docker.
    (
        re.compile(r"\bai4se-(?:sandbox|docker)[:-][0-9a-f]{6,}\b"),
        "<SANDBOX_ID>",
    ),
    (re.compile(r"\bpid[=: ]\s*\d+", re.IGNORECASE), "pid=<PID>"),
    (re.compile(r"0x[0-9a-fA-F]{4,}"), "0x<ADDR>"),  # endereços de objeto
    # Duração SÓ na forma contextual do rodapé de suíte ("in 0.03s"). Casar
    # qualquer token terminado em `s` apagaria valor causal: "timeout configured
    # as 5s" e "...as 60s" são configurações diferentes que colidiriam.
    (re.compile(r"\bin \d+(?:\.\d+)?s\b"), "in <DUR>"),
    (re.compile(r"[ \t]+"), " "),
    (re.compile(r"\n{2,}"), "\n"),
)


def _normalizar_texto_volatil(texto: str) -> str:
    """Remove de `texto` o que varia entre execuções da MESMA causa."""
    normalizado = texto
    for padrao, troca in _SUBSTITUICOES_VOLATEIS:
        normalizado = padrao.sub(troca, normalizado)
    return normalizado.strip()


def _valor_canonico(valor: Any) -> str:
    """Serializa um valor de evidência de forma estável e normalizada."""
    return _normalizar_texto_volatil(valor if isinstance(valor, str) else str(valor))


def _payload_do_estagio(nome: str, estagio: dict) -> list[str]:
    """Extrai do estágio falho os campos que identificam a CAUSA.

    `summary` entra SEMPRE, e não como enfeite: em `ERRO_START_SERVICE` o texto
    da exceção que causou a falha só existe ali — a `evidence` desse caminho traz
    apenas `run_command` (constante para a task) e o log do build (de outro
    estágio). Sem o summary, toda falha de start de serviço colidiria numa
    assinatura só.
    """
    partes = [
        f"stage:{nome}",
        f"status:{estagio.get('status')}",
        f"error_code:{estagio.get('error_code')}",
        f"summary:{_valor_canonico(estagio.get('summary') or '')}",
    ]

    evidencia = estagio.get("evidence")
    if not isinstance(evidencia, dict):
        return partes

    for chave in _CHAVES_EVIDENCIA_CAUSAL:
        if chave in evidencia:
            partes.append(f"{chave}:{_valor_canonico(evidencia.get(chave))}")

    resultados = evidencia.get("resultados")
    if isinstance(resultados, list):
        for indice, resultado in enumerate(resultados):
            if not isinstance(resultado, dict):
                continue
            for chave in _CHAVES_RESULTADO_DE_TESTE:
                if chave in resultado:
                    valor = _valor_canonico(resultado.get(chave))
                    partes.append(f"teste[{indice}].{chave}:{valor}")

    return partes


def assinatura_erro(execution_report: Any) -> str:
    """Impressão digital da FALHA desta rodada, para detectar repetição.

    Precisa ser fina o bastante para distinguir "a mesma falha de novo" de "uma
    falha DIFERENTE no mesmo estágio". O `error_code` do harness é categórico por
    ESTÁGIO, não por causa: `FALHA_BUILD` cobre desde um pacote inexistente no
    `requirements.txt` até um erro de sintaxe. Uma assinatura montada só com
    `(estágio, error_code)` tratava duas correções legítimas e distintas como a
    mesma falha — e, com `RODADAS_PARA_ACELERAR=2`, bastavam duas tentativas
    diferentes para o gatilho de erro repetido matar uma task que progredia.
    Daí a assinatura descer até a saída do comando que falhou, normalizada.

    Compõem a assinatura:
      - de cada estágio com `falha`/`erro`: estágio, status, `error_code`,
        `summary` e os campos causais da evidência (ver `_payload_do_estagio`);
      - a contagem agregada de testes (passaram/falharam/erros), que capta
        progresso parcial mesmo quando a saída não muda de forma.

    Recebe SÓ o `ExecutionReport`: o `ValidationVerdict` saiu do cálculo porque o
    julgamento de critérios deixou de ter conteúdo variável — no caminho de
    falha, `montar_veredito` monta a lista inteira de forma determinística
    (mesmos critérios, todos `inconclusivo`), então ela não distinguia rodada
    alguma. Uma assinatura de falha TÉCNICA também não é lugar para julgamento
    semântico.

    Returns:
        Hash hexadecimal. Usado só para comparação de igualdade entre rodadas.
    """
    report = execution_report if isinstance(execution_report, dict) else {}

    partes: list[str] = []

    estagios = estagios_por_nome(report)
    for nome in sorted(estagios):
        estagio = estagios[nome]
        if isinstance(estagio, dict) and estagio.get("status") in _STATUS_COM_FALHA:
            partes.extend(_payload_do_estagio(nome, estagio))

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

    # Reatribuída, nunca mutada no lugar: o `state` do callback rastreia delta
    # por atribuição de chave (mesma razão de `registrar_rodada`). Toda rodada
    # entra, inclusive as sem report (`None`), para o histórico ficar ALINHADO
    # com o de notas — é esse alinhamento que `contar_rodadas_sem_avanco` usa.
    assinaturas = list(state.get(CHAVE_HISTORICO_ASSINATURAS) or []) + [
        assinatura_erro_atual
    ]
    state[CHAVE_HISTORICO_ASSINATURAS] = assinaturas

    decisao = avaliar_continuidade(
        historico_notas=historico,
        arquivos_mudaram=arquivos_mudaram,
        assinatura_erro_atual=assinatura_erro_atual,
        assinatura_erro_anterior=state.get(CHAVE_ASSINATURA),
        historico_assinaturas=assinaturas,
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
