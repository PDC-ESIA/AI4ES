"""Proteção determinística contra sobrescrita cega entre tasks do coder.

Duas metades da mesma defesa, uma reativa e outra preventiva:

- `bloquear_sobrescrita_herdada` (before_tool_callback) RECUSA a sobrescrita
  integral de um arquivo de task anterior. É a rede que garante que nada se
  perde.
- `anunciar_arquivos_herdados` (after_tool_callback) AVISA, antes de a primeira
  escrita ser tentada, que o projeto já existe e quais arquivos são dele.

A segunda existe por uma observação de execução real (run do "fotógrafo",
6 tasks): em TODAS as tasks a partir da 2ª, a primeira ação do coder sobre o
código era `tool_criar_arquivo("PLAN.md")` — ou seja, ele entrava no ramo
"primeira execução" do prompt e tentava replanejar e reconstruir o projeto do
zero, apesar de o prompt dizer explicitamente para não fazer isso. O guard
bloqueou 19 de 19 tentativas e nada foi destruído, mas a task inteira era gasta
batendo na parede — e terminava em `sem_alteracao_arquivos` ou `erro_repetido`.

O que a mesma run mostrou que FUNCIONA: depois de cada bloqueio, o coder lia o
arquivo corretamente (`tool_ler_arquivo`) na sequência, sem exceção. Ou seja,
ele reage ao RESULTADO DE UMA TOOL de forma muito mais confiável do que a uma
instrução em prosa no system prompt. `anunciar_arquivos_herdados` usa esse
canal: leva o aviso para dentro da resposta da tool que o coder chama primeiro
em toda task, em vez de esperar que ele se lembre do prompt.
"""

from __future__ import annotations

import logging
from pathlib import PurePosixPath
from typing import Any, MutableMapping

from shared.workspace import get_agent_workspace

logger = logging.getLogger(__name__)

CHAVE_ARQUIVOS_HERDADOS = "coder_arquivos_herdados_da_task"
NOME_TOOL_REMOCAO = "tool_remover_arquivo"

# Tool cuja resposta carrega o aviso. É a PRIMEIRA chamada do coder em toda
# task (confirmado na run do "fotógrafo": 6 chamadas, uma por task, sempre
# abrindo a task), então o aviso chega antes da primeira decisão de escrita e
# uma única vez — sem poluir as dezenas de leituras que vêm depois.
_TOOL_ANUNCIADA = "tool_listar_workspace"

# Teto de caminhos listados no aviso. Um projeto grande não pode transformar o
# aviso num despejo de contexto; o que importa é o coder saber QUE o projeto
# existe e reconhecer os arquivos de topo.
_MAX_ARQUIVOS_NO_AVISO = 80


def preparar_arquivos_herdados(
    state: MutableMapping[str, Any], *, primeira: bool
) -> None:
    """Registra os arquivos que já existiam antes da task corrente.

    Na primeira task o projeto ainda está sendo materializado, portanto não há
    proteção contra sobrescrita integral. Nas seguintes, a fotografia permanece
    imutável durante todos os retries da mesma task.
    """
    if primeira:
        state[CHAVE_ARQUIVOS_HERDADOS] = []
        return

    raiz = get_agent_workspace("cr_coder")
    state[CHAVE_ARQUIVOS_HERDADOS] = sorted(
        caminho.relative_to(raiz).as_posix()
        for caminho in raiz.rglob("*")
        if caminho.is_file()
    )


def _normalizar_caminho(caminho: object) -> str | None:
    """Normaliza um caminho relativo da tool ou devolve None se for inseguro."""
    if not isinstance(caminho, str) or not caminho.strip():
        return None
    texto = caminho.strip().replace("\\", "/")
    path = PurePosixPath(texto)
    if path.is_absolute() or ".." in path.parts:
        return None
    normalizado = path.as_posix()
    return None if normalizado in ("", ".") else normalizado


def bloquear_sobrescrita_herdada(tool, args, tool_context) -> dict | None:
    """Impede ``tool_criar_arquivo`` de sobrescrever arquivo de task anterior.

    Arquivos novos da task atual continuam livres, inclusive em retries. Um
    arquivo herdado pode ser modificado conscientemente após leitura usando
    ``tool_substituir_trecho``; apenas a substituição integral e cega é barrada.
    """
    if getattr(tool, "name", None) != "tool_criar_arquivo":
        return None

    herdados = tool_context.state.get(CHAVE_ARQUIVOS_HERDADOS)
    if herdados is None:
        # Execuções diretas do coder, fora do TaskIterator, preservam o
        # comportamento legado porque não possuem baseline por task.
        return None
    if not isinstance(herdados, list):
        return {
            "sucesso": False,
            "codigo": "BASELINE_DA_TASK_INVALIDA",
            "erro": (
                "A fotografia dos arquivos anteriores desta task está inválida; "
                "a sobrescrita integral foi bloqueada por segurança."
            ),
            "caminho": args.get("caminho"),
        }

    caminho = _normalizar_caminho(args.get("caminho"))
    if caminho is None or caminho not in set(herdados):
        return None

    return {
        "sucesso": False,
        "codigo": "SOBRESCRITA_INTER_TASK_BLOQUEADA",
        "erro": (
            f"O arquivo '{caminho}' já existia antes da task atual e não pode "
            "ser sobrescrito integralmente com tool_criar_arquivo. Leia-o com "
            "tool_ler_arquivo e altere somente o trecho necessário usando "
            "tool_substituir_trecho. Não recrie o projeto nem o PLAN.md."
        ),
        "caminho": caminho,
    }


