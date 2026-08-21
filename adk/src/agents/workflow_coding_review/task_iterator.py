"""TaskIterator — iteração determinística sobre as tasks do coding_review.

Fecha a causa raiz da issue #369: o `task_id` deixava de ser escolhido por
código e ficava a cargo do LLM, de modo que apenas a primeira task acabava
processada. Este agente percorre POR CÓDIGO todas as tasks emitidas pelo
context_engineer, invocando o `code_execute_loop` (coder ↔ executor) uma vez
por task, e calcula de forma determinística se a cobertura ficou completa.

A divisão de responsabilidades do workflow é preservada: o iterator NÃO julga
implementação. Ele escopa a task da vez, classifica o desfecho a partir do
veredito que o `implementation_validator` já gravou em `state['validation']` e
agrega tudo em `state['task_iteration_summary']`.

Nenhum LLM participa das decisões deste módulo.

`cobertura_completa` é calculado e publicado no state para o gate determinístico
do reviewer, que impede a sinalização final de aprovação quando a cobertura não
foi comprovada.
"""

from __future__ import annotations

import logging
import re
from typing import Any, AsyncGenerator, Optional

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions

from src.agents.implementation_validator.agent import _report_path_valido

from .coder.workspace_guard import preparar_arquivos_herdados
from .executor.loop_policy import CHAVE_MOTIVO_PARADA, CHAVES_DE_CICLO

logger = logging.getLogger(__name__)

# Formato do id de task emitido pelo context_engineer ("TASK-XXX (sequencial)",
# ver context_engineer/prompt.py). Estrito de propósito: o id validado aqui é
# usado sem sanitização adicional para compor o nome da branch da task.
_ID_TASK_RE = re.compile(r"^TASK-[0-9]{3,}$")

# Chaves de ciclo do loop coder ↔ executor, removidas entre tasks para que uma
# task nunca herde o desfecho da anterior. Removidas (pop) e não zeradas: quem
# as consome checa ausência, e `None` não representa ausência sem ambiguidade.
#
# As chaves da política de progresso vêm de `CHAVES_DE_CICLO` (issue #394) em vez
# de repetidas aqui: quem as cria é o `loop_policy`, e uma chave nova que
# escapasse desta limpeza faria a task seguinte herdar o histórico da anterior —
# a primeira rodada dela seria lida como "sem alteração" e poderia ser cortada
# antes de qualquer tentativa real.
_CHAVES_CICLO_REMOVIDAS = (
    "validation",
    "report_path",
    "error_report",
) + CHAVES_DE_CICLO

# Marcador do 3º ramo do coder (ver coder/prompt.py): a partir da 2ª task,
# `execution_result` nunca fica ausente — se ficasse, o coder entenderia
# "primeira execução" e tentaria reconstruir o projeto do zero.
_MARCADOR_NOVA_TASK = "NOVA_TASK:"


def marcador_nova_task(task_id: str) -> str:
    """Conteúdo de `execution_result` injetado a partir da 2ª task."""
    return (
        f"{_MARCADOR_NOVA_TASK} validação da task {task_id} — projeto já "
        "implementado por uma task anterior nesta mesma execução. Ainda não "
        "há erro registrado para esta task específica."
    )


def branch_da_task(branch_base: Optional[str], indice: int, task_id: str) -> str:
    """Branch-irmã dedicada à task, para isolar o histórico entre tasks."""
    sufixo = f"task_iterator.task_{indice}_{task_id}"
    return f"{branch_base}.{sufixo}" if branch_base else sufixo


def detalhe_erro_operacional(exc: Exception) -> str:
    """Resumo seguro de uma exceção; detalhes e traceback permanecem no log.

    Mensagens de bibliotecas podem conter paths, URLs, payloads ou credenciais.
    O summary será consumido downstream na Fatia 2, por isso registra somente
    o tipo da falha e direciona os detalhes para o canal de log.
    """
    return f"{type(exc).__name__}: erro operacional; consulte os logs."


