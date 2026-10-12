"""Orchestrator SDLC v5 — Custom BaseAgent com HITL via LongRunningFunctionTool.

Evolução do v4 (sessões isoladas) com suporte real a pausa HITL no
qa_pipeline. Em vez de descartar a sessão do qa_pipeline ao fim de cada
invocação, mantemos o Runner vivo em `_live_runners[outer_session_id]`
quando o pipeline emite um function_call long-running pendente. Na
próxima invocação, o texto do usuário ("aprovar"/"rejeitar"/...) é
parseado em (decision, comments), embalado em function_response e
enviado ao runner pausado via runner.run_async — qa_pipeline retoma
exatamente de onde parou.

Estado persistido em ctx.session.state (sessão externa):
    accumulated_outputs: list[tuple[name, last_text]]
    paused_pipeline: str | None
    paused_inner_session_id: str | None
    paused_function_call: {id, name, args} | None

Contagem de tokens opcional (desligada por padrão, ver `shared.pipeline_flags`):
persistência por workflow e em token_usage.json, consumo por agente, tabela
nas pausas e total acumulado da sessão.

Estado em memória do processo (NÃO persistido — limitação documentada):
    _live_runners: dict[outer_session_id, tuple[Runner, inner_session_id]]
"""

from typing import Any, AsyncGenerator, ClassVar, Dict, List, Optional, Tuple

import logging
import time

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import ConfigDict, PrivateAttr

from src.agents.workflow_requirements.agent import agent as requirements_pipeline
from src.agents.workflow_design_pipeline.agent import agent as design_pipeline
from src.agents.workflow_coding_review.agent import agent as coding_review_pipeline
from src.agents.workflow_qa.agent import agent as qa_pipeline

from shared import pipeline_flags as flags
from shared.workspace import get_workspace_root, init_workspace
from shared.preflight import ensure_llm_ready
from shared.token_usage import (
    STAGE_LABELS,
    TokenUsage,
    bind_stage,
    current_stage,
    token_usage_plugin,
)

from src.agents.orchestrator._helpers import (
    _build_function_response_payload,
    _build_input,
    _build_manifest_input,
    _clear_pause_state,
    _extract_user_text,
    _is_empty_response,
    _is_pending_long_running_call,
    _load_phase_manifests,
    _merge_state_delta,
    _parse_decision,
    _set_pause_state,
    EMPTY_RETRY_PROMPT,
)


# Logger da narrativa de alto nível do orchestrator. Herda handler/nível do
# setup_adk_logger nativo (namespace google_adk). O orchestrator é um BaseAgent
# custom e não passa pelos callbacks de LlmAgent, então os plugins nativos
# capturam os sub-pipelines mas não a linha do tempo por estágio — este logger
# cobre exatamente esse gap (início/fim/duração/desfecho de cada pipeline).
logger = logging.getLogger("google_adk.orchestrator")

TOKEN_SNAPSHOT_FILENAME = "token_usage.json"


def _stage_label(pipeline_name: str) -> str:
    return STAGE_LABELS.get(pipeline_name, pipeline_name)


