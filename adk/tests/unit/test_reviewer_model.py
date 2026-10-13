"""Testes da escolha de modelo do reviewer do workflow coding_review."""

import pytest

import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer


@pytest.fixture
def sem_variaveis(monkeypatch):
    monkeypatch.delenv("REVIEWER_LLM_MODEL", raising=False)
    monkeypatch.delenv("ADK_LLM_MODEL", raising=False)
    return monkeypatch


def test_modelo_dedicado_tem_precedencia(sem_variaveis):
    sem_variaveis.setenv("ADK_LLM_MODEL", "github_copilot/gpt-4")
    sem_variaveis.setenv("REVIEWER_LLM_MODEL", "github_copilot/gpt-5-mini")
    assert cr_reviewer._resolver_modelo() == "github_copilot/gpt-5-mini"


def test_sem_modelo_dedicado_usa_o_global(sem_variaveis):
    sem_variaveis.setenv("ADK_LLM_MODEL", "github_copilot/gpt-4")
    assert cr_reviewer._resolver_modelo() == "github_copilot/gpt-4"


def test_modelo_dedicado_vazio_usa_o_global(sem_variaveis):
    # O .env.example traz REVIEWER_LLM_MODEL= vazio: não pode virar modelo "".
    sem_variaveis.setenv("ADK_LLM_MODEL", "github_copilot/gpt-4")
    sem_variaveis.setenv("REVIEWER_LLM_MODEL", "  ")
    assert cr_reviewer._resolver_modelo() == "github_copilot/gpt-4"


def test_sem_nenhuma_variavel_usa_o_padrao(sem_variaveis):
    assert cr_reviewer._resolver_modelo() == cr_reviewer._DEFAULT_MODEL


def test_agente_usa_o_modelo_resolvido_no_import():
    assert cr_reviewer.agent.model == cr_reviewer._model
