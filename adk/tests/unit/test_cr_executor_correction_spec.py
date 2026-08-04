"""Tests para o ErrorReport — feedback estruturado do executor pro coder.

Cobre:
- O MECANISMO da ADK (AgentTool propaga state_delta do sub-agente pro
  tool_context do agente pai) — testado com Runner real e BaseAgent fake.
- A lógica de `montar_error_report` (after_agent_callback do cr_executor):
  quando retorna None, quando monta ErrorReport, filtragem de critérios
  atendidos, e persistência no state.
"""

import json

import pytest
from google.adk.agents import BaseAgent
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from src.agents.workflow_coding_review.cr_executor import montar_error_report


# ===========================================================================
# Mecanismo ADK: AgentTool propaga state_delta pro parent
# ===========================================================================


class _FakeValidatorAgent(BaseAgent):
    """Sub-agente sem LLM que só emite um state_delta, como o after_agent_callback
    real do implementation_validator faria."""

    async def _run_async_impl(self, ctx):
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            content=types.Content(
                role="model",
                parts=[types.Part(text='{"status": "reprovado"}')],
            ),
            actions=EventActions(
                state_delta={
                    "validation": {"status": "reprovado", "marker": "propagated"}
                }
            ),
        )


class _ParentProbeAgent(BaseAgent):
    """Chama o AgentTool diretamente e guarda o que sobrou no tool_context.state."""

    captured: dict = {}

    async def _run_async_impl(self, ctx):
        tool = AgentTool(agent=_FakeValidatorAgent(name="fake_validator"))
        tool_context = ToolContext(invocation_context=ctx)
        await tool.run_async(
            args={"request": "validar TASK-001"}, tool_context=tool_context
        )
        self.captured["validation"] = tool_context.state.get("validation")
        yield Event(author=self.name, invocation_id=ctx.invocation_id)


@pytest.mark.asyncio
async def test_agent_tool_propaga_state_delta_pro_parent():
    """Confirma empiricamente o mecanismo do qual o callback depende: o
    after_agent_callback do implementation_validator escreve
    callback_context.state["validation"], e isso precisa chegar no
    tool_context do cr_executor_agent."""
    parent = _ParentProbeAgent(name="parent_probe")
    runner = Runner(
        app_name="test_app",
        agent=parent,
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )
    session = await runner.session_service.create_session(
        app_name="test_app", user_id="u", state={}
    )
    content = types.Content(role="user", parts=[types.Part(text="oi")])
    async for _ in runner.run_async(
        user_id=session.user_id, session_id=session.id, new_message=content
    ):
        pass

    assert parent.captured.get("validation") == {
        "status": "reprovado",
        "marker": "propagated",
    }


# ===========================================================================
# montar_error_report — lógica pura (callback_context fake, sem Runner/LLM)
# ===========================================================================


class _FakeCallbackContext:
    def __init__(self, state: dict):
        self.state = state


def _validation_reprovado(criteria_verdicts, work_item_id="TASK-001"):
    return {
        "work_item_id": work_item_id,
        "status": "reprovado",
        "blocking_reason": "Ao menos um critério ficou nao_atendido ou inconclusivo.",
        "criteria_verdicts": criteria_verdicts,
    }


def test_validation_ausente_retorna_none():
    """Sem state['validation'], montar_error_report degrada para None."""
    ctx = _FakeCallbackContext({})
    assert montar_error_report(ctx) is None


def test_veredito_aprovado_retorna_none():
    """Veredito 'aprovado' não gera ErrorReport."""
    validation = {
        "work_item_id": "TASK-001",
        "status": "aprovado",
        "blocking_reason": None,
        "criteria_verdicts": [],
    }
    ctx = _FakeCallbackContext({"validation": validation})
    assert montar_error_report(ctx) is None
    assert "error_report" not in ctx.state


def test_estagnacao_retorna_none():
    """Turno de estagnação (contém 'STATUS: bloqueado') não é sobrescrito."""
    validation = _validation_reprovado([])
    ctx = _FakeCallbackContext({
        "validation": validation,
        "execution_result": "STATUS: bloqueado — coder não fez alterações.",
    })
    assert montar_error_report(ctx) is None


def test_reprovado_monta_error_report():
    """Veredito reprovado com critérios gera ErrorReport no state."""
    validation = _validation_reprovado([
        {
            "criterion": "Persistir usuário no banco",
            "status": "nao_atendido",
            "reasoning": "Model User não tem campo obrigatório.",
            "evidence_ref": "estagio testes_automatizados",
        },
    ])
    ctx = _FakeCallbackContext({"validation": validation})

    content = montar_error_report(ctx)
    assert content is not None

    report = json.loads(content.parts[0].text)
    assert report["work_item_id"] == "TASK-001"
    assert report["verdict_status"] == "reprovado"
    assert len(report["failed_criteria"]) == 1
    assert report["failed_criteria"][0]["criterion"] == "Persistir usuário no banco"

    # Também persiste no state
    assert "error_report" in ctx.state
    assert ctx.state["error_report"]["work_item_id"] == "TASK-001"


def test_criterio_atendido_nao_aparece_no_report():
    """Critérios com status 'atendido' são filtrados do ErrorReport."""
    validation = _validation_reprovado([
        {
            "criterion": "Critério OK",
            "status": "atendido",
            "reasoning": "ok",
            "evidence_ref": None,
        },
        {
            "criterion": "Critério falho",
            "status": "nao_atendido",
            "reasoning": "falhou",
            "evidence_ref": None,
        },
    ])
    ctx = _FakeCallbackContext({"validation": validation})

    content = montar_error_report(ctx)
    report = json.loads(content.parts[0].text)
    criterios = [c["criterion"] for c in report["failed_criteria"]]
    assert "Critério OK" not in criterios
    assert "Critério falho" in criterios


def test_work_item_id_fallback_para_desconhecido():
    """Sem work_item_id no validation nem exec_report, usa 'desconhecido'."""
    validation = {
        "status": "reprovado",
        "blocking_reason": "falha",
        "criteria_verdicts": [],
    }
    ctx = _FakeCallbackContext({"validation": validation})

    content = montar_error_report(ctx)
    report = json.loads(content.parts[0].text)
    assert report["work_item_id"] == "desconhecido"