# ---------------------------------------------------------------------------
# Validação do envelope de entrada
# ---------------------------------------------------------------------------


def validar_envelope_de_tasks(envelope: Any) -> tuple[list[dict], list[dict]]:
    """Valida `state['tasks']` inteiro — envelope, lista e cada id.

    Nunca indexa sem checar antes: um envelope malformado vira `input_errors`
    tipados, não uma exceção. Qualquer erro invalida a iteração INTEIRA (nenhuma
    task é processada), porque uma lista de tasks parcialmente confiável não
    permite afirmar cobertura.

    Returns:
        (tasks_validas, input_errors) — `tasks_validas` é vazia sempre que
        houver ao menos um erro.
    """
    if envelope is None:
        return [], [
            {
                "type": "tasks_ausente",
                "detalhe": "state['tasks'] ausente — o context_engineer não publicou tasks.",
            }
        ]
    if not isinstance(envelope, dict):
        return [], [
            {
                "type": "envelope_invalido",
                "detalhe": f"state['tasks'] é {type(envelope).__name__}; esperado dict.",
            }
        ]
    if "tasks" not in envelope:
        return [], [
            {
                "type": "lista_ausente",
                "detalhe": "state['tasks']['tasks'] ausente no envelope.",
            }
        ]

    lista = envelope["tasks"]
    if not isinstance(lista, list):
        return [], [
            {
                "type": "lista_tipo_invalido",
                "detalhe": f"state['tasks']['tasks'] é {type(lista).__name__}; esperado list.",
            }
        ]
    if not lista:
        return [], [
            {
                "type": "lista_vazia",
                "detalhe": "state['tasks']['tasks'] é uma lista vazia.",
            }
        ]

    erros: list[dict] = []
    vistos: set[str] = set()
    for indice, item in enumerate(lista):
        if not isinstance(item, dict):
            erros.append(
                {
                    "type": "task_tipo_invalido",
                    "detalhe": f"índice {indice}: {type(item).__name__}; esperado dict.",
                }
            )
            continue
        if "id" not in item:
            erros.append(
                {
                    "type": "id_ausente",
                    "detalhe": f"índice {indice}: task sem a chave 'id'.",
                }
            )
            continue
        task_id = item["id"]
        if not isinstance(task_id, str):
            erros.append(
                {
                    "type": "id_tipo_invalido",
                    "detalhe": f"índice {indice}: id é {type(task_id).__name__}; esperado str.",
                }
            )
            continue
        if not _ID_TASK_RE.match(task_id):
            erros.append(
                {
                    "type": "id_invalido",
                    "detalhe": (
                        f"índice {indice}: id {task_id!r} não casa com "
                        f"{_ID_TASK_RE.pattern}."
                    ),
                }
            )
            continue
        if task_id in vistos:
            erros.append(
                {
                    "type": "id_duplicado",
                    "detalhe": f"índice {indice}: id {task_id!r} repetido na lista.",
                }
            )
            continue
        vistos.add(task_id)

    if erros:
        return [], erros
    return list(lista), []


# ---------------------------------------------------------------------------
# Classificação do desfecho de uma task
# ---------------------------------------------------------------------------


def _normalizar_validation(bruto: Any) -> Optional[dict]:
    """Devolve o veredito como dict, ou None se não for utilizável.

    O callback do `implementation_validator` grava `verdict.model_dump()` — o
    valor normal já é dict. A normalização cobre o caso de algum caminho gravar
    o `BaseModel` diretamente; qualquer coisa que não vire dict é inválida.
    """
    if isinstance(bruto, dict):
        return bruto
    model_dump = getattr(bruto, "model_dump", None)
    if callable(model_dump):
        try:
            valor = model_dump()
        except Exception:  # noqa: BLE001 — veredito ilegível é veredito inválido
            return None
        return valor if isinstance(valor, dict) else None
    return None