def anunciar_arquivos_herdados(tool, args, tool_context, tool_response):
    """Anexa à resposta de `tool_listar_workspace` o estado real do projeto.

    Transforma o aviso "o projeto já existe, não recrie" de instrução em prosa
    (que a run do "fotógrafo" mostrou ser ignorada em 5 de 5 tasks) em DADO
    ESTRUTURADO devolvido por uma tool — o canal ao qual o coder comprovadamente
    reage. Ver a docstring do módulo para a evidência.

    Só atua quando há arquivos herdados, isto é, a partir da 2ª task. Na
    primeira o projeto está sendo criado do zero e o aviso seria falso.

    Returns:
        Dict que SUBSTITUI a resposta da tool (o ADK usa o retorno não-`None` do
        `after_tool_callback` no lugar do original), preservando a listagem em
        `itens`. `None` deixa a resposta original intacta — inclusive quando a
        tool devolveu erro, caso em que anexar o aviso só confundiria.
    """
    if getattr(tool, "name", None) != _TOOL_ANUNCIADA:
        return None

    herdados = tool_context.state.get(CHAVE_ARQUIVOS_HERDADOS)
    if not isinstance(herdados, list) or not herdados:
        return None

    # A tool sinaliza falha devolvendo uma string "Erro: ..." em vez da lista.
    if not isinstance(tool_response, list):
        return None

    mostrados = [c for c in herdados[:_MAX_ARQUIVOS_NO_AVISO] if isinstance(c, str)]
    omitidos = len(herdados) - len(mostrados)

    return {
        "itens": tool_response,
        "projeto_ja_implementado": True,
        "arquivos_existentes_no_workspace": mostrados,
        "arquivos_omitidos_deste_aviso": omitidos,
        "instrucao_obrigatoria": (
            "O projeto JÁ foi implementado por uma task anterior desta mesma "
            "execução — os arquivos acima já existem no workspace. NÃO recrie o "
            "PLAN.md, NÃO refaça o planejamento e NÃO reimplemente o que já "
            "está pronto: `tool_criar_arquivo` sobre qualquer um desses "
            "caminhos será RECUSADO. Para alterar um arquivo existente, leia-o "
            "com `tool_ler_arquivo` e edite o trecho com "
            "`tool_substituir_trecho`. Use `tool_criar_arquivo` apenas para "
            "arquivos NOVOS, exigidos especificamente pela task atual."
        ),
    }


def _remover_da_baseline(herdados: list, caminho: str) -> list:
    """Devolve a baseline sem o caminho removido e sem o que havia sob ele."""
    prefixo = f"{caminho}/"
    return [
        item
        for item in herdados
        if not (item == caminho or (isinstance(item, str) and item.startswith(prefixo)))
    ]


def auditar_remocao(tool, args, tool_context, tool_response) -> None:
    """Registra a remoção feita pelo coder e libera o caminho na baseline.

    Duas responsabilidades, ambas determinísticas:

    1. **Auditoria.** Toda chamada a ``tool_remover_arquivo`` vira uma linha de
       log com a task corrente, o caminho pedido e o desfecho — é o que permite
       rastrear depois o que sumiu do workspace e por conta de qual task.
    2. **Baseline.** Remover um arquivo herdado é ato explícito, não sobrescrita
       cega: o caminho sai de ``CHAVE_ARQUIVOS_HERDADOS`` para que a task possa
       recriá-lo (renomeação, troca de implementação) sem esbarrar no
       ``SOBRESCRITA_INTER_TASK_BLOQUEADA``. Só acontece quando a remoção
       **de fato ocorreu**; recusa nenhuma altera a fotografia.

    Devolve sempre ``None`` — o retorno da tool chega ao modelo intacto.
    """
    if getattr(tool, "name", None) != NOME_TOOL_REMOCAO:
        return None

    solicitado = args.get("caminho") if isinstance(args, dict) else None
    task_id = tool_context.state.get("task_id") or "sem_task"
    resposta = tool_response if isinstance(tool_response, dict) else {}

    if resposta.get("sucesso") is not True:
        logger.warning(
            "[CODER][%s] remoção RECUSADA de '%s': %s",
            task_id,
            solicitado,
            resposta.get("codigo") or "resposta_inesperada",
        )
        return None

    logger.info(
        "[CODER][%s] REMOVIDO do workspace (%s): '%s' -> %s",
        task_id,
        resposta.get("tipo") or "desconhecido",
        solicitado,
        resposta.get("caminho"),
    )

    caminho = _normalizar_caminho(solicitado)
    if caminho is None:
        return None

    herdados = tool_context.state.get(CHAVE_ARQUIVOS_HERDADOS)
    if isinstance(herdados, list):
        restante = _remover_da_baseline(herdados, caminho)
        if len(restante) != len(herdados):
            tool_context.state[CHAVE_ARQUIVOS_HERDADOS] = restante

    return None