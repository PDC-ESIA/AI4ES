"""Testes de aceite independentes do coder (`AI4ES_ACEITE_INDEPENDENTE`).

Cobre o mapa critério→teste extraído do arquivo, a decisão dos critérios no
harness, o veredito do validador, a ferramenta e o gate do autor, a proteção
contra edição pelo coder e os gates de aceitação com ressalvas e do manifesto.
Com a flag desligada, cada peça mantém o comportamento histórico.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from google.adk.agents import BaseAgent
from google.adk.events.event import Event
from google.genai import types
from pydantic import PrivateAttr

from shared.execution.sandbox import CommandResult
from shared.tools.coding_tools import aceite_independente as ai
from shared.tools.coding_tools import harness_execucao as harness
from src.agents.implementation_validator.agent import montar_veredito
from src.agents.implementation_validator.schemas import CriterionStatus, VerdictStatus
from tests.unit import test_harness_execucao as th

_FLAG = "AI4ES_ACEITE_INDEPENDENTE"
_ARQ = ai.caminho_relativo("TASK-001")

_CODIGO = '''
import pytest

def test_CA_01_cria_ensaio():
    assert 1

def test_CA_01_lista_ensaio():
    assert 1

class TestStatus:
    def test_CA_03_retorna_201(self):
        assert 1

def test_CA_09_nao_existe():
    assert 1

def auxiliar():
    pass
'''


@pytest.fixture
def ligada(monkeypatch):
    monkeypatch.setenv(_FLAG, "true")


@pytest.fixture
def desligada(monkeypatch):
    monkeypatch.delenv(_FLAG, raising=False)


# ── Mapa ───────────────────────────────────────────────────────────────────


def test_mapa_sai_do_nome_das_funcoes_e_ignora_ids_fora_da_task():
    mapa = ai.extrair_mapa(_CODIGO, ["CA-01", "CA-02", "CA-03"], _ARQ)
    assert mapa == {
        "CA-01": [f"{_ARQ}::test_CA_01_cria_ensaio", f"{_ARQ}::test_CA_01_lista_ensaio"],
        "CA-03": [f"{_ARQ}::TestStatus::test_CA_03_retorna_201"],
    }


def test_mapa_de_codigo_que_nao_compila_levanta():
    with pytest.raises(SyntaxError):
        ai.extrair_mapa("def test_CA_01(:\n", ["CA-01"], _ARQ)


def test_mapa_gravado_e_lido_so_para_a_propria_task(tmp_path):
    ai.gravar_mapa(tmp_path, "TASK-001", _ARQ, {"CA-01": ["x::y"]})
    assert ai.ler_mapa(tmp_path, "TASK-001")["por_criterio"] == {"CA-01": ["x::y"]}
    assert ai.ler_mapa(tmp_path, "TASK-002") is None
    ai.caminho_mapa(tmp_path, "TASK-002").write_text(json.dumps({"task_id": "TASK-001"}))
    assert ai.ler_mapa(tmp_path, "TASK-002") is None


@pytest.mark.parametrize(
    "caminho, protegido",
    [
        ("tests/acceptance/test_aceite_TASK_001.py", True),
        ("backend/tests/acceptance/x.py", True),
        ("./tests/acceptance", True),
        ("tests/test_ensaios.py", False),
        ("tests/acceptance_extra.py", False),
        (None, False),
    ],
)
def test_caminho_protegido(caminho, protegido):
    assert ai.e_caminho_protegido(caminho) is protegido


def test_comando_de_aceite_reaproveita_o_prefixo_do_pytest():
    assert ai.comando_de_aceite(["venv/bin/python -m pytest -v tests"], _ARQ) == (
        f"venv/bin/python -m pytest -v -p no:cacheprovider {_ARQ}"
    )
    assert ai.comando_de_aceite(["npm test"], _ARQ) is None


# ── Harness ────────────────────────────────────────────────────────────────


def _cenario_harness(tmp_path, saida_aceite: str, *, saida_suite: str = "1 passed"):
    coder, execution, tasks = th._dirs(tmp_path)
    th._write_task(
        tasks,
        criteria=[
            {"id": "CA-01", "description": "Cria ensaio", "automatable": True},
            {"id": "CA-02", "description": "Retorna 201", "automatable": True},
            {"id": "CA-03", "description": "Visual agradável", "automatable": False},
        ],
    )
    th._write_manifest(coder, th._manifest_command(test=["venv/bin/python -m pytest -v tests/test_meu.py"]))
    ai.gravar_mapa(
        tasks,
        "TASK-001",
        _ARQ,
        {"CA-01": [f"{_ARQ}::test_CA_01_cria"], "CA-02": [f"{_ARQ}::test_CA_02_status"]},
    )
    sandbox = th.FakeSandbox(
        exec_results={
            _ARQ: CommandResult(exit_code=1, stdout=saida_aceite, stderr=""),
            "pytest": CommandResult(exit_code=0, stdout=saida_suite, stderr=""),
        }
    )
    relatorio = th._run("TASK-001", coder, execution, tasks, sandbox)
    return relatorio, sandbox


_SAIDA_ACEITE = (
    f"{_ARQ}::test_CA_01_cria PASSED\n"
    f"{_ARQ}::test_CA_02_status FAILED\n"
    "1 failed, 1 passed in 0.1s"
)


def test_harness_decide_criterios_pelos_testes_independentes(ligada, tmp_path):
    relatorio, sandbox = _cenario_harness(tmp_path, _SAIDA_ACEITE)

    assert any(_ARQ in c for c in sandbox.exec_calls), "comando de aceite não rodou"
    por_id = {e["criterion_id"]: e for e in relatorio["criteria_evidence"]}
    assert por_id["CA-01"]["outcome"] == "atendido"
    assert por_id["CA-02"]["outcome"] == "nao_atendido"
    assert por_id["CA-03"]["outcome"] == "nao_avaliado"
    assert por_id["CA-02"]["checkable"] is True
    # Teste de aceite falho também reprova tecnicamente a suíte.
    testes = next(s for s in relatorio["stages"] if s["stage"] == "testes_automatizados")
    assert testes["status"] == "falha"


def test_harness_sem_resultado_do_teste_marca_nao_executado(ligada, tmp_path):
    relatorio, _ = _cenario_harness(tmp_path, "nada reconhecível")
    por_id = {e["criterion_id"]: e for e in relatorio["criteria_evidence"]}
    assert por_id["CA-01"]["outcome"] == "teste_nao_executado"


def test_harness_nao_reexecuta_quando_a_suite_ja_coletou(ligada, tmp_path):
    suite = (
        f"{_ARQ}::test_CA_01_cria PASSED\n{_ARQ}::test_CA_02_status PASSED\n2 passed in 0.1s"
    )
    relatorio, sandbox = _cenario_harness(tmp_path, "", saida_suite=suite)
    assert not any("no:cacheprovider" in c for c in sandbox.exec_calls)
    assert {e["outcome"] for e in relatorio["criteria_evidence"][:2]} == {"atendido"}


def test_harness_sem_flag_ignora_o_mapa(desligada, tmp_path):
    relatorio, sandbox = _cenario_harness(tmp_path, _SAIDA_ACEITE)
    assert not any(_ARQ in c for c in sandbox.exec_calls)
    assert {e["outcome"] for e in relatorio["criteria_evidence"]} == {"nao_avaliado"}


# ── Validador ──────────────────────────────────────────────────────────────


def _report(overall="sucesso", outcome="nao_atendido"):
    return {
        "work_item_id": "TASK-001",
        "overall_status": overall,
        "acceptance_criteria": ["Retorna 201", "Cria ensaio"],
        "stages": [{"stage": "testes_automatizados", "status": "sucesso"}],
        "criteria_evidence": [
            {"criterion": "Retorna 201", "criterion_id": "CA-02", "outcome": outcome,
             "observed": "test → falhou", "linked_tests": ["t::CA_02"]},
            {"criterion": "Cria ensaio", "criterion_id": "CA-01", "outcome": "nao_avaliado"},
        ],
    }


def test_validador_reprova_criterio_nao_atendido_mesmo_com_execucao_ok(ligada):
    veredito = montar_veredito(_report())
    assert veredito.status == VerdictStatus.REPROVADO
    assert "CA-02" in veredito.blocking_reason
    status = {v.criterion: v.status for v in veredito.criteria_verdicts}
    assert status["Retorna 201"] == CriterionStatus.NAO_ATENDIDO


def test_validador_aprova_com_criterios_atendidos(ligada):
    veredito = montar_veredito(_report(outcome="atendido"))
    assert veredito.status == VerdictStatus.APROVADO
    status = {v.criterion: v.status for v in veredito.criteria_verdicts}
    assert status["Retorna 201"] == CriterionStatus.ATENDIDO


def test_validador_em_falha_de_execucao_mostra_o_criterio_decidido(ligada):
    veredito = montar_veredito(_report(overall="falha"))
    assert veredito.status == VerdictStatus.REPROVADO
    status = {v.criterion: v.status for v in veredito.criteria_verdicts}
    assert status == {
        "Retorna 201": CriterionStatus.NAO_ATENDIDO,
        "Cria ensaio": CriterionStatus.INCONCLUSIVO,
    }
    assert "CA-02" in veredito.blocking_reason


def test_validador_sem_flag_mantem_a_politica_de_execucao(desligada):
    assert montar_veredito(_report()).status == VerdictStatus.APROVADO


# ── Ferramenta e gate do autor ─────────────────────────────────────────────


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    modulo = importlib.import_module("src.agents.workflow_coding_review.acceptance.agent")
    from shared.workspace import get_agent_workspace

    coder = get_agent_workspace("cr_coder")
    (coder / "app").mkdir(parents=True, exist_ok=True)
    (coder / "app" / "main.py").write_text("app = 1\n")
    (coder / "run.json").write_text(
        json.dumps({"surface": "command", "run": "venv/bin/python -m app.main",
                    "test": ["venv/bin/python -m pytest -v"]})
    )
    return SimpleNamespace(
        modulo=modulo, coder=coder, tasks=get_agent_workspace("cr_context_engineer")
    )


_TASKS = {
    "macro_context": {"tech_stack": ["python"]},
    "tasks": [
        {
            "id": "TASK-001",
            "description": "CRUD",
            "acceptance_criteria": [
                {"id": "CA-01", "description": "cria", "automatable": True},
                {"id": "CA-02", "description": "visual", "automatable": False},
            ],
        }
    ],
}


def test_ferramenta_grava_teste_e_mapa(ws):
    ctx = SimpleNamespace(state={"task_id": "TASK-001", "tasks": _TASKS})
    codigo = "def test_CA_01_cria():\n    assert 1\n\ndef test_CA_02_visual():\n    assert 1\n"
    resposta = ws.modulo.tool_salvar_teste_aceite(codigo, ctx)

    assert resposta["sucesso"] is True
    assert resposta["criterios_cobertos"] == ["CA-01"]  # CA-02 não é automatizável
    assert (ws.coder / _ARQ).read_text() == codigo
    assert ai.ler_mapa(ws.tasks, "TASK-001")["por_criterio"] == {
        "CA-01": [f"{_ARQ}::test_CA_01_cria"]
    }


@pytest.mark.parametrize(
    "codigo, trecho",
    [("def test_CA_01(:\n", "não compila"), ("def test_outro():\n    pass\n", "Nenhuma função")],
)
def test_ferramenta_recusa_arquivo_invalido(ws, codigo, trecho):
    ctx = SimpleNamespace(state={"task_id": "TASK-001", "tasks": _TASKS})
    resposta = ws.modulo.tool_salvar_teste_aceite(codigo, ctx)
    assert resposta["sucesso"] is False and trecho in resposta["erro"]
    assert ai.ler_mapa(ws.tasks, "TASK-001") is None


class _AutorFalso(BaseAgent):
    _chamadas: list = PrivateAttr(default_factory=list)

    async def _run_async_impl(self, ctx):
        self._chamadas.append(ctx.session.state.get("aceite_task"))
        yield Event(
            invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text="ok")]),
        )


async def _rodar_gate(modulo, state):
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService

    autor = _AutorFalso(name="autor_falso")
    gate = modulo.AceiteIndependenteGate(name="gate_teste", sub_agents=[autor])
    servico = InMemorySessionService()
    runner = Runner(agent=gate, app_name="t", session_service=servico)
    sessao = await servico.create_session(app_name="t", user_id="u", state=state)
    async for _ in runner.run_async(
        user_id="u", session_id=sessao.id,
        new_message=types.Content(role="user", parts=[types.Part(text="x")]),
    ):
        pass
    final = await servico.get_session(app_name="t", user_id="u", session_id=sessao.id)
    return autor._chamadas, final.state


@pytest.mark.asyncio
async def test_gate_invoca_o_autor_com_a_task_e_conta_tentativas(ws, ligada):
    chamadas, state = await _rodar_gate(ws.modulo, {"task_id": "TASK-001", "tasks": _TASKS})
    assert len(chamadas) == 1
    dados = json.loads(chamadas[0])
    assert dados["task"]["id"] == "TASK-001"
    assert dados["arquivo_de_testes"] == _ARQ
    assert "app/main.py" in dados["arquivos_do_projeto"]
    assert state["aceite_tentativas"] == {"TASK-001": 1}


@pytest.mark.asyncio
async def test_gate_nao_roda_sem_flag_com_mapa_ou_sem_tentativas(ws, monkeypatch):
    estado = {"task_id": "TASK-001", "tasks": _TASKS}
    monkeypatch.delenv(_FLAG, raising=False)
    assert (await _rodar_gate(ws.modulo, dict(estado)))[0] == []

    monkeypatch.setenv(_FLAG, "true")
    esgotado = {**estado, "aceite_tentativas": {"TASK-001": ws.modulo.MAX_TENTATIVAS}}
    assert (await _rodar_gate(ws.modulo, esgotado))[0] == []

    ai.gravar_mapa(ws.tasks, "TASK-001", _ARQ, {"CA-01": ["x"]})
    assert (await _rodar_gate(ws.modulo, dict(estado)))[0] == []


@pytest.mark.asyncio
async def test_gate_espera_o_artefato_executavel(ws, ligada):
    (ws.coder / "run.json").unlink()
    assert (await _rodar_gate(ws.modulo, {"task_id": "TASK-001", "tasks": _TASKS}))[0] == []


def test_loop_inclui_o_gate_so_com_a_flag(tmp_path):
    # Processo à parte: o pipeline não pode ser recarregado no mesmo processo
    # (cada sub-agente só aceita um parent).
    import os
    import subprocess
    import sys

    codigo = (
        "from src.agents.workflow_coding_review.agent import _code_execute_loop as l;"
        "print(','.join(a.name for a in l.sub_agents))"
    )

    def _nomes(valor):
        env = {**os.environ, _FLAG: valor, "WORKSPACE_OUTPUT_DIR": str(tmp_path / "ws")}
        saida = subprocess.run(
            [sys.executable, "-c", codigo], env=env, capture_output=True, text=True,
            cwd=str(Path(__file__).resolve().parents[2]), timeout=120,
        )
        return saida.stdout.strip().splitlines()[-1]

    assert _nomes("true") == "cr_coder_agent,acceptance_gate,cr_executor_agent"
    assert _nomes("") == "cr_coder_agent,cr_executor_agent"


# ── Proteção, ressalvas e manifesto ────────────────────────────────────────


def test_coder_nao_escreve_em_tests_acceptance(ligada):
    from src.agents.workflow_coding_review.coder.workspace_guard import proteger_testes_de_aceite

    ctx = SimpleNamespace(state={})
    for nome in ("tool_criar_arquivo", "tool_substituir_trecho", "tool_remover_arquivo"):
        resposta = proteger_testes_de_aceite(SimpleNamespace(name=nome), {"caminho": _ARQ}, ctx)
        assert resposta["codigo"] == "TESTE_DE_ACEITE_PROTEGIDO"
    ler = SimpleNamespace(name="tool_ler_arquivo")
    assert proteger_testes_de_aceite(ler, {"caminho": _ARQ}, ctx) is None
    criar = SimpleNamespace(name="tool_criar_arquivo")
    assert proteger_testes_de_aceite(criar, {"caminho": "tests/test_x.py"}, ctx) is None


def test_protecao_desligada_sem_flag(desligada):
    from src.agents.workflow_coding_review.coder.workspace_guard import proteger_testes_de_aceite

    criar = SimpleNamespace(name="tool_criar_arquivo")
    assert proteger_testes_de_aceite(criar, {"caminho": _ARQ}, SimpleNamespace(state={})) is None


_PROGRESSO_B = {"conceito": "B", "historico_notas": [0.8], "detalhes_notas": [
    {"minimo_para_rodar": 1, "ambiente_preparado": 1, "build_concluido": 1, "app_iniciou": 1}
]}


@pytest.mark.parametrize("cobertura, aceita", [(0.0, False), (0.5, False), (0.6, True), (1.0, True)])
def test_ressalvas_exigem_cobertura_com_a_flag(ligada, cobertura, aceita):
    from src.agents.workflow_coding_review.task_iterator import _aceitavel_com_ressalvas

    progresso = {**_PROGRESSO_B, "cobertura_criterios": cobertura}
    assert _aceitavel_com_ressalvas(progresso, "/r.json") is aceita


def test_ressalvas_sem_flag_ignoram_cobertura(desligada):
    from src.agents.workflow_coding_review.task_iterator import _aceitavel_com_ressalvas

    assert _aceitavel_com_ressalvas({**_PROGRESSO_B, "cobertura_criterios": 0.0}, "/r.json")


def _emitir_manifesto(tmp_path, monkeypatch, nao_atendidos):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import get_agent_workspace
    from src.agents.workflow_coding_review import manifest

    coder = get_agent_workspace("cr_coder")
    (coder / "app.py").write_text("x = 1\n")
    review = coder.parent / "review"
    review.mkdir(parents=True, exist_ok=True)
    (review / "review.md").write_text("## Status: APROVADO\n")
    state = {
        "task_iteration_summary": {
            "approved_task_ids": ["TASK-001"],
            "accepted_task_ids": [],
            "task_results": {
                "TASK-001": {"status": "aprovado", "criterios_esperados": 2, "aceite": {
                    "total": 2, "atendidos": 2 - nao_atendidos, "nao_atendidos": nao_atendidos}},
            },
        }
    }
    manifest.emit_coding_manifest(SimpleNamespace(state=state))
    return state["coding_manifest"]["status"]


def test_manifesto_fica_parcial_com_criterio_reprovado(tmp_path, monkeypatch, ligada):
    assert _emitir_manifesto(tmp_path, monkeypatch, nao_atendidos=1) == "partial"


def test_manifesto_ok_quando_todos_atendidos(tmp_path, monkeypatch, ligada):
    assert _emitir_manifesto(tmp_path, monkeypatch, nao_atendidos=0) == "ok"


def test_manifesto_sem_flag_nao_usa_criterios(tmp_path, monkeypatch, desligada):
    assert _emitir_manifesto(tmp_path, monkeypatch, nao_atendidos=1) == "ok"
