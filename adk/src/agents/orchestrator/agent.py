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

Estado em memória do processo (NÃO persistido — limitação documentada):
    _live_runners: dict[outer_session_id, tuple[Runner, inner_session_id]]
"""

from typing import Any, AsyncGenerator, ClassVar, Dict, List, Tuple

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

from src.agents.orchestrator._helpers import (
    _build_function_response_payload,
    _build_input,
    _clear_pause_state,
    _extract_user_text,
    _is_empty_response,
    _is_pending_long_running_call,
    _parse_decision,
    _set_pause_state,
    EMPTY_RETRY_PROMPT,
)


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

        paused = state.get("paused_pipeline")

        # === Branch RESUME ===
        if paused:
            async for ev in self._handle_resume(ctx, outer_sid, user_text):
                yield ev
            return

        # === Branch FRESH RUN ===
        async for ev in self._handle_fresh_run(ctx, outer_sid, user_text):
            yield ev

    async def _handle_resume(
        self, ctx: InvocationContext, outer_sid: str, user_text: str
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
            yield self._make_state_event({
                "paused_pipeline": state["paused_pipeline"],
                "paused_inner_session_id": state["paused_inner_session_id"],
                "paused_function_call": state["paused_function_call"],
            })
            return

        # Conclusão: cleanup.
        _clear_pause_state(state)
        accumulated = state.get("accumulated_outputs", []) or []
        accumulated.append((paused, last_text))
        state["accumulated_outputs"] = accumulated
        await runner.close()
        self._live_runners.pop(outer_sid, None)
        yield self._make_state_event({
            "paused_pipeline": None,
            "paused_inner_session_id": None,
            "paused_function_call": None,
            "accumulated_outputs": accumulated,
        })

    async def _handle_fresh_run(
        self, ctx: InvocationContext, outer_sid: str, user_text: str
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        # Fresh run reseta accumulated (nova conversa SDLC).
        state["accumulated_outputs"] = []
        accumulated: list[tuple[str, str]] = []

        # Se houver _live_runner legado em outer_sid (sessão zombie), fecha.
        legacy = self._live_runners.pop(outer_sid, None)
        if legacy is not None:
            await legacy[0].close()

        for pipeline in self._pipelines:
            pipeline_input = _build_input(user_text, accumulated)
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
                plugins=ctx.plugin_manager.plugins if ctx.plugin_manager else None,
            )
            inner_session = await runner.session_service.create_session(
                app_name=pipeline.name, user_id=ctx.user_id, state={},
            )

            last_text = ""
            pending_pause = None
            async for event in runner.run_async(
                user_id=inner_session.user_id,
                session_id=inner_session.id,
                new_message=content,
            ):
                yield event
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

            if pending_pause is not None:
                # Salva estado, MANTÉM runner vivo (não fecha).
                self._live_runners[outer_sid] = (runner, inner_session.id)
                _set_pause_state(
                    state,
                    pipeline_name=pipeline.name,
                    inner_session_id=inner_session.id,
                    function_call_id=pending_pause.id,
                    function_call_name=pending_pause.name,
                    function_call_args=dict(pending_pause.args or {}),
                )
                state["accumulated_outputs"] = accumulated
                yield self._make_state_event({
                    "paused_pipeline": state["paused_pipeline"],
                    "paused_inner_session_id": state["paused_inner_session_id"],
                    "paused_function_call": state["paused_function_call"],
                    "accumulated_outputs": accumulated,
                })
                return  # NÃO roda pipelines subsequentes

            # Pipeline concluiu sem pausa.
            accumulated.append((pipeline.name, last_text))
            await runner.close()

        state["accumulated_outputs"] = accumulated
        yield self._make_state_event({
            "accumulated_outputs": accumulated,
            "paused_pipeline": None,
            "paused_inner_session_id": None,
            "paused_function_call": None,
        })

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
