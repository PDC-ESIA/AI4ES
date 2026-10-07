"""Modo contexto enxuto do coder/reviewer (`AI4ES_CODER_CONTEXTO_ENXUTO`).

Cobre as quatro peças do modo — a task corrente publicada pelo TaskIterator, o
prompt restrito à task, o aviso de escopo e o `include_contents='none'` — e a
garantia de que quem chama o coder fora do TaskIterator (benchmarks HumanEval/
MBPP e o TACO) continua recebendo exatamente a instrução histórica.
"""

from __future__ import annotations

import asyncio
import importlib
import json
from types import SimpleNamespace

import pytest
from google.adk.events.event import Event
from google.adk.flows.llm_flows import contents as adk_contents
from google.genai import types

from src.agents.workflow_coding_review.coder import prompt as coder_prompt
from src.agents.workflow_coding_review.coder.workspace_guard import (
    CODIGO_FORA_DO_ESCOPO,
    avisar_fora_do_escopo,
)
from src.agents.workflow_coding_review.task_iterator import (
    CHAVE_TASK_ATUAL,
    TaskIterator,
    montar_task_atual,
)

_FLAG = "AI4ES_CODER_CONTEXTO_ENXUTO"

_TASK = {
    "id": "TASK-001",
    "description": "CRUD de Ensaio",
    "acceptance_criteria": [{"id": "CA-01", "description": "cria", "automatable": True}],
    "contract": {
        "inputs": [],
        "outputs": ["app/main.py", "coder/src/app/routes/ensaios.py", "app/templates/"],
        "interfaces": ["POST /ensaios"],
    },
}
_MACRO = {
    "summary": "fotos",
    "product_type": "web_app",
    "tech_stack": ["python", "fastapi"],
    "global_rules": ["roda local"],
    "extra_ignorado": "x",
}


# ── Prompt ─────────────────────────────────────────────────────────────────


def test_prompt_historico_nao_muda_sem_o_modo_enxuto():
    historico = coder_prompt.build_instruction("/ws")
    assert historico == coder_prompt.build_instruction("/ws", enxuto=False)
    assert "implemente o projeto COMPLETO" in historico
    assert "{current_task?}" not in historico


def test_prompt_enxuto_restringe_a_task_atual():
    enxuto = coder_prompt.build_instruction("/ws", enxuto=True)
    assert enxuto.startswith("# TASK ATUAL")
    assert "{current_task?}" in enxuto
    assert "projeto COMPLETO" not in enxuto
    assert "histórico desta sessão" not in enxuto
    # Os ramos de modo continuam intactos: o gate e o execution_result.
    assert "{execution_result?}" in enxuto
    assert "ANTES DE QUALQUER OUTRA COISA" in enxuto


def test_todas_as_ancoras_do_modo_enxuto_existem_no_prompt():
    historico = coder_prompt.build_instruction("/ws")
    for antigo, _ in coder_prompt._SUBSTITUICOES_ENXUTO:
        assert antigo in historico, antigo[:60]


# ── InstructionProvider (benchmarks/TACO) ──────────────────────────────────


