"""Testes da configuração fail-fast do LiteLLM e do preflight de credencial.

Cobre as Frentes B e C do fix de lentidão:
- Frente B: `shared` seta `litellm.request_timeout`/`num_retries` (default 120s/1),
  sobrescrevíveis por `AI4ES_LLM_TIMEOUT`/`AI4ES_LLM_NUM_RETRIES`.
- Frente C: `app.main._preflight_copilot_credential` valida a credencial no boot,
  pulando modelos não-Copilot e nunca derrubando o processo em falha.

Segurança: forçamos `ADK_LLM_MODEL` para um provider não-Copilot ANTES de importar
`app.main`, garantindo que o preflight executado no import do módulo retorne cedo
(sem tentar autenticação de rede real).
"""

import importlib
import logging

import litellm

# app.main é pré-importado em conftest.py (com env guard) antes do stub de
# pydantic feito por test_git_tools.py; aqui apenas obtemos o módulo cacheado.
import app.main as main


def _reload_shared():
    import shared

    return importlib.reload(shared)


# --------------------------------------------------------------------------- #
# Frente B: configuração global do LiteLLM
# --------------------------------------------------------------------------- #
def test_shared_aplica_defaults_de_timeout_e_retries(monkeypatch):
    monkeypatch.delenv("AI4ES_LLM_TIMEOUT", raising=False)
    monkeypatch.delenv("AI4ES_LLM_NUM_RETRIES", raising=False)
    _reload_shared()
    assert litellm.request_timeout == 120.0
    assert litellm.num_retries == 1


def test_shared_respeita_override_por_env(monkeypatch):
    monkeypatch.setenv("AI4ES_LLM_TIMEOUT", "45")
    monkeypatch.setenv("AI4ES_LLM_NUM_RETRIES", "3")
    _reload_shared()
    assert litellm.request_timeout == 45.0
    assert litellm.num_retries == 3
    # Restaura defaults para não vazar estado para outros testes.
    monkeypatch.delenv("AI4ES_LLM_TIMEOUT")
    monkeypatch.delenv("AI4ES_LLM_NUM_RETRIES")
    _reload_shared()


# --------------------------------------------------------------------------- #
# Frente C: preflight da credencial GitHub Copilot
# --------------------------------------------------------------------------- #
def test_preflight_pula_modelo_nao_copilot(monkeypatch):
    monkeypatch.setenv("ADK_LLM_MODEL", "vertex_ai/gemini")
    chamado = {"auth": False}

    class _Sentinela:
        def get_api_key(self):
            chamado["auth"] = True

    monkeypatch.setattr(
        "litellm.llms.github_copilot.authenticator.Authenticator", _Sentinela
    )
    main._preflight_copilot_credential()
    # Não deve instanciar/consultar o Authenticator para provider não-Copilot.
    assert chamado["auth"] is False


def test_preflight_sucesso_loga_info(monkeypatch, caplog):
    monkeypatch.setenv("ADK_LLM_MODEL", "github_copilot/gpt-4")

    class _AuthOk:
        def get_api_key(self):
            return "token123"

    monkeypatch.setattr(
        "litellm.llms.github_copilot.authenticator.Authenticator", _AuthOk
    )
    with caplog.at_level(logging.INFO, logger=main.logger.name):
        main._preflight_copilot_credential()
    assert any("válida" in r.message for r in caplog.records)


def test_preflight_falha_nao_derruba_e_loga_warning(monkeypatch, caplog):
    monkeypatch.setenv("ADK_LLM_MODEL", "github/gpt-4")

    class _AuthFalha:
        def get_api_key(self):
            raise RuntimeError("credencial expirada")

    monkeypatch.setattr(
        "litellm.llms.github_copilot.authenticator.Authenticator", _AuthFalha
    )
    with caplog.at_level(logging.WARNING, logger=main.logger.name):
        # Não deve propagar exceção.
        main._preflight_copilot_credential()
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings
    assert any("copilot_auth.py" in r.message for r in warnings)
