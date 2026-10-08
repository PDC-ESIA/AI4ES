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
        f"venv/bin/python -m pytest -v -p no:cacheprovider -p no:warnings --tb=short -rfE {_ARQ}"
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
    (coder / ai.PASTA_ACEITE).mkdir(parents=True)
    (coder / _ARQ).write_text("def test_CA_01_cria():\n    pass\n")
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


def test_harness_isola_os_protegidos_da_suite_do_coder(ligada, tmp_path):
    relatorio, sandbox = _cenario_harness(tmp_path, _SAIDA_ACEITE)
    suite = [c for c in sandbox.exec_calls if "tests/test_meu.py" in c]
    aceite = [c for c in sandbox.exec_calls if c.endswith(_ARQ)]
    assert suite == [
        "venv/bin/python -m pytest --ignore=tests/acceptance -p no:warnings "
        "--tb=short -rfE -v tests/test_meu.py"
    ]
    assert aceite == [f"venv/bin/python -m pytest -v -p no:cacheprovider -p no:warnings --tb=short -rfE {_ARQ}"]


def test_harness_roda_aceite_de_tasks_anteriores_como_regressao(ligada, tmp_path):
    from shared.tools.coding_tools.harness_execucao import _arquivos_protegidos

    coder, execution, tasks = th._dirs(tmp_path)
    th._write_manifest(coder, th._manifest_command())
    (coder / ai.PASTA_ACEITE).mkdir(parents=True)
    for task in ("TASK-001", "TASK-002"):
        (coder / ai.caminho_relativo(task)).write_text("def test_CA_01():\n    pass\n")
    ctx = SimpleNamespace(
        manifest=SimpleNamespace(workdir="."), coder_dir=coder, mapa_independente=None
    )
    assert _arquivos_protegidos(ctx) == [
        ai.caminho_relativo("TASK-001"),
        ai.caminho_relativo("TASK-002"),
    ]


def test_execucao_isolada_usa_copia_limpa_com_o_build_reaproveitado(tmp_path, monkeypatch):
    from shared.execution.sandbox import DirectSandbox
    from shared.tools.coding_tools.harness_execucao import _rodar_isolado

    coder = tmp_path / "src"
    coder.mkdir()
    (coder / "app.db").write_text("original")
    principal = DirectSandbox()
    principal.setup(coder)
    (principal.workdir / "venv").mkdir()
    (principal.workdir / "venv" / "marca").write_text("build")
    (principal.workdir / "app.db").write_text("sujo pelos testes do coder")
    ctx = SimpleNamespace(manifest=SimpleNamespace(sandbox="direct", workdir="."), sandbox=principal, coder_dir=coder)
    try:
        res = _rodar_isolado(ctx, "cat app.db venv/marca", None)
    finally:
        principal.cleanup()
    assert res.stdout == "originalbuild"


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


# ── Teto de rodadas com testes protegidos falhando ─────────────────────────


def _report_protegido(falhou: bool) -> dict:
    return {
        "stages": [
            {
                "stage": "testes_automatizados",
                "evidence": {
                    "resultados": [
                        {"comando": "pytest -v", "exit_code": 0},
                        {"comando": f"pytest {_ARQ}", "exit_code": 1 if falhou else 0,
                         "aceite_independente": True},
                    ]
                },
            }
        ]
    }


def test_detecta_falha_em_teste_protegido():
    from src.agents.workflow_coding_review.executor.loop_policy import protegidos_falharam

    assert protegidos_falharam(_report_protegido(True)) is True
    assert protegidos_falharam(_report_protegido(False)) is False
    assert protegidos_falharam({}) is False


def test_teto_de_rodadas_seguidas_com_protegido_falhando(monkeypatch):
    from src.agents.workflow_coding_review.executor.loop_policy import (
        CHAVE_MOTIVO_PARADA,
        CHAVES_DE_CICLO,
        MOTIVO_PROTEGIDOS_TRAVADOS,
        MOTIVOS_PARADA,
        registrar_protegidos,
    )

    monkeypatch.delenv("AI4ES_PROTEGIDOS_MAX_RODADAS", raising=False)
    state: dict = {}
    assert registrar_protegidos(state, True) is None
    assert registrar_protegidos(state, False) is None  # rodada limpa zera
    assert registrar_protegidos(state, True) is None
    assert registrar_protegidos(state, True) is None
    assert registrar_protegidos(state, True) == MOTIVO_PROTEGIDOS_TRAVADOS
    assert state[CHAVE_MOTIVO_PARADA] == MOTIVO_PROTEGIDOS_TRAVADOS
    # Reconhecido pelo TaskIterator e limpo entre tasks.
    assert MOTIVO_PROTEGIDOS_TRAVADOS in MOTIVOS_PARADA
    assert "progress_protected_failures" in CHAVES_DE_CICLO


