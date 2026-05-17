"""Orchestrator SDLC v3 — Custom BaseAgent com sessões isoladas.

Por que não LlmAgent (v1)?
    Gemini 2.5 Flash emite MALFORMED_FUNCTION_CALL ao orquestrar 9 tools
    com contexto multi-turno. Pode até retornar 0 candidate tokens.

Por que não SequentialAgent (v2)?
    SequentialAgent passa a MESMA InvocationContext (e session) para todos
    os sub_agents. Após 2-3 sub-pipelines pesadas, o histórico ultrapassa
    o limite de 1M tokens do Gemini.

Solução (v3):
    BaseAgent custom que invoca cada sub-pipeline via Runner em SESSÃO
    ISOLADA (mesmo padrão de AgentTool — context window dedicado por
    pipeline). Sem LLM no topo → sem MALFORMED. Sem session compartilhada
    → sem overflow.

Sequência fixa:
    requirements_pipeline → design_pipeline → coding_review_pipeline → qa_pipeline

Cada pipeline recebe como input o prompt original + um sumário curto
dos outputs anteriores (último texto de cada sub-pipeline).
"""

from typing import AsyncGenerator, ClassVar, List

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import ConfigDict

from src.agents.workflow_requirements.agent import agent as requirements_pipeline
from src.agents.workflow_design_pipeline.agent import agent as design_pipeline
from src.agents.workflow_coding_review.agent import agent as coding_review_pipeline
from src.agents.workflow_qa.agent import agent as qa_pipeline


class _PipelineOrchestrator(BaseAgent):
    """Roda pipelines em sequência, cada uma em sessão isolada."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Mantemos os pipelines como class variable para evitar o
    # validator de sub_agents que clama parent ownership.
    _pipelines: ClassVar[List[BaseAgent]] = [
        requirements_pipeline,
        design_pipeline,
        coding_review_pipeline,
        qa_pipeline,
    ]

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # Extrai a mensagem inicial do usuário do contexto.
        user_text = ""
        if ctx.user_content and ctx.user_content.parts:
            for part in ctx.user_content.parts:
                if part.text:
                    user_text += part.text + "\n"
        user_text = user_text.strip()
        if not user_text:
            return

        accumulated_outputs: list[str] = []

        for pipeline in self._pipelines:
            # Monta input para esta pipeline: prompt original + sumário
            # curto das pipelines anteriores (apenas o texto final de cada).
            if accumulated_outputs:
                prior_summary = "\n\n".join(
                    f"### Output de {nome}:\n{texto[:8000]}"
                    for nome, texto in accumulated_outputs
                )
                pipeline_input = (
                    f"{user_text}\n\n"
                    f"---\n"
                    f"CONTEXTO DAS FASES ANTERIORES:\n{prior_summary}\n"
                    f"---\n"
                )
            else:
                pipeline_input = user_text

            content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=pipeline_input)],
            )

            # Runner com session/memory isoladas — não polui o context window
            # do próximo pipeline.
            runner = Runner(
                app_name=pipeline.name,
                agent=pipeline,
                artifact_service=ctx.artifact_service,
                session_service=InMemorySessionService(),
                memory_service=InMemoryMemoryService(),
                credential_service=ctx.credential_service,
                plugins=ctx.plugin_manager.plugins if ctx.plugin_manager else None,
            )

            session = await runner.session_service.create_session(
                app_name=pipeline.name,
                user_id=ctx.user_id,
                state={},
            )

            last_text = ""
            try:
                async for event in runner.run_async(
                    user_id=session.user_id,
                    session_id=session.id,
                    new_message=content,
                ):
                    # Forward de eventos para o caller (UI/REST veem o stream).
                    yield event
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                last_text = part.text
            finally:
                await runner.close()

            accumulated_outputs.append((pipeline.name, last_text))


root_agent = _PipelineOrchestrator(
    name="orchestrator",
    description=(
        "Orchestrator SDLC v4 — executa requirements → design → coding+review → qa "
        "em sessões isoladas. Sem MALFORMED_FUNCTION_CALL (sem LLM no topo) "
        "e sem token overflow (sessões dedicadas por pipeline)."
    ),
)