@pytest.fixture
def coder_module(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    cr_coder = importlib.import_module("src.agents.workflow_coding_review.coder.agent")

    yield cr_coder
    monkeypatch.delenv(_FLAG, raising=False)
    importlib.reload(cr_coder)


def _instrucao(cr_coder, monkeypatch, state):
    async def _sem_injecao(texto, _ctx):
        return texto

    monkeypatch.setattr(
        "google.adk.utils.instructions_utils.inject_session_state", _sem_injecao
    )
    return asyncio.run(cr_coder._INSTRUCTION(SimpleNamespace(state=state)))


def test_sem_current_task_instrucao_e_a_historica_mesmo_com_flag(coder_module, monkeypatch):
    monkeypatch.delenv(_FLAG, raising=False)
    desligada = _instrucao(coder_module, monkeypatch, {})
    monkeypatch.setenv(_FLAG, "true")
    ligada = _instrucao(coder_module, monkeypatch, {})
    assert ligada == desligada
    assert "TASK ATUAL" not in ligada


def test_com_flag_e_current_task_a_instrucao_e_enxuta(coder_module, monkeypatch):
    monkeypatch.setenv(_FLAG, "true")
    instrucao = _instrucao(coder_module, monkeypatch, {CHAVE_TASK_ATUAL: "{}"})
    assert instrucao.startswith("# TASK ATUAL")


def test_current_task_sem_flag_nao_ativa_o_modo(coder_module, monkeypatch):
    monkeypatch.delenv(_FLAG, raising=False)
    instrucao = _instrucao(coder_module, monkeypatch, {CHAVE_TASK_ATUAL: "{}"})
    assert "TASK ATUAL" not in instrucao


def test_include_contents_segue_a_flag_no_import(coder_module, monkeypatch):
    cr_executor = importlib.import_module(
        "src.agents.workflow_coding_review.executor.agent"
    )

    monkeypatch.setenv(_FLAG, "true")
    assert importlib.reload(coder_module).agent.include_contents == "none"
    assert importlib.reload(cr_executor).agent.include_contents == "none"
    monkeypatch.delenv(_FLAG)
    assert importlib.reload(coder_module).agent.include_contents == "default"
    assert importlib.reload(cr_executor).agent.include_contents == "default"


# ── TaskIterator ───────────────────────────────────────────────────────────


def test_montar_task_atual_leva_so_o_macro_relevante():
    dados = json.loads(montar_task_atual(_TASK, _MACRO))
    assert dados["task"] == _TASK
    assert set(dados["macro_context"]) == {
        "summary",
        "product_type",
        "tech_stack",
        "global_rules",
    }


async def _rodar_iterator(monkeypatch, *, ligada: bool):
    from tests.unit.test_task_iterator import _executar_iterator

    if ligada:
        monkeypatch.setenv(_FLAG, "true")
    else:
        monkeypatch.delenv(_FLAG, raising=False)
    tasks = {"macro_context": _MACRO, "tasks": [_TASK, {**_TASK, "id": "TASK-002"}]}
    return await _executar_iterator(tasks, {})


@pytest.mark.asyncio
async def test_iterator_publica_task_atual_e_abre_turno_no_branch(monkeypatch):
    _, eventos, state = await _rodar_iterator(monkeypatch, ligada=True)

    inicios = [
        e for e in eventos
        if e.content and e.author == "task_iterator_test"
        and e.content.parts[0].text.startswith("Inicie")
    ]
    assert [e.branch for e in inicios] == [
        "task_iterator.task_0_TASK-001",
        "task_iterator.task_1_TASK-002",
    ]
    # O state final carrega a ÚLTIMA task publicada.
    assert json.loads(state[CHAVE_TASK_ATUAL])["task"]["id"] == "TASK-002"


@pytest.mark.asyncio
async def test_iterator_sem_flag_nao_publica_task_nem_evento(monkeypatch):
    _, eventos, state = await _rodar_iterator(monkeypatch, ligada=False)
    assert CHAVE_TASK_ATUAL not in state
    assert not any(
        e.content and e.content.parts and (e.content.parts[0].text or "").startswith("Inicie")
        for e in eventos
    )


def test_resetar_ciclo_remove_a_task_atual():
    state = {CHAVE_TASK_ATUAL: "{}"}
    TaskIterator._resetar_ciclo(state, primeira=True, task_id="TASK-001")
    assert CHAVE_TASK_ATUAL not in state


# ── Contexto visto pelo ADK com include_contents='none' ────────────────────


def _evento(author, texto, branch=None):
    return Event(
        invocation_id="inv",
        author=author,
        branch=branch,
        content=types.Content(role="model", parts=[types.Part(text=texto)]),
    )


def test_turno_do_coder_comeca_no_evento_da_task_nao_no_context_engineer():
    branch = "coding_review_pipeline.task_iterator.task_1_TASK-002"
    eventos = [
        _evento("cr_context_engineer", '{"tasks": ["JSON ENORME"]}'),
        _evento("cr_coder_agent", "rodada da task 1", branch="x.task_0_TASK-001"),
        _evento("task_iterator", "Inicie a TASK-002 (2/2).", branch=branch),
    ]
    vistos = adk_contents._get_current_turn_contents(branch, eventos, "cr_coder_agent")
    texto = json.dumps([c.model_dump(mode="json") for c in vistos], ensure_ascii=False)
    assert "Inicie a TASK-002" in texto
    assert "JSON ENORME" not in texto
    assert "rodada da task 1" not in texto


# ── Aviso de escopo ────────────────────────────────────────────────────────


def _ctx(state):
    return SimpleNamespace(state=state)


_STATE_ENXUTO = {CHAVE_TASK_ATUAL: montar_task_atual(_TASK, _MACRO), "task_id": "TASK-001"}
_CRIAR = SimpleNamespace(name="tool_criar_arquivo")
_OK = {"sucesso": True, "caminho": "/ws/x"}


@pytest.mark.parametrize(
    "caminho",
    [
        "app/main.py",
        "app/routes/ensaios.py",  # output citado com prefixo coder/src/
        "app/templates/painel.html",  # dentro de pasta listada
        "tests/test_ensaios.py",
        "run.json",
        "app/__init__.py",
        "requirements.txt",
    ],
)
def test_arquivo_do_contrato_ou_de_suporte_nao_gera_aviso(caminho):
    assert avisar_fora_do_escopo(_CRIAR, {"caminho": caminho}, _ctx(_STATE_ENXUTO), _OK) is None


def test_arquivo_fora_do_contrato_recebe_aviso_sem_bloquear():
    resposta = avisar_fora_do_escopo(
        _CRIAR, {"caminho": "app/routes/albums.py"}, _ctx(_STATE_ENXUTO), _OK
    )
    assert resposta["sucesso"] is True
    assert resposta["aviso"] == CODIGO_FORA_DO_ESCOPO
    assert "albums.py" in resposta["mensagem_aviso"]


def test_sem_task_atual_ou_outra_tool_nao_avisa():
    assert avisar_fora_do_escopo(_CRIAR, {"caminho": "x/y.py"}, _ctx({}), _OK) is None
    ler = SimpleNamespace(name="tool_ler_arquivo")
    assert avisar_fora_do_escopo(ler, {"caminho": "x/y.py"}, _ctx(_STATE_ENXUTO), _OK) is None
    falha = {"sucesso": False}
    assert avisar_fora_do_escopo(_CRIAR, {"caminho": "x/y.py"}, _ctx(_STATE_ENXUTO), falha) is None