def _motivo_de_travamento(state: dict) -> Optional[str]:
    """Motivo do encerramento por travamento, se houve um.

    Lê o campo TIPADO que a política de progresso grava
    (`state['loop_stop_reason']`, issue #394). Substituiu o string-sniffing de
    `"STATUS: bloqueado"` na primeira linha de `execution_result`, que dependia
    de o LLM do executor escrever o marcador exato — mesma postura do resto
    deste módulo, que evita confiar em texto cru (ver `_normalizar_validation`).
    """
    motivo = state.get(CHAVE_MOTIVO_PARADA)
    if isinstance(motivo, str) and motivo:
        return motivo
    return None


def _progresso(state: dict) -> dict:
    """Nota final e histórico da task, para o summary do iterator.

    Vai em TODOS os ramos de `classificar_desfecho`, não só no de sucesso: uma
    task reprovada ou travada é exatamente o caso em que o histórico mais
    importa para auditoria e para a revisão a jusante.
    """
    historico = state.get("progress_score_history")
    historico = (
        [n for n in historico if isinstance(n, (int, float))]
        if isinstance(historico, list)
        else []
    )
    return {
        "nota_final": historico[-1] if historico else None,
        "historico_notas": historico,
    }


def classificar_desfecho(state: dict, task_id: str) -> dict:
    """Classifica o desfecho da task a partir do state, sem confiar cegamente.

    O veredito só é aceito se for um dict E se `work_item_id` corresponder à
    task da vez — um veredito remanescente de outra task não pode aprovar esta.
    """
    report_path = state.get("report_path")
    if not (isinstance(report_path, str) and _report_path_valido(report_path, task_id)):
        report_path = None

    progresso = _progresso(state)
    motivo_travamento = _motivo_de_travamento(state)

    validation = _normalizar_validation(state.get("validation"))
    if validation is None or validation.get("work_item_id") != task_id:
        # Travamento ANTES de existir veredito. Acontece quando o gate estrutural
        # recusa todas as rodadas: o coder nunca produz o mínimo executável, o
        # harness nunca roda e o validador nunca é acionado — mas a política de
        # progresso encerrou o loop por decisão determinística.
        #
        # Sem este ramo, o desfecho virava "validation_ausente_ou_invalida", uma
        # falha genérica que esconde a informação mais útil que temos: POR QUE o
        # loop parou. O `loop_stop_reason` é confiável aqui porque é limpo entre
        # tasks (CHAVES_DE_CICLO), então só pode ser desta task.
        if motivo_travamento is not None:
            return {
                "status": "bloqueado",
                "blocking_reason": (
                    "Loop encerrado por falta de progresso antes de haver "
                    f"veredito (motivo: {motivo_travamento}). O artefato não "
                    "chegou a ser executável."
                ),
                "report_path": report_path,
                "motivo_terminacao": f"bloqueado_{motivo_travamento}",
                **progresso,
            }
        return {
            "status": "reprovado",
            "blocking_reason": (
                "Veredito ausente, ilegível ou referente a outro work item em "
                "state['validation']."
            ),
            "report_path": report_path,
            "motivo_terminacao": "validation_ausente_ou_invalida",
            **progresso,
        }

    status_veredito = validation.get("status")
    blocking_reason = validation.get("blocking_reason")

    if status_veredito == "aprovado":
        return {
            "status": "aprovado",
            "blocking_reason": blocking_reason,
            "report_path": report_path,
            "motivo_terminacao": "aprovado",
            **progresso,
        }

    if status_veredito == "reprovado":
        if motivo_travamento is not None:
            # O motivo específico (platô / sem alteração / erro repetido) é
            # preservado no lugar do antigo "bloqueado_estagnacao" genérico: o
            # dado já existe e distingue "a solução parou de evoluir" de "o
            # coder parou de mexer no código", que pedem análises diferentes.
            return {
                "status": "bloqueado",
                "blocking_reason": blocking_reason,
                "report_path": report_path,
                "motivo_terminacao": f"bloqueado_{motivo_travamento}",
                **progresso,
            }
        return {
            "status": "reprovado",
            "blocking_reason": blocking_reason,
            "report_path": report_path,
            "motivo_terminacao": "reprovado_apos_loop",
            **progresso,
        }

    # Status fora do enum VerdictStatus — fail-closed, como veredito inválido.
    return {
        "status": "reprovado",
        "blocking_reason": (f"Veredito com status inesperado: {status_veredito!r}."),
        "report_path": report_path,
        "motivo_terminacao": "validation_ausente_ou_invalida",
        **progresso,
    }


