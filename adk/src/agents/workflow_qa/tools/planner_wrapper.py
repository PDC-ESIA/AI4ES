"""Wrapper de retry para invocações do action_planner no qa_pipeline.

Motivação: action_planner via AgentTool retorna ocasionalmente {"result": ""},
travando o qa_pipeline em HITL falso. Este wrapper roda o action_planner em
runner isolado, faz retry programático em caso de empty, e garante que o
caller (qa_pipeline) sempre receba JSON estruturado.
"""

from typing import Optional

from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.genai import types

from src.agents.qa_agent.subagents.action_planner.agent import agent as action_planner_agent


_EMPTY_THRESHOLD = 8


_FALLBACK_BLOCKED_JSON = (
    '{"tipo_entrada":"indefinido","modo":"indefinido","tools":[],'
    '"casos_de_teste_propostos":[],"lifecycle":{"status":"bloqueado",'
    '"execution_allowed":false,"next_step":"aguardar_resolucao_humana"},'
    '"erro":"action_planner não respondeu após 2 tentativas — falha de modelo"}'
)


def _is_empty(text: Optional[str]) -> bool:
    """True quando o texto é vazio, None, só whitespace ou só backticks.

    Heurística: <_EMPTY_THRESHOLD chars úteis = empty.
    """
    if text is None:
        return True
    stripped = text.strip().strip("`").strip()
    return len(stripped) < _EMPTY_THRESHOLD


async def _invoke_once(request: str, user_id: str = "qa-pipeline") -> str:
    """Roda action_planner uma vez em runner isolado, retorna last_text.

    Em caso de exceção do Runner, devolve string 'ERROR: <msg>' em vez de
    propagar — para que invocar_planejamento_qa possa decidir fallback.
    """
    try:
        runner = Runner(
            app_name=action_planner_agent.name,
            agent=action_planner_agent,
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        session = await runner.session_service.create_session(
            app_name=action_planner_agent.name, user_id=user_id, state={},
        )
        content = types.Content(
            role="user", parts=[types.Part.from_text(text=request)],
        )
        last_text = ""
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        last_text = part.text
        await runner.close()
        return last_text
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"
