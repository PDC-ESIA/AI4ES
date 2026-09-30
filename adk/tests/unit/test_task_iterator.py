"""Testes da Fatia 1: iteração determinística e gate de cobertura."""

from __future__ import annotations

from types import SimpleNamespace
from typing import AsyncGenerator

import pytest
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import PrivateAttr

from shared.tools.coding_tools import harness_execucao
from src.agents.workflow_coding_review.executor.loop_policy import CHAVES_DE_CICLO
from src.agents.workflow_coding_review.task_iterator import (
    _CHAVES_CICLO_REMOVIDAS,
    TaskIterator,
    calcular_cobertura,
    classificar_desfecho,
    conceito_da_nota,
    detalhe_erro_operacional,
    validar_envelope_de_tasks,
)


class _StubLoop(BaseAgent):
    """Loop controlável que aprova, reprova ou lança erro por task."""

    _comportamentos: dict[str, str] = PrivateAttr(default_factory=dict)
    _chamadas: list[dict] = PrivateAttr(default_factory=list)

    def configurar(self, comportamentos: dict[str, str]) -> None:
        self._comportamentos = comportamentos

    @property
    def chamadas(self) -> list[dict]:
        return self._chamadas

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        task_id = ctx.session.state["task_id"]
        self._chamadas.append(
            {
                "task_id": task_id,
                "branch": ctx.branch,
                "execution_result": ctx.session.state.get("execution_result"),
            }
        )
        comportamento = self._comportamentos.get(task_id, "aprovado")
        if comportamento == "erro":
            raise RuntimeError("falha operacional de teste")

        ctx.session.state["validation"] = {
            "work_item_id": task_id,
            "status": comportamento,
            "blocking_reason": None if comportamento == "aprovado" else "falhou",
        }
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=task_id)]),
        )


async def _executar_iterator(tasks: object, comportamentos: dict[str, str]):
    loop = _StubLoop(name="stub_loop")
    loop.configurar(comportamentos)
    iterator = TaskIterator(
        name="task_iterator_test",
        sub_agents=[loop],
    )
    session_service = InMemorySessionService()
    runner = Runner(
        agent=iterator,
        app_name="workflow_coding_review",
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name="workflow_coding_review",
        user_id="test-user",
        state={"tasks": tasks},
    )

    eventos = []
    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=types.Content(
            role="user", parts=[types.Part(text="processar tasks")]
        ),
    ):
        eventos.append(event)

    atualizada = await session_service.get_session(
        app_name="workflow_coding_review",
        user_id=session.user_id,
        session_id=session.id,
    )
    assert atualizada is not None
    return loop, eventos, atualizada.state


def test_validar_envelope_rejeita_formas_invalidas():
    casos = [
        (None, "tasks_ausente"),
        ([], "envelope_invalido"),
        ({}, "lista_ausente"),
        ({"tasks": {}}, "lista_tipo_invalido"),
        ({"tasks": []}, "lista_vazia"),
        ({"tasks": [None]}, "task_tipo_invalido"),
        ({"tasks": [{}]}, "id_ausente"),
        ({"tasks": [{"id": 1}]}, "id_tipo_invalido"),
        ({"tasks": [{"id": "../TASK-001"}]}, "id_invalido"),
        (
            {"tasks": [{"id": "TASK-001"}, {"id": "TASK-001"}]},
            "id_duplicado",
        ),
    ]

    for envelope, tipo_esperado in casos:
        tasks, erros = validar_envelope_de_tasks(envelope)
        assert tasks == []
        assert any(erro["type"] == tipo_esperado for erro in erros)


def test_validar_envelope_aceita_ids_com_menos_de_tres_digitos():
    envelope = {
        "tasks": [
            {"id": "TASK-1"},
            {"id": "TASK-02"},
            {"id": "TASK-003"},
        ]
    }
    tasks, erros = validar_envelope_de_tasks(envelope)
    assert erros == []
    assert len(tasks) == 3
    assert [t["id"] for t in tasks] == ["TASK-1", "TASK-02", "TASK-003"]


