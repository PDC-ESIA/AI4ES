"""Testes do contexto injetado no prompt do reviewer (`_review_context`).

Com `include_contents="none"` esse bloco é a ÚNICA visão que o reviewer tem do
que o pipeline produziu — o histórico da sessão não entra mais no prompt. Duas
propriedades precisam valer sempre: nada essencial pode ser perdido, e o
tamanho precisa ser limitado por construção (o bloco vive na instrução, que é
reenviada a cada requisição do turno).
"""

import importlib
import json

import pytest


@pytest.fixture
def cr_reviewer(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as modulo

    importlib.reload(review_tools)
    importlib.reload(modulo)
    return modulo


def _state(tasks=None, macro=None, summary=None):
    return {
        "tasks": {
            "macro_context": macro if macro is not None else {"tech_stack": ["FastAPI"]},
            "tasks": tasks if tasks is not None else [{"id": "TASK-001"}],
        },
        "task_iteration_summary": summary
        if summary is not None
        else {"cobertura_completa": True, "expected_task_ids": ["TASK-001"]},
    }


def test_contexto_preserva_macro_context(cr_reviewer):
    """Sem histórico de sessão, é a única fonte de stack/product_type/regras."""
    contexto = cr_reviewer._review_context(
        _state(macro={"tech_stack": ["Go/Gin"], "product_type": "api_service",
                      "global_rules": ["camadas: handler/service/repo"]})
    )

    assert "## macro_context" in contexto
    assert "Go/Gin" in contexto
    assert "api_service" in contexto
    assert "handler/service/repo" in contexto


def test_summary_vem_antes_das_tasks(cr_reviewer):
    """A ordem é contrato: o summary é o dado que decide o veredito de cobertura."""
    contexto = cr_reviewer._review_context(_state())

    assert contexto.index("## task_iteration_summary") < contexto.index("## tasks")


def test_tasks_excedentes_sao_omitidas_com_json_valido(cr_reviewer):
    """Trunca descartando itens inteiros — nunca cortando no meio da string."""
    gorda = {"id": "TASK-00X", "description": "D" * 8_000}
    contexto = cr_reviewer._review_context(
        _state(tasks=[{**gorda, "id": f"TASK-00{i}"} for i in range(1, 9)])
    )

    bloco = contexto.split("## tasks\n```json\n")[1].split("\n```")[0]
    corpo, _, nota = bloco.partition("\n[")
    assert "task(s) omitida(s)" in nota
    json.loads(corpo)  # o que sobrou continua sendo JSON válido


def test_task_unica_maior_que_o_orcamento_vira_marcador(cr_reviewer):
    """Sem isto a primeira task entraria sempre e o teto seria decorativo."""
    contexto = cr_reviewer._review_context(
        _state(tasks=[{"id": "TASK-001", "description": "X" * 60_000}])
    )

    bloco = contexto.split("## tasks\n```json\n")[1].split("\n```")[0]
    assert "X" * 100 not in bloco
    assert "_omitida" in bloco
    assert len(bloco) < cr_reviewer._MAX_TASKS_CHARS
    itens = json.loads(bloco)
    assert itens[0]["id"] == "TASK-001"


def test_envelope_malformado_nao_levanta(cr_reviewer):
    """Contexto degradado é aceitável; exceção no InstructionProvider não é."""
    for envelope in (None, "lixo", {"tasks": "não é lista"}, {}):
        contexto = cr_reviewer._review_context(
            {"tasks": envelope, "task_iteration_summary": None}
        )
        assert "## task_iteration_summary" in contexto
        assert "## tasks" in contexto