def calcular_cobertura(
    input_valid: bool,
    expected_task_ids: list[str],
    processed_task_ids: list[str],
    approved_task_ids: list[str],
) -> bool:
    """Gate de completude, fail-closed.

    `len(expected) > 0` é explícito: sem ele, uma lista vazia satisfaria
    `expected == processed == approved` trivialmente e aprovaria no vácuo.
    """
    return (
        input_valid
        and len(expected_task_ids) > 0
        and set(expected_task_ids) == set(processed_task_ids)
        and set(expected_task_ids) == set(approved_task_ids)
    )


def montar_summary(
    *,
    input_valid: bool,
    input_errors: list[dict],
    expected_task_ids: list[str],
    processed_task_ids: list[str],
    approved_task_ids: list[str],
    task_results: dict[str, dict],
) -> dict:
    """Monta o `task_iteration_summary` (sempre um objeto novo, sem aliasing)."""
    return {
        "input_valid": input_valid,
        "input_errors": [dict(e) for e in input_errors],
        "expected_task_ids": list(expected_task_ids),
        "processed_task_ids": list(processed_task_ids),
        "approved_task_ids": list(approved_task_ids),
        "task_results": {k: dict(v) for k, v in task_results.items()},
        "cobertura_completa": calcular_cobertura(
            input_valid, expected_task_ids, processed_task_ids, approved_task_ids
        ),
    }


# ---------------------------------------------------------------------------
# Agente
# ---------------------------------------------------------------------------