def test_calcular_cobertura_e_fail_closed():
    ids = ["TASK-001", "TASK-002"]
    assert calcular_cobertura(True, ids, ids, ids) is True
    assert calcular_cobertura(False, ids, ids, ids) is False
    assert calcular_cobertura(True, [], [], []) is False
    assert calcular_cobertura(True, ids, ids, ["TASK-001"]) is False


def test_cobertura_aceita_combinacao_de_aprovadas_e_ressalvas():
    ids = ["TASK-001", "TASK-002"]

    assert calcular_cobertura(
        True, ids, ids, ["TASK-001"], ["TASK-002"]
    ) is True
    assert calcular_cobertura(
        True, ids, ids, ["TASK-001"], ["TASK-001", "TASK-002"]
    ) is False, "uma task não pode estar nas duas categorias"


@pytest.mark.parametrize(
    "nota,conceito",
    [(0.0, "C"), (0.6, "C"), (0.600001, "B"), (0.9, "B"), (0.900001, "A"), (1.0, "A")],
)
def test_conceito_da_nota_respeita_fronteiras(nota, conceito):
    assert conceito_da_nota(nota) == conceito


def test_conceito_sem_nota_permanece_ausente():
    assert conceito_da_nota(None) is None


def test_classificar_desfecho_rejeita_work_item_divergente():
    resultado = classificar_desfecho(
        {
            "validation": {
                "work_item_id": "TASK-999",
                "status": "aprovado",
            }
        },
        "TASK-001",
    )
    assert resultado["status"] == "reprovado"
    assert resultado["motivo_terminacao"] == "validation_ausente_ou_invalida"


def test_classificar_desfecho_detecta_travamento():
    """O travamento vem do campo tipado da política, não mais de texto cru."""
    resultado = classificar_desfecho(
        {
            "validation": {
                "work_item_id": "TASK-001",
                "status": "reprovado",
                "blocking_reason": "sem progresso",
            },
            "loop_stop_reason": "plato_nota",
        },
        "TASK-001",
    )
    assert resultado["status"] == "bloqueado"
    assert resultado["motivo_terminacao"] == "bloqueado_plato_nota"


def test_estagnacao_conceito_b_com_base_executavel_e_aceita(monkeypatch):
    import src.agents.workflow_coding_review.task_iterator as modulo

    monkeypatch.setattr(modulo, "_report_path_valido", lambda *_: True)
    resultado = classificar_desfecho(
        {
            "validation": {
                "work_item_id": "TASK-001",
                "status": "reprovado",
                "blocking_reason": "Ainda há testes falhos.",
            },
            "report_path": "/ws/coder/execution/TASK-001.report.json",
            "loop_stop_reason": "plato_nota",
            "progress_score_history": [0.8, 0.8, 0.8],
            "progress_score_details": [
                {
                    "minimo_para_rodar": 1,
                    "ambiente_preparado": 1,
                    "build_concluido": 1,
                    "app_iniciou": 1,
                    "testes_passaram": 0.5,
                }
            ] * 3,
        },
        "TASK-001",
    )

    assert resultado["status"] == "aceito_com_ressalvas"
    assert resultado["conceito"] == "B"
    assert resultado["nota_final_10"] == 8.0
    assert resultado["motivo_terminacao"] == "aceito_com_ressalvas_plato_nota"


