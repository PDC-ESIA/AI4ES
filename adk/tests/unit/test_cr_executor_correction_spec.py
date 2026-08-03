"""Tests para o CorrectionSpec — feedback estruturado do executor pro coder.

Cobre duas coisas distintas:
- O MECANISMO da ADK que o callback depende (AgentTool propaga
  event.actions.state_delta do sub-agente pro tool_context do agente pai) —
  testado com um Runner real e um BaseAgent fake, sem LLM.
- A lógica pura de parse + validação cruzada em
  `cr_executor_correction.parse_e_montar_correction_spec`, testada com um
  callback_context fake (mesmo estilo de test_review_agent_persistence.py),
  sem Runner nem LLM.
"""

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

from src.agents.workflow_coding_review.cr_executor import parse_e_montar_correction_spec


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
    tool_context do cr_executor_agent — sem essa propagação, a validação
    cruzada da CorrectionSpec não teria como funcionar."""
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
# Parse + validação cruzada (sem Runner, callback_context fake)
# ===========================================================================


class _FakeCallbackContext:
    def __init__(self, state: dict):
        self.state = state


_MARKDOWN_DOIS_CRITERIOS = """BLOCKING_REASON: Ao menos um critério ficou nao_atendido ou inconclusivo.

### CORRECAO
CRITERIO: Persistir usuário no banco
CAUSA_RAIZ: Model User não tem ForeignKey para Ensaio.
ARQUIVOS_AFETADOS: app/models.py
MUDANCA_REQUERIDA: Adicionar ForeignKey("ensaios.id") em User.ensaio_id.
EVIDENCIA_REF: estagio inicializacao_aplicacao

### CORRECAO
CRITERIO: GET /health deve retornar status 200
CAUSA_RAIZ: Rota /health não implementada.
ARQUIVOS_AFETADOS: app/main.py
MUDANCA_REQUERIDA: Adicionar endpoint GET /health.
EVIDENCIA_REF: -
"""


def _validation_reprovado(criteria_verdicts):
    return {
        "work_item_id": "TASK-001",
        "status": "reprovado",
        "blocking_reason": "Ao menos um critério ficou nao_atendido ou inconclusivo.",
        "criteria_verdicts": criteria_verdicts,
    }


def test_caminho_feliz_cross_valida_e_monta_spec():
    validation = _validation_reprovado(
        [
            {
                "criterion": "Persistir usuário no banco",
                "status": "nao_atendido",
                "reasoning": "x",
                "evidence_ref": "real-ref-1",
            },
            {
                "criterion": "GET /health deve retornar status 200",
                "status": "inconclusivo",
                "reasoning": "y",
                "evidence_ref": None,
            },
        ]
    )
    ctx = _FakeCallbackContext(
        {"execution_result": _MARKDOWN_DOIS_CRITERIOS, "validation": validation}
    )

    content = parse_e_montar_correction_spec(ctx)

    assert content is not None
    import json

    spec = json.loads(content.parts[0].text)
    assert spec["work_item_id"] == "TASK-001"
    assert len(spec["items"]) == 2
    item1 = next(
        i for i in spec["items"] if i["criterion"] == "Persistir usuário no banco"
    )
    assert item1["affected_files"] == ["app/models.py"]
    assert (
        item1["required_change"]
        == 'Adicionar ForeignKey("ensaios.id") em User.ensaio_id.'
    )
    assert item1["evidence_ref"] == "estagio inicializacao_aplicacao"
    item2 = next(
        i
        for i in spec["items"]
        if i["criterion"] == "GET /health deve retornar status 200"
    )
    # EVIDENCIA_REF "-" no bloco → cai pro evidence_ref real (None aqui)
    assert item2["evidence_ref"] is None
    assert ctx.state["correction_spec"] == spec


def test_criterio_reprovado_sem_diagnostico_gera_fallback():
    """Critério nao_atendido no veredito real, mas ausente no markdown do LLM
    → item de fallback sintetizado, nunca some."""
    validation = _validation_reprovado(
        [
            {
                "criterion": "Critério não diagnosticado pelo executor",
                "status": "nao_atendido",
                "reasoning": "x",
                "evidence_ref": "real-ref",
            }
        ]
    )
    ctx = _FakeCallbackContext(
        {
            # markdown só cobre um critério diferente do real
            "execution_result": _MARKDOWN_DOIS_CRITERIOS,
            "validation": validation,
        }
    )

    content = parse_e_montar_correction_spec(ctx)
    assert content is not None
    import json

    spec = json.loads(content.parts[0].text)
    assert len(spec["items"]) == 1
    item = spec["items"][0]
    assert item["criterion"] == "Critério não diagnosticado pelo executor"
    assert "Não diagnosticado" in item["root_cause"]
    assert item["affected_files"] == []
    assert item["evidence_ref"] == "real-ref"


def test_criterio_atendido_nao_gera_item():
    validation = _validation_reprovado(
        [
            {
                "criterion": "Persistir usuário no banco",
                "status": "nao_atendido",
                "reasoning": "x",
                "evidence_ref": None,
            },
            {
                "criterion": "Critério já atendido",
                "status": "atendido",
                "reasoning": "ok",
                "evidence_ref": None,
            },
        ]
    )
    ctx = _FakeCallbackContext(
        {"execution_result": _MARKDOWN_DOIS_CRITERIOS, "validation": validation}
    )

    content = parse_e_montar_correction_spec(ctx)
    import json

    spec = json.loads(content.parts[0].text)
    criterios = [i["criterion"] for i in spec["items"]]
    assert "Critério já atendido" not in criterios


def test_state_validation_ausente_faz_fallback_sem_cross_check():
    ctx = _FakeCallbackContext({"execution_result": _MARKDOWN_DOIS_CRITERIOS})

    content = parse_e_montar_correction_spec(ctx)
    assert content is not None
    import json

    spec = json.loads(content.parts[0].text)
    assert spec["work_item_id"] == "desconhecido"
    assert len(spec["items"]) == 2  # os dois blocos do markdown, sem cross-check
    assert all(i["status"] == "inconclusivo" for i in spec["items"])


def test_veredito_real_aprovado_retorna_none():
    """Mesmo que o LLM tenha (indevidamente) emitido blocos ### CORRECAO, um
    veredito real 'aprovado' não deve gerar CorrectionSpec."""
    validation = {
        "work_item_id": "TASK-001",
        "status": "aprovado",
        "blocking_reason": None,
        "criteria_verdicts": [],
    }
    ctx = _FakeCallbackContext(
        {"execution_result": _MARKDOWN_DOIS_CRITERIOS, "validation": validation}
    )

    assert parse_e_montar_correction_spec(ctx) is None
    assert "correction_spec" not in ctx.state


def test_sem_blocos_correcao_retorna_none():
    """Cobre o caminho de aprovação (texto curto de confirmação) e o de
    ESTAGNAÇÃO (outro formato) — nenhum dos dois tem blocos ### CORRECAO."""
    ctx = _FakeCallbackContext(
        {
            "execution_result": "Aprovado! Resumo: tudo certo.",
            "validation": {"status": "aprovado"},
        }
    )
    assert parse_e_montar_correction_spec(ctx) is None


def test_execution_result_vazio_retorna_none():
    ctx = _FakeCallbackContext({})
    assert parse_e_montar_correction_spec(ctx) is None