class TaskIterator(BaseAgent):
    """Itera as tasks do context_engineer, uma invocação do loop por task.

    O `code_execute_loop` é declarado como `sub_agent` de verdade (preservando
    descoberta, observabilidade e introspecção da árvore), mas QUANDO e QUANTAS
    vezes ele roda é decidido aqui, no `_run_async_impl`.
    """

    @property
    def _sub_loop(self) -> BaseAgent:
        """O `code_execute_loop` — único sub-agente deste iterator."""
        if len(self.sub_agents) != 1:
            raise RuntimeError(
                "TaskIterator exige exatamente um sub_agent (code_execute_loop); "
                f"recebeu {len(self.sub_agents)}."
            )
        return self.sub_agents[0]

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state

        tasks, input_errors = validar_envelope_de_tasks(state.get("tasks"))
        if input_errors:
            logger.error(
                "[TASK_ITERATOR] Envelope de tasks inválido (%d erro(s)); "
                "nenhuma task será processada: %s",
                len(input_errors),
                input_errors,
            )
            yield self._evento_summary(
                ctx,
                state,
                montar_summary(
                    input_valid=False,
                    input_errors=input_errors,
                    expected_task_ids=[],
                    processed_task_ids=[],
                    approved_task_ids=[],
                    task_results={},
                ),
            )
            return

        expected_task_ids = [t["id"] for t in tasks]
        processed_task_ids: list[str] = []
        approved_task_ids: list[str] = []
        task_results: dict[str, dict] = {}

        def _summary() -> dict:
            return montar_summary(
                input_valid=True,
                input_errors=[],
                expected_task_ids=expected_task_ids,
                processed_task_ids=processed_task_ids,
                approved_task_ids=approved_task_ids,
                task_results=task_results,
            )

        # Summary inicial: o conjunto esperado passa a ser observável antes da
        # primeira task, para que uma interrupção no meio dela não deixe o
        # summary totalmente ausente.
        logger.info(
            "[TASK_ITERATOR] %d task(s) a processar: %s",
            len(expected_task_ids),
            expected_task_ids,
        )
        yield self._evento_summary(ctx, state, _summary())

        for indice, task in enumerate(tasks):
            task_id = task["id"]
            self._resetar_ciclo(state, primeira=(indice == 0), task_id=task_id)
            preparar_arquivos_herdados(state, primeira=(indice == 0))
            state["task_id"] = task_id

            task_ctx = ctx.model_copy(
                update={"branch": branch_da_task(ctx.branch, indice, task_id)}
            )

            logger.info(
                "[TASK_ITERATOR] Iniciando task %s (%d/%d).",
                task_id,
                indice + 1,
                len(expected_task_ids),
            )

            try:
                async for event in self._sub_loop.run_async(task_ctx):
                    yield event
            except Exception as exc:  # noqa: BLE001 — isolamento por task
                # CancelledError/KeyboardInterrupt/SystemExit/GeneratorExit
                # derivam de BaseException e continuam propagando.
                logger.exception(
                    "[TASK_ITERATOR] Erro operacional na task %s; seguindo "
                    "para a próxima.",
                    task_id,
                )
                resultado = {
                    "status": "reprovado",
                    "blocking_reason": detalhe_erro_operacional(exc),
                    "report_path": None,
                    "motivo_terminacao": "erro_operacional",
                    # Também aqui: a task pode ter progredido por várias rodadas
                    # antes do erro operacional, e esse histórico é a única
                    # pista do que ela chegou a alcançar.
                    **_progresso(state),
                }
            else:
                resultado = classificar_desfecho(state, task_id)

            task_results[task_id] = resultado
            processed_task_ids.append(task_id)
            if resultado["status"] == "aprovado":
                approved_task_ids.append(task_id)

            logger.info(
                "[TASK_ITERATOR] Task %s encerrada: status=%s motivo=%s",
                task_id,
                resultado["status"],
                resultado["motivo_terminacao"],
            )
            yield self._evento_summary(ctx, state, _summary(), task_id=task_id)

    @staticmethod
    def _resetar_ciclo(state: dict, *, primeira: bool, task_id: str) -> None:
        """Zera as chaves de ciclo do loop antes de escopar a próxima task.

        `execution_result` recebe tratamento próprio porque é ele que discrimina
        os ramos do coder: ausente = primeira execução (cria o PLAN.md e
        implementa do zero); presente = já há projeto. A partir da 2ª task,
        injetamos o marcador NOVA_TASK para que o coder não recomece o projeto.
        """
        for chave in _CHAVES_CICLO_REMOVIDAS:
            state.pop(chave, None)
        if primeira:
            state.pop("execution_result", None)
        else:
            state["execution_result"] = marcador_nova_task(task_id)

    def _evento_summary(
        self,
        ctx: InvocationContext,
        state: dict,
        summary: dict,
        task_id: Optional[str] = None,
    ) -> Event:
        """Atualiza o state local e devolve o evento que persiste o summary.

        `Session.state` é um dict puro (não a classe `State`, que rastreia
        delta), então a mutação local não seria persistida sozinha: o evento com
        `state_delta` é o que faz o summary sobreviver fora desta invocação. A
        mutação vem ANTES do yield porque o iterator não depende do round-trip
        do Runner para nada que ele mesmo precise ler em seguida.
        """
        state["task_iteration_summary"] = summary
        delta: dict[str, Any] = {"task_iteration_summary": summary}
        if task_id is not None:
            delta["task_id"] = task_id
        return Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            actions=EventActions(state_delta=delta),
        )