@pytest.mark.parametrize(
    "nota,detalhe",
    [
        (0.6, {"minimo_para_rodar": 1, "ambiente_preparado": 1, "build_concluido": 1, "app_iniciou": 1}),
        (0.8, {"minimo_para_rodar": 1, "ambiente_preparado": 1, "build_concluido": 1, "app_iniciou": 0}),
    ],
)
def test_estagnacao_conceito_c_ou_base_quebrada_continua_bloqueada(
    monkeypatch, nota, detalhe
):
    import src.agents.workflow_coding_review.task_iterator as modulo

    monkeypatch.setattr(modulo, "_report_path_valido", lambda *_: True)
    resultado = classificar_desfecho(
        {
            "validation": {"work_item_id": "TASK-001", "status": "reprovado"},
            "report_path": "/ws/coder/execution/TASK-001.report.json",
            "loop_stop_reason": "plato_nota",
            "progress_score_history": [nota],
            "progress_score_details": [detalhe],
        },
        "TASK-001",
    )

    assert resultado["status"] == "bloqueado"


def test_marcador_de_texto_nao_encerra_mais_a_task():
    """Regressão: `STATUS: bloqueado` na saída do LLM era o gatilho antigo.

    Um executor que ainda escrevesse o marcador (ou um coder que o mencionasse
    por acaso) não pode mais classificar a task como travada — só a política
    decide isso.
    """
    resultado = classificar_desfecho(
        {
            "validation": {
                "work_item_id": "TASK-001",
                "status": "reprovado",
                "blocking_reason": "sem progresso",
            },
            "execution_result": "STATUS: bloqueado\nSem alterações.",
        },
        "TASK-001",
    )
    assert resultado["status"] == "reprovado"
    assert resultado["motivo_terminacao"] == "reprovado_apos_loop"


@pytest.mark.asyncio
async def test_iterator_processa_todas_em_branches_irmas_e_publica_gate():
    loop, eventos, state = await _executar_iterator(
        {"tasks": [{"id": "TASK-001"}, {"id": "TASK-002"}]},
        {"TASK-001": "aprovado", "TASK-002": "aprovado"},
    )

    assert [c["task_id"] for c in loop.chamadas] == ["TASK-001", "TASK-002"]
    assert [c["branch"] for c in loop.chamadas] == [
        "task_iterator.task_0_TASK-001",
        "task_iterator.task_1_TASK-002",
    ]
    assert loop.chamadas[0]["execution_result"] is None
    assert loop.chamadas[1]["execution_result"].startswith("NOVA_TASK:")

    summary = state["task_iteration_summary"]
    assert summary["processed_task_ids"] == ["TASK-001", "TASK-002"]
    assert summary["approved_task_ids"] == ["TASK-001", "TASK-002"]
    assert summary["cobertura_completa"] is True
    assert any(
        event.actions and event.actions.state_delta.get("task_iteration_summary")
        for event in eventos
    )


@pytest.mark.asyncio
async def test_iterator_preserva_total_de_criterios_sem_report():
    _, _, state = await _executar_iterator(
        {
            "tasks": [
                {
                    "id": "TASK-001",
                    "acceptance_criteria": ["Primeiro", "Segundo"],
                }
            ]
        },
        {"TASK-001": "aprovado"},
    )

    resultado = state["task_iteration_summary"]["task_results"]["TASK-001"]
    assert resultado["criterios_esperados"] == 2


@pytest.mark.asyncio
async def test_iterator_isola_erro_e_continua_proxima_task():
    loop, _, state = await _executar_iterator(
        {"tasks": [{"id": "TASK-001"}, {"id": "TASK-002"}]},
        {"TASK-001": "erro", "TASK-002": "aprovado"},
    )

    assert [c["task_id"] for c in loop.chamadas] == ["TASK-001", "TASK-002"]
    summary = state["task_iteration_summary"]
    assert summary["processed_task_ids"] == ["TASK-001", "TASK-002"]
    assert summary["approved_task_ids"] == ["TASK-002"]
    assert (
        summary["task_results"]["TASK-001"]["motivo_terminacao"] == "erro_operacional"
    )
    assert summary["cobertura_completa"] is False