def test_executor_encerra_a_task_no_teto(monkeypatch, tmp_path, ligada):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    monkeypatch.setenv("AI4ES_PROTEGIDOS_MAX_RODADAS", "2")
    executor = importlib.import_module("src.agents.workflow_coding_review.executor.agent")
    monkeypatch.setattr(executor, "_carregar_execution_report", lambda _c: _report_protegido(True))
    monkeypatch.setattr(executor, "fingerprint_mudou", lambda _s: True)
    # Notas sempre diferentes: nenhum gatilho histórico dispararia.
    notas = iter([0.3, 0.5])
    monkeypatch.setattr(
        executor, "calcular_nota",
        lambda _r: SimpleNamespace(total=next(notas), como_dict=lambda: {}),
    )
    state = {"task_id": "TASK-001", "validation": {"status": "reprovado"}}
    ctx = SimpleNamespace(state=state, actions=SimpleNamespace(escalate=None))

    assert executor.aplicar_politica_de_progresso(ctx) is None
    parada = executor.aplicar_politica_de_progresso(ctx)
    assert ctx.actions.escalate is True
    assert "testes_protegidos_travados" in parada.parts[0].text


def test_iteracao_vem_do_historico_da_task():
    from shared.tools.coding_tools.harness_execucao import _resolver_iteracao

    assert _resolver_iteracao(1, None) == 1
    assert _resolver_iteracao(1, SimpleNamespace(state={})) == 1
    assert _resolver_iteracao(1, SimpleNamespace(state={"progress_score_history": [0.2, 0.4]})) == 3


# ── Linha de base: falhas já aceitas não reprovam tasks seguintes ──────────


def test_regressao_tolera_falha_ja_aceita_e_reprova_a_nova(ligada, tmp_path):
    coder, execution, tasks = th._dirs(tmp_path)
    th._write_task(tasks, task_id="TASK-003", criteria=[{"id": "CA-01", "description": "x", "automatable": True}])
    th._write_manifest(coder, th._manifest_command())
    (coder / ai.PASTA_ACEITE).mkdir(parents=True)
    arq2, arq3 = ai.caminho_relativo("TASK-002"), ai.caminho_relativo("TASK-003")
    for arq in (arq2, arq3):
        (coder / arq).write_text("def test_CA_01():\n    pass\n")
    ai.gravar_mapa(tasks, "TASK-002", arq2, {"CA-01": [f"{arq2}::test_CA_01_a"], "CA-03": [f"{arq2}::test_CA_03_thumb"]})
    ai.registrar_falhas_aceitas(tasks, "TASK-002", [f"{arq2}::test_CA_03_thumb"])
    ai.gravar_mapa(tasks, "TASK-003", arq3, {"CA-01": [f"{arq3}::test_CA_01_b"]})

    def _rodar(falhos_em_002):
        saida2 = "\n".join(
            f"{arq2}::{n} {'FAILED' if n in falhos_em_002 else 'PASSED'}"
            for n in ("test_CA_01_a", "test_CA_03_thumb")
        )
        sandbox = th.FakeSandbox(exec_results={
            arq2: CommandResult(exit_code=1, stdout=saida2, stderr=""),
            arq3: CommandResult(exit_code=0, stdout=f"{arq3}::test_CA_01_b PASSED\n1 passed", stderr=""),
            "pytest": CommandResult(exit_code=0, stdout="1 passed", stderr=""),
        })
        return th._run("TASK-003", coder, execution, tasks, sandbox)

    so_conhecida = _rodar({"test_CA_03_thumb"})
    testes = next(s for s in so_conhecida["stages"] if s["stage"] == "testes_automatizados")
    assert testes["status"] == "sucesso"
    from src.agents.workflow_coding_review.executor.loop_policy import protegidos_falharam
    assert protegidos_falharam(so_conhecida) is False

    regressao = _rodar({"test_CA_03_thumb", "test_CA_01_a"})
    testes = next(s for s in regressao["stages"] if s["stage"] == "testes_automatizados")
    assert testes["status"] == "falha"
    assert protegidos_falharam(regressao) is True


