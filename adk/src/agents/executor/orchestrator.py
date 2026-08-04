"""Executor como `BaseAgent` — a decisão de encerrar o loop vira código.

O fluxo que antes vivia em `prompt.py` (rodar o harness → acionar o validador →
obedecer ao veredito) passa a ser executado deterministicamente: sem LLM no
topo, não há o que reinterpretar. A "salvaguarda" em prosa do prompt existia
para impedir que o LLM decidisse sozinho; aqui ela é desnecessária, porque a
decisão é o próprio código.

Por iteração do loop `[coder → executor]`:

1. Roda o harness sobre o Work Item atual, persistindo o ExecutionReport.
2. Invoca o `implementation_validator` como SUB-AGENTE (`run_async`), que ao
   terminar já deixa `state['validation']` preenchido pela sua política
   determinística — o `after_agent_callback` dispara dentro do próprio
   `run_async`, sem chamada extra daqui.
3. Decide a partir de `ValidationVerdict.status`, e só dele:
   - `aprovado`  → encerra o loop (Event com `EventActions(escalate=True)`,
     equivalente ao `exit_loop` de quando isto era tool call);
   - `reprovado` → devolve ao coder o `ErrorReport` determinístico do hook
     injetado, SEM encerrar.

O `overall_status` técnico do harness nunca encerra o loop sozinho — como
antes, só o veredito encerra.

A única outra saída é a ESTAGNAÇÃO (ver `estagnacao.py`): quando o mesmo par
`(hash do código, blocking_reason)` se repete em 3 iterações consecutivas, o
loop encerra com o resumo `bloqueado` em vez do ErrorReport. Encerrar por
estagnação NÃO é aprovar — o veredito continua reprovado.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Callable, Optional

from google.adk.agents import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.genai import types
from pydantic import ConfigDict, PrivateAttr

from shared.tools.harness_execucao import executar_harness_validacao
from shared.workspace import get_agent_workspace

from .estagnacao import LIMITE_REPETICOES, hash_codigo, resumo_bloqueado

logger = logging.getLogger(__name__)

# Hook que monta o relatório devolvido ao coder quando o veredito é reprovado.
# Recebe um contexto com `.state` (o CallbackContext desta invocação) e devolve
# o Content a emitir, ou None quando não há relatório a emitir.
ErrorReportBuilder = Callable[[CallbackContext], Optional[types.Content]]

_CHAVE_ITERACAO = "executor_iteration"
_CHAVE_CONTAGEM_ESTAGNACAO = "stagnation_count"
_CHAVE_CHAVE_ESTAGNACAO = "stagnation_key"


class ExecutorOrchestrator(BaseAgent):
    """Orquestra harness → validador → decisão de encerramento, sem LLM."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Hook injetado por quem instancia — dependência de comportamento, não
    # configuração serializável do agente; por isso PrivateAttr.
    _error_report_builder: Optional[ErrorReportBuilder] = PrivateAttr(default=None)

    def __init__(
        self,
        *,
        validator: BaseAgent,
        error_report_builder: Optional[ErrorReportBuilder] = None,
        **kwargs: Any,
    ) -> None:
        """Args:
        validator: agente de validação a usar como sub-agente. É injetado, e
            não importado como singleton, porque o ADK exige parent ÚNICO em
            `sub_agents` — use `implementation_validator.agent.criar_agente()`
            para obter uma instância própria por orquestração.
        error_report_builder: hook que monta o `ErrorReport` do turno reprovado
            (ver `executor/error_report.py`). Sem ele, um veredito reprovado
            apenas registra o `blocking_reason` em texto — o loop continua
            igual, mas o coder não recebe a evidência bruta dos estágios.
        """
        super().__init__(sub_agents=[validator], **kwargs)
        self._error_report_builder = error_report_builder

    @property
    def validator(self) -> BaseAgent:
        """O agente de validação — mesma instância passada ao construtor."""
        return self.sub_agents[0]

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # CallbackContext expõe o `.state` delta-aware desta invocação: as
        # escritas caem direto em ctx.session.state (visíveis já para o
        # validador, que compartilha a sessão) e ficam acumuladas em
        # `.actions.state_delta` para viajar nos Events que emitimos — é assim
        # que report_path/task_id chegam a ser persistidos.
        cb = CallbackContext(ctx)

        task_id = self._resolver_task_id(cb)
        if not task_id:
            logger.warning(
                "executor: nenhum task_id resolvível no state; harness não "
                "executado nesta iteração."
            )
            yield self._evento_texto(
                ctx,
                "Não foi possível identificar o Work Item a validar: nem "
                "`task_id` nem `tasks` estão no state da sessão.",
                cb,
            )
            return

        iteration = self._proxima_iteracao(cb)

        # ---- 1. Harness ----
        # Chamada síncrona direta, como a FunctionTool do ADK já fazia com esta
        # mesma função (ela não é awaitable e o ADK a invoca inline).
        payload = executar_harness_validacao(task_id, iteration, tool_context=cb)
        report_path = payload.get("report_path", "")

        # O report_path vai no CONTEÚDO do turno porque é assim que ele entra no
        # contexto do validador — que antes o recebia como argumento da
        # AgentTool. A política do validador o lê do state (fonte determinística);
        # o LLM dele precisa vê-lo aqui para saber o que ler do disco.
        yield self._evento_texto(
            ctx,
            f"Harness executado para {task_id} (iteração {iteration}). "
            f"REPORT_PATH: {report_path}",
            cb,
        )

        # ---- 2. Validador como sub-agente ----
        # Ao final deste laço, `state['validation']` já está escrito pela
        # política determinística do validador (o after_agent_callback dele
        # dispara dentro do próprio run_async).
        async for event in self.validator.run_async(ctx):
            yield event

        # ---- 3. Decisão — obedece ao veredito, e só a ele ----
        validation = ctx.session.state.get("validation") or {}
        status = validation.get("status")

        if status == "aprovado":
            yield self._evento_texto(
                ctx,
                f"Veredito APROVADO para {task_id}. "
                f"{validation.get('summary') or ''}".rstrip(),
                cb,
                escalate=True,
            )
            return

        if status != "reprovado":
            # A política do validador nunca deixa de emitir veredito (o
            # fail-safe dela reprova). Um status ausente/inesperado aqui
            # significa que a propagação falhou — tratar como aprovação seria
            # exatamente o erro que a salvaguarda antiga existia para impedir.
            logger.warning(
                "executor: veredito ausente ou inesperado (%r); tratando como "
                "não-aprovação e mantendo o loop.",
                status,
            )

        # ---- 3a. Estagnação — avaliada ANTES de montar o ErrorReport ----
        # A ordem importa: no caminho de estagnação o builder nem chega a ser
        # chamado, então o resumo `bloqueado` é o que persiste em
        # `execution_result`. (O builder também reconhece o marcador e devolve
        # None, mas depender só disso deixaria a garantia num efeito colateral.)
        repeticoes = self._contar_estagnacao(cb, validation)
        if repeticoes >= LIMITE_REPETICOES:
            resumo = resumo_bloqueado(
                validation.get("blocking_reason") or "", repeticoes
            )
            cb.state["execution_result"] = resumo
            logger.info(
                "executor: estagnação em %s — mesmo (hash, blocking_reason) por "
                "%d iterações consecutivas; encerrando como bloqueado.",
                task_id,
                repeticoes,
            )
            yield self._evento_texto(ctx, resumo, cb, escalate=True)
            return

        conteudo = (
            self._error_report_builder(cb) if self._error_report_builder else None
        )
        if conteudo is not None:
            yield Event(
                author=self.name,
                invocation_id=ctx.invocation_id,
                branch=ctx.branch,
                content=conteudo,
                actions=self._drenar_actions(cb),
            )
            return

        yield self._evento_texto(
            ctx,
            f"Veredito REPROVADO para {task_id}: "
            f"{validation.get('blocking_reason') or 'sem blocking_reason.'}",
            cb,
        )

    # ------------------------------------------------------------------
    # Resolução determinística das entradas do harness
    # ------------------------------------------------------------------

    @staticmethod
    def _resolver_task_id(cb: CallbackContext) -> str:
        """Identifica o Work Item a validar, sem depender de LLM.

        Duas fontes, nesta ordem:
          1. `state['task_id']` — gravado pelo próprio harness numa iteração
             anterior, o que mantém o mesmo Work Item ao longo do loop;
          2. a primeira task de `state['tasks']`, a saída estruturada que o
             context_engineer já grava (`output_key="tasks"`) antes do loop
             começar.

        Devolve "" quando nenhuma das duas resolve — quem chama decide o que
        fazer (aqui: não rodar o harness e registrar o motivo).
        """
        do_state = cb.state.get("task_id")
        if isinstance(do_state, str) and do_state:
            return do_state

        try:
            task_id = cb.state["tasks"]["tasks"][0]["id"]
        except (KeyError, TypeError, IndexError):
            return ""

        return task_id if isinstance(task_id, str) else ""

    @staticmethod
    def _contar_estagnacao(cb: CallbackContext, validation: dict) -> int:
        """Repetições CONSECUTIVAS do par `(hash do código, blocking_reason)`.

        Devolve 1 na primeira reprovação de um par novo, e incrementa enquanto o
        par se repetir. Qualquer mudança em uma das metades zera a contagem —
        `LIMITE_REPETICOES` é sobre repetições seguidas, não acumuladas.

        Vive no state pelo mesmo motivo que `_proxima_iteracao`: acompanha a
        sessão, não o processo. A chave é gravada como lista porque é assim que
        ela sobrevive à serialização do session state.
        """
        par = [
            hash_codigo(get_agent_workspace("cr_coder")),
            validation.get("blocking_reason") or "",
        ]

        anterior = cb.state.get(_CHAVE_CHAVE_ESTAGNACAO)
        contagem = cb.state.get(_CHAVE_CONTAGEM_ESTAGNACAO)
        if par == anterior and isinstance(contagem, int):
            atual = contagem + 1
        else:
            atual = 1

        cb.state[_CHAVE_CHAVE_ESTAGNACAO] = par
        cb.state[_CHAVE_CONTAGEM_ESTAGNACAO] = atual
        return atual

    @staticmethod
    def _proxima_iteracao(cb: CallbackContext) -> int:
        """Conta as passagens do executor nesta sessão (1 na primeira).

        Vive no state, e não num atributo de instância, porque é o número que o
        harness registra no ExecutionReport — precisa acompanhar a sessão, não
        o processo.
        """
        anterior = cb.state.get(_CHAVE_ITERACAO)
        atual = (anterior + 1) if isinstance(anterior, int) else 1
        cb.state[_CHAVE_ITERACAO] = atual
        return atual

    # ------------------------------------------------------------------
    # Construção de eventos
    # ------------------------------------------------------------------

    @staticmethod
    def _drenar_actions(cb: CallbackContext, *, escalate: bool = False) -> EventActions:
        """Transfere o state_delta pendente para um `EventActions` do evento.

        Cada Event leva o seu próprio objeto de actions: reaproveitar
        `cb.actions` faria dois eventos compartilharem a mesma instância
        mutável, e as escritas posteriores alterariam retroativamente um evento
        já emitido.
        """
        delta = dict(cb.actions.state_delta)
        cb.actions.state_delta.clear()
        return EventActions(state_delta=delta, escalate=escalate)

    def _evento_texto(
        self,
        ctx: InvocationContext,
        texto: str,
        cb: CallbackContext,
        *,
        escalate: bool = False,
    ) -> Event:
        return Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=texto)]),
            actions=self._drenar_actions(cb, escalate=escalate),
        )