@pytest.mark.asyncio
async def test_iterator_entrada_invalida_nao_invoca_loop():
    loop, _, state = await _executar_iterator(
        {"tasks": [{"id": "TASK-invalida"}]},
        {},
    )
    assert loop.chamadas == []
    summary = state["task_iteration_summary"]
    assert summary["input_valid"] is False
    assert summary["cobertura_completa"] is False


def test_resolver_task_id_state_prevalece_e_fallback_e_preservado(monkeypatch):
    recebidos = []

    def fake_validacao(task_id, iteration, tool_context=None):
        recebidos.append((task_id, iteration, tool_context))
        return {"work_item_id": task_id}

    monkeypatch.setattr(harness_execucao, "executar_harness_validacao", fake_validacao)
    contexto = SimpleNamespace(state={"task_id": "TASK-002"})

    resultado = harness_execucao.executar_harness_tool(
        "TASK-999", iteration=3, tool_context=contexto
    )
    assert resultado["work_item_id"] == "TASK-002"
    assert recebidos[-1][:2] == ("TASK-002", 3)

    resultado_direto = harness_execucao.executar_harness_tool("TASK-003")
    assert resultado_direto["work_item_id"] == "TASK-003"


def test_detalhe_erro_operacional_nao_expoe_mensagem_bruta():
    detalhe = detalhe_erro_operacional(RuntimeError("segredo " * 100))
    assert detalhe == "RuntimeError: erro operacional; consulte os logs."
    assert "segredo" not in detalhe


# ===========================================================================
# Política de progresso (issue #394)
# ===========================================================================


def _reprovado(**extra) -> dict:
    state = {
        "validation": {
            "work_item_id": "TASK-001",
            "status": "reprovado",
            "blocking_reason": "sem progresso",
        }
    }
    state.update(extra)
    return state


@pytest.mark.parametrize(
    "motivo,esperado",
    [
        ("plato_nota", "bloqueado_plato_nota"),
        ("sem_alteracao_arquivos", "bloqueado_sem_alteracao_arquivos"),
        ("erro_repetido", "bloqueado_erro_repetido"),
    ],
)
def test_motivo_de_travamento_e_preservado(motivo, esperado):
    """O motivo específico distingue 'a solução parou de evoluir' de 'o coder
    parou de mexer no código' — análises diferentes, antes achatadas num
    'bloqueado_estagnacao' genérico."""
    resultado = classificar_desfecho(_reprovado(loop_stop_reason=motivo), "TASK-001")

    assert resultado["status"] == "bloqueado"
    assert resultado["motivo_terminacao"] == esperado


def test_campo_tipado_decide_mesmo_com_texto_conflitante():
    """O texto do turno não interfere: só o campo da política é consultado."""
    state = _reprovado(
        loop_stop_reason="plato_nota",
        execution_result="tudo certo por aqui",
    )

    assert classificar_desfecho(state, "TASK-001")["motivo_terminacao"] == (
        "bloqueado_plato_nota"
    )


def test_reprovado_sem_travamento_nao_vira_bloqueado():
    resultado = classificar_desfecho(_reprovado(), "TASK-001")

    assert resultado["status"] == "reprovado"
    assert resultado["motivo_terminacao"] == "reprovado_apos_loop"


def test_nota_e_historico_aparecem_no_desfecho():
    state = _reprovado(
        progress_score_history=[0.2, 0.5, 0.5],
        progress_score_details=[
            {"build_concluido": 0.0},
            {"build_concluido": 1.0},
            {"build_concluido": 1.0},
        ],
    )

    resultado = classificar_desfecho(state, "TASK-001")

    assert resultado["nota_final"] == 0.5
    assert resultado["historico_notas"] == [0.2, 0.5, 0.5]
    assert resultado["detalhes_notas"] == [
        {"build_concluido": 0.0},
        {"build_concluido": 1.0},
        {"build_concluido": 1.0},
    ]


