"""Workflow coding: CodingOrchestrator — pipeline SDLC com sessões isoladas.

Substitui o antigo SequentialAgent por um BaseAgent custom que segue o
padrão do _PipelineOrchestrator (orchestrator/agent.py):
- Cada etapa roda em Runner isolado com InMemorySessionService.
- Output de cada etapa é injetado no contexto da próxima.
- Retry automático (1x) quando o LLM retorna resposta vazia.
"""

from typing import AsyncGenerator, ClassVar, List

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import ConfigDict

from src.agents.requirements.agent import agent as requirements_agent
from src.agents.context_engineer.agent import agent as context_engineer_agent
from src.agents.architect.agent import agent as architecture_agent
from src.agents.test_planner.agent import agent as test_planning_agent
from src.agents.coder.agent import agent as implementation_agent
from src.agents.reviewer.agent import agent as review_agent
from src.agents.qa_agent.agent import agent as qa_agent
from src.agents.cicd_agent.agent import agent as cicd_agent
from src.agents.finalizer.agent import agent as finalization_agent

from src.agents.orchestrator._helpers import (
    _build_input,
    _extract_user_text,
    _is_empty_response,
    EMPTY_RETRY_PROMPT,
)


class CodingOrchestrator(BaseAgent):
    """Orquestra os agentes individuais do SDLC em sessões isoladas.

    Percorre cada etapa definida em ``_stages``, criando um Runner
    dedicado (com ``InMemorySessionService``) para cada uma. O output
    textual de cada etapa é acumulado e injetado no contexto da etapa
    seguinte via ``_build_input``.

    Se uma etapa devolver resposta vazia, faz **1 retry** com prompt
    explícito antes de registrar falha e avançar.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Lista de agentes na ordem de execução.
    # ClassVar para que Pydantic não tente serializar.
    _stages: ClassVar[List[BaseAgent]] = [
        requirements_agent,
        context_engineer_agent,
        architecture_agent,        
        test_planning_agent,      
        implementation_agent,
        cicd_agent,
        review_agent,             
        qa_agent,                 
        finalization_agent,
    ]

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Executa as etapas SDLC em sequência com isolamento de sessão."""
        user_text = _extract_user_text(ctx)
        if not user_text:
            return

        accumulated: list[tuple[str, str]] = []

        for stage in self._stages:
            stage_input = _build_input(user_text, accumulated)
            content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=stage_input)],
            )

            runner = Runner(
                app_name=stage.name,
                agent=stage,
                artifact_service=ctx.artifact_service,
                session_service=InMemorySessionService(),
                memory_service=InMemoryMemoryService(),
                credential_service=ctx.credential_service,
                plugins=ctx.plugin_manager.plugins if ctx.plugin_manager else None,
            )
            inner_session = await runner.session_service.create_session(
                app_name=stage.name, user_id=ctx.user_id, state={},
            )

            last_text = ""
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

            # RETRY: resposta vazia → reinvoca 1x com prompt de retry.
            if _is_empty_response(last_text):
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

                if _is_empty_response(last_text):
                    last_text = (
                        f"[CodingOrchestrator] etapa {stage.name} "
                        "retornou empty após retry"
                    )

            accumulated.append((stage.name, last_text))
            await runner.close()

    @staticmethod
    def _make_text_event(author: str, text: str) -> Event:
        """Cria evento textual simples (debug/erro)."""
        return Event(
            author=author,
            invocation_id="coding-orchestrator",
            content=types.Content(role="model", parts=[types.Part(text=text)]),
            actions=EventActions(),
        )


# Instância pública — standalone ou plugável no orchestrator principal.
agent = CodingOrchestrator(
    name="sdlc_pipeline",
    description=(
        "Pipeline SDLC completo com sessões isoladas e retry: "
        "requisitos → contexto → arquitetura → plano de testes → implementação → "
        "CI/CD → revisão → QA → finalização."
    ),
)

# ADK CLI busca por `root_agent` ao carregar um app diretamente.
root_agent = agent