def test_fechar_linha_de_base_registra_falhas_do_relatorio(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import get_agent_workspace
    from src.agents.workflow_coding_review.task_iterator import fechar_linha_de_base

    tasks = get_agent_workspace("cr_context_engineer")
    arq = ai.caminho_relativo("TASK-002")
    ai.gravar_mapa(tasks, "TASK-002", arq, {"CA-01": [f"{arq}::a"], "CA-03": [f"{arq}::b"]})
    relatorio = tmp_path / "r.json"
    relatorio.write_text(json.dumps({"stages": [{"stage": "testes_automatizados", "evidence": {"resultados": [
        {"testes": [{"nodeid": f"{arq}::a", "outcome": "passou"}, {"nodeid": f"{arq}::b", "outcome": "falhou"},
                    {"nodeid": "tests/test_x.py::c", "outcome": "falhou"}]}]}}]}))
    fechar_linha_de_base("TASK-002", str(relatorio))
    assert ai.ler_mapa(tasks, "TASK-002")["falhas_aceitas"] == [f"{arq}::b"]

    fechar_linha_de_base("TASK-002", None)  # sem relatório: nada é linha de base de sucesso
    assert set(ai.ler_mapa(tasks, "TASK-002")["falhas_aceitas"]) == {f"{arq}::a", f"{arq}::b"}


def test_suite_do_coder_ganha_saida_legivel_so_com_as_flags():
    from shared.tools.coding_tools.harness_execucao import _sem_pastas_protegidas as ajustar

    assert ajustar("venv/bin/python -m pytest -v", [], legivel=False) == "venv/bin/python -m pytest -v"
    assert ajustar("venv/bin/python -m pytest -v", [], legivel=True) == (
        "venv/bin/python -m pytest -p no:warnings --tb=short -rfE -v"
    )
    # Não duplica opção que o coder já pôs.
    assert ajustar("pytest --tb=long -q", [], legivel=True) == "pytest -p no:warnings -rfE --tb=long -q"
    assert ajustar("npm test", ["tests/acceptance"], legivel=True) == "npm test"


def test_autor_roda_o_proprio_teste_so_depois_de_salvar(ws, monkeypatch):
    import shared.execution.verificacao_rapida as vr

    ctx = SimpleNamespace(state={"task_id": "TASK-001", "tasks": _TASKS, "trilha": {"id": "t"}})
    assert "Salve o arquivo" in ws.modulo.tool_executar_teste_aceite(ctx)["saida"]

    ws.modulo.tool_salvar_teste_aceite("def test_CA_01_cria():\n    assert 1\n", ctx)
    chamado = {}

    def _executar(coder_dir, trilha, arquivo):
        chamado.update(trilha=trilha, arquivo=arquivo)
        return 1, "E   TypeError: allow_redirects"

    monkeypatch.setattr(vr, "executar_arquivo_de_teste", _executar)
    resposta = ws.modulo.tool_executar_teste_aceite(ctx)
    assert resposta == {"exit_code": 1, "saida": "E   TypeError: allow_redirects"}
    assert chamado == {"trilha": {"id": "t"}, "arquivo": _ARQ}
    assert "tool_executar_teste_aceite" in [t.name for t in ws.modulo.author.tools]


def test_teto_de_chamadas_de_llm_por_pipeline(monkeypatch):
    from shared.pipeline_flags import max_llm_calls

    for flag in ("AI4ES_CODER_CONTEXTO_ENXUTO", "AI4ES_ACEITE_INDEPENDENTE", "AI4ES_JORNADA", "AI4ES_MAX_LLM_CALLS"):
        monkeypatch.delenv(flag, raising=False)
    assert max_llm_calls() == 500  # padrão do ADK, comportamento histórico
    monkeypatch.setenv("AI4ES_ACEITE_INDEPENDENTE", "true")
    assert max_llm_calls() == 2000
    monkeypatch.setenv("AI4ES_MAX_LLM_CALLS", "1200")
    assert max_llm_calls() == 1200