class _PipelineOrchestrator(BaseAgent):
    """Roda pipelines em sequência, com pausa HITL no qa_pipeline."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    _pipelines: ClassVar[List[BaseAgent]] = [
        requirements_pipeline,
        design_pipeline,
        coding_review_pipeline,
        qa_pipeline,
    ]

    # Runners vivos do pipeline pausado, indexados por outer_session_id.
    # NÃO persistido — reinício do servidor entre T0 e T1 perde isto.
    _live_runners: Dict[str, Tuple[Any, str]] = PrivateAttr(default_factory=dict)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        outer_sid = ctx.session.id
        user_text = _extract_user_text(ctx)
        if not user_text:
            return

        # Health-check rápido do LLM (1x por prompt): valida credencial + ping,
        # renova token em caso de falha; se o provedor estiver indisponível,
        # aborta cedo com mensagem acionável em vez de travar por minutos.
        preflight = await ensure_llm_ready()
        if not preflight.ok:
            logger.warning(
                "[ORCHESTRATOR] Preflight de LLM falhou, abortando prompt "
                "(session=%s): %s",
                outer_sid,
                preflight.message,
            )
            yield self._make_text_event(self.name, preflight.message)
            return

        paused = state.get("paused_pipeline")
        # Resume continua o acumulado salvo na pausa; fresh run começa do zero.
        usage = (
            TokenUsage.from_dict(
                state.get("token_usage"), state.get("token_usage_agents")
            )
            if paused
            else TokenUsage()
        )
        self._setup_usage(state, outer_sid, usage, new_run=not paused)

        try:
            # === Branch RESUME ===
            if paused:
                logger.info(
                    "[ORCHESTRATOR] Retomando pipeline pausado '%s' (session=%s)",
                    paused,
                    outer_sid,
                )
                async for ev in self._handle_resume(
                    ctx, outer_sid, user_text, usage
                ):
                    yield ev
                return

            # === Branch FRESH RUN ===
            logger.info(
                "[ORCHESTRATOR] Fresh run iniciado: %d pipelines (session=%s)",
                len(self._pipelines),
                outer_sid,
            )
            async for ev in self._handle_fresh_run(ctx, outer_sid, user_text, usage):
                yield ev
        except Exception as exc:
            # Execução abortada (ex.: rate limit do provedor): emite o consumo
            # até aqui antes de propagar o erro, senão os tokens gastos somem.
            stage = current_stage()
            logger.warning(
                "[ORCHESTRATOR] Execução falhou no workflow '%s'; emitindo "
                "relatório parcial de tokens (session=%s)",
                stage,
                outer_sid,
            )
            local = f"no workflow **{stage}**" if stage else "antes do primeiro workflow"
            # ParallelAgent embrulha a falha em ExceptionGroup — mostra a causa real.
            cause: BaseException = exc
            while isinstance(cause, BaseExceptionGroup) and cause.exceptions:
                cause = cause.exceptions[0]
            note = (
                f"Execução interrompida {local}: "
                f"`{type(cause).__name__}: {str(cause)[:300]}`"
            )
            delta = self._usage_delta(state, usage, status="falhou")
            yield self._make_text_event(
                self.name, self._report(state, usage, note=note), state_delta=delta
            )
            raise

    async def _handle_resume(
        self,
        ctx: InvocationContext,
        outer_sid: str,
        user_text: str,
        usage: TokenUsage,
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        paused = state["paused_pipeline"]
        runner_handle = self._live_runners.get(outer_sid)

        if runner_handle is None:
            # Servidor reiniciou entre T0 e T1 — runner perdeu-se.
            _clear_pause_state(state)
            yield self._make_text_event(
                paused,
                "Sessão HITL expirada (servidor foi reiniciado entre a pausa "
                "e a resposta). Por favor reenvie o prompt original para "
                "iniciar uma nova sessão.",
                state_delta={
                    "paused_pipeline": None,
                    "paused_inner_session_id": None,
                    "paused_function_call": None,
                },
            )
            return

        runner, inner_sid = runner_handle
        call = state["paused_function_call"]
        allowed = call["args"].get("allowed_decisions", []) or []

        try:
            decision, comments = _parse_decision(user_text, allowed)
        except ValueError as exc:
            yield self._make_text_event(
                paused,
                f"Decisão inválida: {exc}. "
                f"Por favor responda com uma destas opções: "
                f"{', '.join(allowed)}."
            )
            return  # pausa intacta

        # ADK exige que `id` no function_response case com o id do
        # function_call original. Construímos via FunctionResponse direto
        # porque `types.Part.from_function_response` não expõe `id=` em
        # algumas versões.
        function_response = types.Content(
            role="user",
            parts=[types.Part(function_response=types.FunctionResponse(
                id=call["id"],
                name=call["name"],
                response=_build_function_response_payload(
                    decision=decision,
                    comments=comments,
                    checkpoint_id=call["args"].get("checkpoint_id", ""),
                ),
            ))],
        )

        bind_stage(usage, paused)

        last_text = ""
        new_pause = None
        async for event in runner.run_async(
            user_id=ctx.user_id,
            session_id=inner_sid,
            new_message=function_response,
        ):
            yield event
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        last_text = part.text
                    elif _is_pending_long_running_call(part, event):
                        new_pause = part.function_call

        state["token_usage"] = usage.to_dict()

        if new_pause is not None:
            # Pausa encadeada — atualiza state, mantém runner.
            _set_pause_state(
                state,
                pipeline_name=paused,
                inner_session_id=inner_sid,
                function_call_id=new_pause.id,
                function_call_name=new_pause.name,
                function_call_args=dict(new_pause.args or {}),
            )
            delta = {
                "paused_pipeline": state["paused_pipeline"],
                "paused_inner_session_id": state["paused_inner_session_id"],
                "paused_function_call": state["paused_function_call"],
                "token_usage": state["token_usage"],
            }
            pause_text = self._pause_text(state, usage, paused)
            if pause_text:
                delta.update(self._usage_delta(state, usage, status="pausada"))
                yield self._make_text_event(self.name, pause_text, state_delta=delta)
            else:
                yield self._make_state_event(delta)
            return

        # Conclusão: cleanup.
        _clear_pause_state(state)
        accumulated = state.get("accumulated_outputs", []) or []
        accumulated.append((paused, last_text))
        state["accumulated_outputs"] = accumulated
        await runner.close()
        self._live_runners.pop(outer_sid, None)
        delta = self._usage_delta(state, usage, status="concluída")
        yield self._make_text_event(
            self.name,
            self._report(state, usage),
            state_delta={
                "paused_pipeline": None,
                "paused_inner_session_id": None,
                "paused_function_call": None,
                "accumulated_outputs": accumulated,
                **delta,
            },
        )

    async def _handle_fresh_run(
        self,
        ctx: InvocationContext,
        outer_sid: str,
        user_text: str,
        usage: TokenUsage,
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        # Fresh run reseta accumulated (nova conversa SDLC).
        state["accumulated_outputs"] = []
        accumulated: list[tuple[str, str]] = []
        state["token_usage"] = usage.to_dict()

        # Manifestos das fases anteriores — contrato leve entre Times.
        phase_manifests = _load_phase_manifests(state)

        # Garante o workspace da sessão (<WORKSPACE_OUTPUT_DIR>/<yyyyMMdd-HHmm>-<session_id>).
        # Não apaga nada: nova prompt na mesma sessão reaproveita a pasta.
        init_workspace()

        # Se houver _live_runner legado em outer_sid (sessão zombie), fecha.
        legacy = self._live_runners.pop(outer_sid, None)
        if legacy is not None:
            await legacy[0].close()

        for idx, pipeline in enumerate(self._pipelines):
            stage_started_at = time.perf_counter()
            logger.info(
                "[STAGE %d/%d] Iniciando pipeline '%s' (session=%s)",
                idx + 1,
                len(self._pipelines),
                pipeline.name,
                outer_sid,
            )
            # Dispatcher fino: repassa só os manifestos das fases anteriores.
            prior_manifests = phase_manifests[:idx]
            manifest_context = _build_manifest_input(prior_manifests)
            if manifest_context:
                pipeline_input = (
                    f"{user_text}\n\n"
                    f"---\n"
                    f"{manifest_context}\n"
                    f"---"
                )
            else:
                pipeline_input = user_text

            content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=pipeline_input)],
            )

            runner = Runner(
                app_name=pipeline.name,
                agent=pipeline,
                artifact_service=ctx.artifact_service,
                session_service=InMemorySessionService(),
                memory_service=InMemoryMemoryService(),
                credential_service=ctx.credential_service,
                plugins=[
                    *(ctx.plugin_manager.plugins if ctx.plugin_manager else []),
                    token_usage_plugin,
                ],
            )
            # Repassa os manifestos acumulados para o pipeline ler paths do workspace.
            inner_state = {
                "phase_manifests": [m.model_dump() for m in prior_manifests]
            }
            inner_session = await runner.session_service.create_session(
                app_name=pipeline.name, user_id=ctx.user_id, state=inner_state,
            )

            bind_stage(usage, pipeline.name)
            last_text = ""
            pending_pause = None
            async for event in runner.run_async(
                user_id=inner_session.user_id,
                session_id=inner_session.id,
                new_message=content,
            ):
                yield event
                # Aplica state_delta vindo do pipeline (ex: novo manifesto QA).
                if event.actions and event.actions.state_delta:
                    _merge_state_delta(state, event.actions.state_delta)
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            last_text = part.text
                        elif _is_pending_long_running_call(part, event):
                            pending_pause = part.function_call

            # RETRY: empty sem pausa = LLM falhou silenciosamente. Reinvoca 1x.
            if pending_pause is None and _is_empty_response(last_text):
                retry_content = types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=EMPTY_RETRY_PROMPT)],
                )
                last_text = ""
                async for event in runner.run_async(
                    user_id=inner_session.user_id,
                    session_id=inner_session.id,
                    new_message=retry_content,
                ):
                    yield event
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                last_text = part.text
                            elif _is_pending_long_running_call(part, event):
                                pending_pause = part.function_call

                if _is_empty_response(last_text) and pending_pause is None:
                    last_text = (
                        f"[orchestrator] pipeline {pipeline.name} "
                        "retornou empty após retry"
                    )
                    logger.warning(
                        "[STAGE %d/%d] Pipeline '%s' retornou empty após retry "
                        "(%.2fs)",
                        idx + 1,
                        len(self._pipelines),
                        pipeline.name,
                        time.perf_counter() - stage_started_at,
                    )

            if pending_pause is not None:
                # Salva estado, MANTÉM runner vivo (não fecha).
                logger.info(
                    "[STAGE %d/%d] Pipeline '%s' PAUSADO para HITL (call=%s, "
                    "%.2fs)",
                    idx + 1,
                    len(self._pipelines),
                    pipeline.name,
                    pending_pause.name,
                    time.perf_counter() - stage_started_at,
                )
                self._live_runners[outer_sid] = (runner, inner_session.id)
                state["token_usage"] = usage.to_dict()
                _set_pause_state(
                    state,
                    pipeline_name=pipeline.name,
                    inner_session_id=inner_session.id,
                    function_call_id=pending_pause.id,
                    function_call_name=pending_pause.name,
                    function_call_args=dict(pending_pause.args or {}),
                )
                state["accumulated_outputs"] = accumulated
                delta = {
                    "paused_pipeline": state["paused_pipeline"],
                    "paused_inner_session_id": state["paused_inner_session_id"],
                    "paused_function_call": state["paused_function_call"],
                    "accumulated_outputs": accumulated,
                    "phase_manifests": state.get("phase_manifests", []),
                    "token_usage": state["token_usage"],
                }
                pause_text = self._pause_text(state, usage, pipeline.name)
                if pause_text:
                    delta.update(self._usage_delta(state, usage, status="pausada"))
                    yield self._make_text_event(self.name, pause_text, state_delta=delta)
                else:
                    yield self._make_state_event(delta)
                return  # NÃO roda pipelines subsequentes

            # Pipeline concluiu sem pausa.
            logger.info(
                "[STAGE %d/%d] Pipeline '%s' concluído (%.2fs)",
                idx + 1,
                len(self._pipelines),
                pipeline.name,
                time.perf_counter() - stage_started_at,
            )
            accumulated.append((pipeline.name, last_text))
            # Atualiza manifestos locais para a próxima iteração.
            phase_manifests = _load_phase_manifests(state)
            await runner.close()

            if flags.token_usage_persist():
                # Checkpoint do consumo por workflow: sobrevive a queda/interrupção.
                yield self._make_state_event({
                    "accumulated_outputs": accumulated,
                    "phase_manifests": state.get("phase_manifests", []),
                    **self._usage_delta(state, usage, status="em andamento"),
                })

        logger.info(
            "[ORCHESTRATOR] Fresh run concluído: %d/%d pipelines (session=%s)",
            len(accumulated),
            len(self._pipelines),
            outer_sid,
        )
        state["accumulated_outputs"] = accumulated
        delta = self._usage_delta(state, usage, status="concluída")
        yield self._make_text_event(
            self.name,
            self._report(state, usage),
            state_delta={
                "accumulated_outputs": accumulated,
                "paused_pipeline": None,
                "paused_inner_session_id": None,
                "paused_function_call": None,
                "phase_manifests": state.get("phase_manifests", []),
                **delta,
            },
        )

    # ──────────────────────────────────────────────────────────────────────
    # Helpers de contagem de tokens
    # ──────────────────────────────────────────────────────────────────────

    def _pause_text(
        self, state: dict[str, Any], usage: TokenUsage, pipeline_name: str
    ) -> str:
        """Tabela parcial na pausa (AI4ES_TOKEN_REPORT_ON_PAUSE); vazia se desligada."""
        if not flags.token_report_on_pause():
            return ""
        label = _stage_label(pipeline_name)
        return self._report(state, usage, note=f"Execução pausada em **{label}**.")

    def _setup_usage(
        self,
        state: dict[str, Any],
        outer_sid: str,
        usage: TokenUsage,
        *,
        new_run: bool,
    ) -> None:
        if flags.token_session_total() and new_run:
            runs = state.get("token_usage_runs") or []
            state["token_usage_run"] = len(runs) + 1
        if flags.token_usage_persist():
            usage.persist_path = get_workspace_root() / TOKEN_SNAPSHOT_FILENAME
            usage.persist_meta = {
                "session_id": outer_sid,
                "run": state.get("token_usage_run"),
                "status": "em andamento",
                "previous_runs": [
                    r for r in state.get("token_usage_runs") or []
                    if r.get("run") != state.get("token_usage_run")
                ],
            }

    def _usage_delta(
        self, state: dict[str, Any], usage: TokenUsage, *, status: str
    ) -> dict[str, Any]:
        """Grava o consumo no state e devolve as chaves para o state_delta."""
        state["token_usage"] = usage.to_dict()
        delta: dict[str, Any] = {"token_usage": state["token_usage"]}
        if (
            flags.token_usage_persist()
            or flags.token_report_detail()
            or flags.token_session_total()
        ):
            state["token_usage_agents"] = usage.agents_dict()
            delta["token_usage_agents"] = state["token_usage_agents"]
        if flags.token_session_total():
            run = state.get("token_usage_run") or 1
            entry = {
                "run": run,
                "status": status,
                "workflows": usage.to_dict(),
                "agents": usage.agents_dict(),
            }
            runs = [r for r in state.get("token_usage_runs") or [] if r.get("run") != run]
            runs.append(entry)
            runs.sort(key=lambda r: r.get("run", 0))
            state["token_usage_runs"] = runs
            delta["token_usage_runs"] = runs
            delta["token_usage_run"] = run
        if usage.persist_path is not None:
            usage.persist_meta["status"] = status
            usage.write_snapshot()
        return delta

    def _report(
        self, state: dict[str, Any], usage: TokenUsage, note: Optional[str] = None
    ) -> str:
        session_total = None
        runs = state.get("token_usage_runs") or []
        if flags.token_session_total() and runs:
            session_total = TokenUsage()
            for r in runs:
                session_total.merge(
                    TokenUsage.from_dict(r.get("workflows"), r.get("agents"))
                )
        return usage.format_report(
            note,
            detail=flags.token_report_detail(),
            session_total=session_total,
            session_runs=len(runs),
        )

    @staticmethod
    def _make_text_event(
        author: str,
        text: str,
        state_delta: dict[str, Any] | None = None,
    ) -> Event:
        actions = (
            EventActions(state_delta=state_delta) if state_delta else EventActions()
        )
        return Event(
            author=author,
            invocation_id="orchestrator-error",
            content=types.Content(role="model", parts=[types.Part(text=text)]),
            actions=actions,
        )

    def _make_state_event(self, state_delta: dict[str, Any]) -> Event:
        """Evento sem conteúdo, carrega apenas state_delta para persistência."""
        return Event(
            author=self.name,
            invocation_id="orchestrator-state",
            actions=EventActions(state_delta=state_delta),
        )


root_agent = _PipelineOrchestrator(
    name="orchestrator",
    description=(
        "Orchestrator SDLC v5 — executa requirements → design → coding+review → qa "
        "em sessões isoladas com HITL real no qa_pipeline. Sem MALFORMED_FUNCTION_CALL "
        "(sem LLM no topo) e sem token overflow (sessões dedicadas)."
    ),
)