@pytest.mark.parametrize(
    "state",
    [
        {"validation": {"work_item_id": "TASK-001", "status": "aprovado"}},
        {"validation": {"work_item_id": "TASK-999", "status": "aprovado"}},
        {"validation": {"work_item_id": "TASK-001", "status": "coisa_estranha"}},
        {
            "validation": {"work_item_id": "TASK-001", "status": "reprovado"},
            "loop_stop_reason": "plato_nota",
        },
        {"validation": {"work_item_id": "TASK-001", "status": "reprovado"}},
    ],
)
def test_progresso_acompanha_todos_os_desfechos(state):
    """Task reprovada ou travada é justamente onde o histórico mais importa."""
    state = {**state, "progress_score_history": [0.4]}

    resultado = classificar_desfecho(state, "TASK-001")

    assert resultado["nota_final"] == 0.4
    assert resultado["historico_notas"] == [0.4]


def test_historico_ausente_nao_estoura():
    resultado = classificar_desfecho(_reprovado(), "TASK-001")

    assert resultado["nota_final"] is None
    assert resultado["historico_notas"] == []
    assert resultado["detalhes_notas"] == []


def test_historico_corrompido_e_ignorado():
    state = _reprovado(
        progress_score_history=["x", None, 0.7],
        progress_score_details=[{"x": 1}, {"y": 1}, {"app_iniciou": 1.0}],
    )

    resultado = classificar_desfecho(state, "TASK-001")
    assert resultado["nota_final"] == 0.7
    assert resultado["detalhes_notas"] == [{"app_iniciou": 1.0}]


def test_motivo_de_travamento_desconhecido_e_ignorado():
    resultado = classificar_desfecho(
        _reprovado(loop_stop_reason="motivo_inventado"), "TASK-001"
    )

    assert resultado["status"] == "reprovado"
    assert resultado["motivo_terminacao"] == "reprovado_apos_loop"


# ---------------------------------------------------------------------------
# Não-vazamento entre tasks
# ---------------------------------------------------------------------------


def test_chaves_da_politica_sao_limpas_entre_tasks():
    """Sem isso, a task seguinte herdaria o histórico e o fingerprint da
    anterior — sua primeira rodada seria lida como 'sem alteração'."""
    assert set(CHAVES_DE_CICLO) <= set(_CHAVES_CICLO_REMOVIDAS)


def test_resetar_ciclo_remove_o_estado_de_progresso():
    state = {
        "progress_score_history": [0.5],
        "progress_score_details": [{"build_concluido": 1.0}],
        "progress_last_fingerprint": "abc",
        "progress_last_error_signature": "def",
        "loop_stop_reason": "plato_nota",
        "validation": {"status": "reprovado"},
    }

    TaskIterator._resetar_ciclo(state, primeira=False, task_id="TASK-002")

    assert not any(chave in state for chave in CHAVES_DE_CICLO)


def test_travamento_antes_de_haver_veredito_e_classificado(monkeypatch):
    """Regressão: o gate pode encerrar o loop antes de o validador rodar.

    Quando o coder nunca produz o mínimo executável, o harness nunca roda e não
    existe `validation`. O loop encerra corretamente pela política, mas o motivo
    sumia do summary — virava "validation_ausente_ou_invalida", uma falha
    genérica que esconde a informação mais útil que temos.
    """
    resultado = classificar_desfecho(
        {
            "progress_score_history": [0.0, 0.0, 0.0],
            "loop_stop_reason": "sem_alteracao_arquivos",
        },
        "TASK-001",
    )

    assert resultado["status"] == "bloqueado"
    assert resultado["motivo_terminacao"] == "bloqueado_sem_alteracao_arquivos"
    assert resultado["nota_final"] == 0.0


