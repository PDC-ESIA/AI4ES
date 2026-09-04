"""Testes unitários para _try_parse_json — extração robusta de JSON do texto."""

import pytest

from src.agents.workflow_taco.agent import _try_parse_json


# ---------------------------------------------------------------------------
# Fast path — parse direto
# ---------------------------------------------------------------------------


def test_json_valido_direto():
    data = _try_parse_json('{"challenge": {"title": "Soma"}}')
    assert data == {"challenge": {"title": "Soma"}}


def test_json_valido_completo():
    json_str = (
        '{"challenge": {"title": "X", "constraints": {"forbidden": [], "required": []}},'
        ' "solutionsRequested": 2, "variations": []}'
    )
    data = _try_parse_json(json_str)
    assert data["challenge"]["title"] == "X"
    assert data["solutionsRequested"] == 2


def test_cenario2_json_direto():
    data = _try_parse_json('{"codigo_aluno": "print(1)", "exercicio": {}}')
    assert data["codigo_aluno"] == "print(1)"


# ---------------------------------------------------------------------------
# Entradas inválidas
# ---------------------------------------------------------------------------


def test_texto_livre_sem_json_retorna_none():
    assert _try_parse_json("gere um gabarito para soma de dois inteiros") is None


def test_texto_vazio_retorna_none():
    assert _try_parse_json("") is None


def test_somente_espacos_retorna_none():
    assert _try_parse_json("   \n\t  ") is None


def test_lista_json_retorna_none():
    assert _try_parse_json("[1, 2, 3]") is None


def test_json_invalido_incompleto_retorna_none():
    assert _try_parse_json('{"challenge": {') is None


# ---------------------------------------------------------------------------
# Extração de markdown fence
# ---------------------------------------------------------------------------


def test_extrai_de_fence_com_json():
    texto = 'Aqui está:\n```json\n{"challenge": {"title": "Teste"}}\n```'
    data = _try_parse_json(texto)
    assert data == {"challenge": {"title": "Teste"}}


def test_extrai_de_fence_sem_linguagem():
    texto = "```\n{\"codigo_aluno\": \"x = 1\"}\n```"
    data = _try_parse_json(texto)
    assert data == {"codigo_aluno": "x = 1"}


def test_extrai_de_fence_com_json_aninhado():
    texto = (
        "Resultado:\n```json\n"
        '{"challenge": {"title": "X", "constraints": {"forbidden": []}}}\n'
        "```"
    )
    data = _try_parse_json(texto)
    assert data["challenge"]["constraints"] == {"forbidden": []}


# ---------------------------------------------------------------------------
# Extração de bloco livre no texto
# ---------------------------------------------------------------------------


def test_extrai_json_embutido_em_texto():
    texto = 'Aqui está o JSON: {"codigo_aluno": "print(1)", "exercicio": {}} obrigado.'
    data = _try_parse_json(texto)
    assert data is not None
    assert data.get("codigo_aluno") == "print(1)"


def test_extrai_json_com_texto_antes():
    texto = "Claro! O JSON normalizado é:\n\n{\"challenge\": {\"title\": \"Soma\"}}"
    data = _try_parse_json(texto)
    assert data == {"challenge": {"title": "Soma"}}


def test_extrai_json_aninhado_do_texto_livre():
    texto = (
        "Segue a normalização:\n"
        '{"challenge": {"title": "LCS", "constraints": {"forbidden": [], "required": []}}, '
        '"solutionsRequested": 3, "variations": [{"label": "dp", "strategy": "tabulacao", '
        '"use": [], "avoid": []}]}'
    )
    data = _try_parse_json(texto)
    assert data["solutionsRequested"] == 3
    assert data["variations"][0]["label"] == "dp"
