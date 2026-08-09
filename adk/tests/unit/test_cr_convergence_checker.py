"""Testes para o cr_convergence_checker do workflow_coding_review.

Cobre o núcleo determinístico do early-stopping (sem LLM):
- drift-guard: `_STAGE_ORDER` local == enum canônico `StageName`;
- `hash_src`: determinístico, ignora __pycache__/.pyc, sensível a conteúdo;
- `calcular_score` / `calcular_assinatura`: métricas de progresso;
- `decidir`: regras S0..S3 e reset de paciência por progresso;
- `avaliar`: leitura do state com fail-safe;
- adapter ADK: `ConvergenceChecker` emite escalate corretamente via Runner;
- MECANISMO resgatado: AgentTool propaga state_delta do sub-agente pro parent
  (dependência crítica de todos os callbacks determinísticos do fluxo).
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

from src.agents.workflow_coding_review import cr_convergence_checker as cc


# ===========================================================================
# Drift-guard: a tupla local reflete fielmente o enum canônico do executor
# ===========================================================================


def test_stage_order_reflete_stage_name_canonico():
    """`_STAGE_ORDER` é uma cópia local (independência em runtime), mas precisa
    permanecer idêntica ao enum `StageName` do executor — este teste é o único
    acoplamento, e serve de alarme se o enum canônico mudar."""
    from src.agents.executor.schemas import StageName

    assert cc._STAGE_ORDER == tuple(s.value for s in StageName)


# ===========================================================================
# hash_src — determinístico, ignora ruído, sensível a conteúdo
# ===========================================================================


def _escrever(base, rel, conteudo):
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(conteudo, encoding="utf-8")
    return p


def test_hash_src_deterministico_e_estavel(tmp_path):
    src = tmp_path / "src"
    _escrever(src, "main.py", "print('a')\n")
    _escrever(src, "pkg/util.py", "x = 1\n")
    assert cc.hash_src(src) == cc.hash_src(src)


def test_hash_src_muda_com_conteudo(tmp_path):
    src = tmp_path / "src"
    _escrever(src, "main.py", "print('a')\n")
    h1 = cc.hash_src(src)
    _escrever(src, "main.py", "print('b')\n")
    assert cc.hash_src(src) != h1


def test_hash_src_ignora_pycache_e_pyc(tmp_path):
    src = tmp_path / "src"
    _escrever(src, "main.py", "print('a')\n")
    h1 = cc.hash_src(src)
    _escrever(src, "__pycache__/main.cpython-314.pyc", "lixo binário")
    _escrever(src, "pkg/mod.pyc", "outro lixo")
    assert cc.hash_src(src) == h1


def test_hash_src_diretorio_inexistente_e_constante(tmp_path):
    ausente = tmp_path / "nao_existe"
    vazio = tmp_path / "vazio"
    vazio.mkdir()
    assert cc.hash_src(ausente) == cc.hash_src(vazio)


# ===========================================================================
# Score e assinatura
# ===========================================================================


def _report(stages):
    return {"stages": [{"stage": s, "status": st} for s, st in stages]}


def _validation(status, criterios):
    return {
        "status": status,
        "criteria_verdicts": [
            {"criterion": c, "status": s} for c, s in criterios
        ],
    }


def test_deepest_stage_pega_maior_indice_sucesso():
    rep = _report(
        [
            ("preparacao_ambiente", "sucesso"),
            ("implantacao_artefato", "sucesso"),
            ("inicializacao_aplicacao", "falha"),
        ]
    )
    # implantacao_artefato = índice 1
    assert cc._deepest_stage(rep) == 1


def test_deepest_stage_sem_sucesso_e_menos_um():
    assert cc._deepest_stage(_report([("preparacao_ambiente", "falha")])) == -1
    assert cc._deepest_stage({}) == -1


def test_unmet_conta_nao_atendido_e_inconclusivo():
    val = _validation(
        "reprovado",
        [("c1", "atendido"), ("c2", "nao_atendido"), ("c3", "inconclusivo")],
    )
    assert cc._unmet(val) == 2


def test_score_e_lexicografico():
    # mais fundo no pipeline vence, independentemente de unmet
    raso = cc.calcular_score(
        _validation("reprovado", []), _report([("preparacao_ambiente", "sucesso")])
    )
    fundo = cc.calcular_score(
        _validation("reprovado", [("c", "nao_atendido")]),
        _report(
            [("preparacao_ambiente", "sucesso"), ("testes_automatizados", "sucesso")]
        ),
    )
    assert fundo > raso
    # mesmo estágio: menos unmet vence
    a = cc.calcular_score(
        _validation("reprovado", [("c1", "nao_atendido"), ("c2", "inconclusivo")]),
        _report([("preparacao_ambiente", "sucesso")]),
    )
    b = cc.calcular_score(
        _validation("reprovado", [("c1", "nao_atendido")]),
        _report([("preparacao_ambiente", "sucesso")]),
    )
    assert b > a


def test_assinatura_ordena_criterios_e_codigos():
    val = {
        "blocking_reason": "motivo X",
        "criteria_verdicts": [
            {"criterion": "z", "status": "nao_atendido"},
            {"criterion": "a", "status": "inconclusivo"},
            {"criterion": "ok", "status": "atendido"},
        ],
    }
    rep = {
        "stages": [
            {"stage": "s1", "status": "falha", "error_code": "ERR_B"},
            {"stage": "s2", "status": "erro", "error_code": "ERR_A"},
            {"stage": "s3", "status": "sucesso", "error_code": None},
        ]
    }
    assert cc.calcular_assinatura(val, rep) == (
        "motivo X",
        ("a", "z"),
        ("ERR_A", "ERR_B"),
    )


# ===========================================================================
# decidir — regras de parada S0..S3
# ===========================================================================

_KW = dict(patience=3, ceiling=300)


def test_s0_aprovado_para_imediatamente():
    d = cc.decidir(
        {}, status="aprovado", score=(8, 0), assinatura=(None, (), ()), src_hash="h1", **_KW
    )
    assert d.parar is True and d.motivo == "S0_aprovado"


def test_s1_estagnacao_dura_src_hash_repetido():
    prev = {"iteration": 1, "best_score": [1, -1], "last_src_hash": "SAME", "sem_progresso": 0}
    d = cc.decidir(
        prev, status="reprovado", score=(1, -1), assinatura=(None, (), ()), src_hash="SAME", **_KW
    )
    assert d.parar is True and d.motivo == "S1_estagnacao_dura"


def test_s1_nao_dispara_na_primeira_iteracao():
    # sem last_src_hash anterior não há como comparar → não é estagnação
    d = cc.decidir(
        {}, status="reprovado", score=(0, -1), assinatura=(None, (), ()), src_hash="h1", **_KW
    )
    assert d.parar is False and d.motivo == "continua"


def test_s2_sem_progresso_atinge_paciencia():
    # score nunca melhora e o src muda a cada volta (não é S1)
    prev = {}
    hashes = ["h1", "h2", "h3", "h4"]
    motivos = []
    for i, hsh in enumerate(hashes):
        d = cc.decidir(
            prev,
            status="reprovado",
            score=(0, -2),  # constante → sem progresso após a 1ª
            assinatura=(None, (), ()),
            src_hash=hsh,
            **_KW,
        )
        prev = d.novo_estado
        motivos.append(d.motivo)
    # 1ª: progresso (best None→setado); 2ª,3ª: sem_progresso 1,2; 4ª: atinge 3
    assert motivos[-1] == "S2_sem_progresso"
    assert d.parar is True


def test_progresso_reseta_paciencia():
    prev = {"iteration": 2, "best_score": [0, -3], "last_src_hash": "h1", "sem_progresso": 2}
    # score MELHOROU (deepest sobe) → reset e continua
    d = cc.decidir(
        prev, status="reprovado", score=(1, -3), assinatura=(None, (), ()), src_hash="h2", **_KW
    )
    assert d.parar is False
    assert d.novo_estado["sem_progresso"] == 0
    assert d.novo_estado["best_score"] == [1, -3]


def test_s3_teto_encerra():
    prev = {"iteration": 4, "best_score": [9, 0], "last_src_hash": "h1", "sem_progresso": 0}
    d = cc.decidir(
        prev,
        status="reprovado",
        score=(9, 0),  # empata com best → sem progresso, mas paciência alta
        assinatura=(None, (), ()),
        src_hash="h2",
        patience=100,
        ceiling=5,
    )
    assert d.parar is True and d.motivo == "S3_teto"


def test_ordem_de_prioridade_s0_vence_s1():
    # src repetido (S1) mas veredito aprovado (S0) → aprovação vence
    prev = {"iteration": 1, "best_score": [1, 0], "last_src_hash": "SAME", "sem_progresso": 0}
    d = cc.decidir(
        prev, status="aprovado", score=(9, 0), assinatura=(None, (), ()), src_hash="SAME", **_KW
    )
    assert d.motivo == "S0_aprovado"


# ===========================================================================
# avaliar — leitura do state + fail-safe
# ===========================================================================


def test_avaliar_status_desconhecido_nunca_aprova(monkeypatch, tmp_path):
    monkeypatch.setattr(cc, "get_agent_workspace", lambda _: tmp_path / "src")
    state = {"validation": {"status": "???", "criteria_verdicts": []}}
    d = cc.avaliar(state)
    assert d.novo_estado["last_status"] == "reprovado"
    assert d.motivo != "S0_aprovado"


def test_avaliar_report_ilegivel_degrada_para_vazio(monkeypatch, tmp_path):
    monkeypatch.setattr(cc, "get_agent_workspace", lambda _: tmp_path / "src")
    state = {
        "validation": {"status": "reprovado", "criteria_verdicts": []},
        "report_path": str(tmp_path / "TASK-1.report.json"),  # não existe
        "task_id": "TASK-1",
    }
    d = cc.avaliar(state)
    # sem report → deepest_stage -1
    assert d.novo_estado["last_score"][0] == -1


def test_avaliar_report_nome_inesperado_e_ignorado(monkeypatch, tmp_path):
    monkeypatch.setattr(cc, "get_agent_workspace", lambda _: tmp_path / "src")
    outro = tmp_path / "OUTRO.report.json"
    outro.write_text(json.dumps(_report([("preparacao_ambiente", "sucesso")])), encoding="utf-8")
    state = {
        "validation": {"status": "reprovado", "criteria_verdicts": []},
        "report_path": str(outro),
        "task_id": "TASK-1",  # nome não bate → ignora
    }
    d = cc.avaliar(state)
    assert d.novo_estado["last_score"][0] == -1


def test_avaliar_aprovado_para(monkeypatch, tmp_path):
    monkeypatch.setattr(cc, "get_agent_workspace", lambda _: tmp_path / "src")
    rep = tmp_path / "TASK-1.report.json"
    rep.write_text(
        json.dumps(_report([("preparacao_ambiente", "sucesso")])), encoding="utf-8"
    )
    state = {
        "validation": {"status": "aprovado", "criteria_verdicts": []},
        "report_path": str(rep),
        "task_id": "TASK-1",
    }
    d = cc.avaliar(state)
    assert d.parar is True and d.motivo == "S0_aprovado"


# ===========================================================================
# Adapter ADK — ConvergenceChecker emite escalate via Runner
# ===========================================================================


async def _rodar_checker(state):
    runner = Runner(
        app_name="test_cc",
        agent=cc.ConvergenceChecker(name="cr_convergence_checker"),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )
    session = await runner.session_service.create_session(
        app_name="test_cc", user_id="u", state=state
    )
    eventos = []
    content = types.Content(role="user", parts=[types.Part(text="go")])
    async for ev in runner.run_async(
        user_id=session.user_id, session_id=session.id, new_message=content
    ):
        eventos.append(ev)
    return eventos


async def test_checker_escala_quando_aprovado(monkeypatch, tmp_path):
    monkeypatch.setattr(cc, "get_agent_workspace", lambda _: tmp_path / "src")
    eventos = await _rodar_checker(
        {"validation": {"status": "aprovado", "criteria_verdicts": []}}
    )
    escalou = any(e.actions and e.actions.escalate for e in eventos)
    assert escalou is True


async def test_checker_nao_escala_reprovado_na_primeira(monkeypatch, tmp_path):
    monkeypatch.setattr(cc, "get_agent_workspace", lambda _: tmp_path / "src")
    eventos = await _rodar_checker(
        {"validation": {"status": "reprovado", "criteria_verdicts": [{"criterion": "c", "status": "nao_atendido"}]}}
    )
    escalou = any(e.actions and e.actions.escalate for e in eventos)
    assert escalou is False
    # e persistiu o bookkeeping de convergência
    persistiu = any(
        e.actions and e.actions.state_delta and cc._CONV_STATE_KEY in e.actions.state_delta
        for e in eventos
    )
    assert persistiu is True


# ===========================================================================
# MECANISMO ADK (resgatado de test_cr_executor_correction_spec.py):
# AgentTool propaga event.actions.state_delta do sub-agente pro parent.
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


async def test_agent_tool_propaga_state_delta_pro_parent():
    """Confirma empiricamente o mecanismo do qual TODOS os callbacks
    determinísticos do fluxo dependem: o after_agent_callback do
    implementation_validator escreve callback_context.state['validation'], e isso
    precisa chegar ao tool_context do agente pai (executor). Sem essa propagação,
    nem o ErrorReport do executor nem o veredito lido pelo convergence_checker
    teriam como funcionar."""
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