def test_veredito_ausente_sem_travamento_continua_reprovado():
    """Sem motivo de parada, a falta de veredito segue sendo o diagnóstico."""
    resultado = classificar_desfecho({"progress_score_history": [0.3]}, "TASK-001")

    assert resultado["status"] == "reprovado"
    assert resultado["motivo_terminacao"] == "validation_ausente_ou_invalida"


# ===========================================================================
# Nota unificada — técnica + aceite (Fase 6)
# ===========================================================================


def _aceite(nota, cobertura=1.0, total=2, atendidos=2, nao_atendidos=0):
    return {
        "nota": nota,
        "cobertura": cobertura,
        "total": total,
        "atendidos": atendidos,
        "nao_atendidos": nao_atendidos,
        "decididos": atendidos + nao_atendidos,
        "por_resultado": {},
        "criterios_enderecaveis": [],
    }


def test_nota_final_compoe_tecnica_e_aceite():
    state = _reprovado(
        progress_score_history=[0.8],
        acceptance_score=_aceite(0.5, cobertura=1.0),
    )

    resultado = classificar_desfecho(state, "TASK-001")

    assert resultado["nota_tecnica_final"] == 0.8
    assert resultado["nota_aceite"] == 0.5
    assert resultado["nota_final"] == pytest.approx(0.65 * 0.8 + 0.35 * 0.5)
    assert resultado["cobertura_criterios"] == 1.0


def test_sem_aceite_a_nota_final_e_a_tecnica_pura():
    """Compatível com o comportamento anterior à dimensão de aceite."""
    resultado = classificar_desfecho(
        _reprovado(progress_score_history=[0.9]), "TASK-001"
    )

    assert resultado["nota_final"] == 0.9
    assert resultado["nota_tecnica_final"] == 0.9
    assert resultado["nota_aceite"] is None
    assert resultado["cobertura_criterios"] == 0.0


def test_cobertura_baixa_nao_desconta_da_nota_final():
    """Cegueira do harness é medida à parte, nunca desconto na nota.

    Mesma nota de aceite, coberturas muito diferentes: a nota final tem de ser
    IDÊNTICA. Só a cobertura publicada distingue os dois casos.
    """
    ampla = classificar_desfecho(
        _reprovado(
            progress_score_history=[0.9],
            acceptance_score=_aceite(1.0, cobertura=1.0, total=8, atendidos=8),
        ),
        "TASK-001",
    )
    estreita = classificar_desfecho(
        _reprovado(
            progress_score_history=[0.9],
            acceptance_score=_aceite(1.0, cobertura=0.25, total=8, atendidos=2),
        ),
        "TASK-001",
    )

    assert estreita["nota_final"] == ampla["nota_final"]
    assert estreita["cobertura_criterios"] == 0.25
    assert ampla["cobertura_criterios"] == 1.0


def test_conceito_deriva_da_nota_unificada():
    """Aceite ruim rebaixa o conceito mesmo com a técnica impecável."""
    state = _reprovado(
        progress_score_history=[1.0], acceptance_score=_aceite(0.0)
    )

    resultado = classificar_desfecho(state, "TASK-001")

    assert resultado["nota_final"] == pytest.approx(0.65)
    assert resultado["conceito"] == "B"


@pytest.mark.parametrize(
    "bruto",
    [None, "texto", 42, [], {"nota": "x"}, {"nota": True}, {"cobertura": "y"}],
)
def test_aceite_corrompido_degrada_para_a_nota_tecnica(bruto):
    state = _reprovado(progress_score_history=[0.7], acceptance_score=bruto)

    resultado = classificar_desfecho(state, "TASK-001")

    assert resultado["nota_final"] == 0.7
    assert resultado["nota_aceite"] is None


def test_chaves_de_aceite_sao_limpas_entre_tasks():
    """O flag do aviso precisa zerar, ou só a primeira task o receberia."""
    assert "acceptance_score" in _CHAVES_CICLO_REMOVIDAS
    assert "acceptance_coverage_notice_used" in _CHAVES_CICLO_REMOVIDAS
