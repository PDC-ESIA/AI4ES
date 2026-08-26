"""Testes do health-check de LLM (shared/preflight.ensure_llm_ready).

Cobre o preflight rodado 1x por prompt: valida credencial + ping real; em
falha, renova o token e revalida até N vezes; se não recuperar, retorna
ok=False com mensagem acionável (o orchestrator então aborta o prompt).

Estratégia: monkeypatch das funções de baixo nível (_validate_credential,
_ping, _force_renew) para manter tudo offline e determinístico.
"""

import shared.preflight as pf


# --------------------------------------------------------------------------- #
# Configuração via env
# --------------------------------------------------------------------------- #
def test_timeout_default_e_override(monkeypatch):
    monkeypatch.delenv("AI4ES_PREFLIGHT_TIMEOUT", raising=False)
    assert pf._preflight_timeout() == 10.0
    monkeypatch.setenv("AI4ES_PREFLIGHT_TIMEOUT", "25")
    assert pf._preflight_timeout() == 25.0
    monkeypatch.setenv("AI4ES_PREFLIGHT_TIMEOUT", "lixo")
    assert pf._preflight_timeout() == 10.0


def test_renew_attempts_default_e_override(monkeypatch):
    monkeypatch.delenv("AI4ES_PREFLIGHT_RENEW_ATTEMPTS", raising=False)
    assert pf._renew_attempts() == 2
    monkeypatch.setenv("AI4ES_PREFLIGHT_RENEW_ATTEMPTS", "5")
    assert pf._renew_attempts() == 5


# --------------------------------------------------------------------------- #
# ensure_llm_ready
# --------------------------------------------------------------------------- #
async def test_pula_provider_nao_copilot(monkeypatch):
    chamado = {"cred": False, "ping": False}
    monkeypatch.setattr(pf, "_validate_credential", lambda: chamado.__setitem__("cred", True))
    monkeypatch.setattr(pf, "_ping", lambda m, t: chamado.__setitem__("ping", True))

    result = await pf.ensure_llm_ready("vertex_ai/gemini")

    assert result.ok is True
    # No-op: não toca credencial nem endpoint.
    assert chamado == {"cred": False, "ping": False}


async def test_healthy_na_primeira_tentativa(monkeypatch):
    chamado = {"cred": 0, "ping": 0, "renew": 0}
    monkeypatch.setattr(pf, "_validate_credential", lambda: chamado.__setitem__("cred", chamado["cred"] + 1))
    monkeypatch.setattr(pf, "_ping", lambda m, t: chamado.__setitem__("ping", chamado["ping"] + 1))
    monkeypatch.setattr(pf, "_force_renew", lambda: chamado.__setitem__("renew", chamado["renew"] + 1))

    result = await pf.ensure_llm_ready("github_copilot/gpt-4")

    assert result.ok is True
    assert chamado["cred"] == 1
    assert chamado["ping"] == 1
    # Sem falha → nenhuma renovação.
    assert chamado["renew"] == 0


async def test_recupera_apos_renovar_token(monkeypatch):
    # Ping falha na 1ª vez (health-check inicial) e passa após a renovação.
    estado = {"ping_calls": 0, "renew": 0}

    def _ping(model, timeout):
        estado["ping_calls"] += 1
        if estado["ping_calls"] == 1:
            raise RuntimeError("endpoint 401")

    monkeypatch.setattr(pf, "_validate_credential", lambda: None)
    monkeypatch.setattr(pf, "_ping", _ping)
    monkeypatch.setattr(pf, "_force_renew", lambda: estado.__setitem__("renew", estado["renew"] + 1))

    result = await pf.ensure_llm_ready("github_copilot/gpt-4")

    assert result.ok is True
    # 1 renovação e 2 pings (inicial que falhou + revalidação ok).
    assert estado["renew"] == 1
    assert estado["ping_calls"] == 2


async def test_aborta_apos_esgotar_tentativas(monkeypatch):
    estado = {"renew": 0}
    monkeypatch.setenv("AI4ES_PREFLIGHT_RENEW_ATTEMPTS", "2")
    monkeypatch.setattr(pf, "_validate_credential", lambda: None)

    def _ping_sempre_falha(model, timeout):
        raise RuntimeError("credencial expirada")

    monkeypatch.setattr(pf, "_ping", _ping_sempre_falha)
    monkeypatch.setattr(pf, "_force_renew", lambda: estado.__setitem__("renew", estado["renew"] + 1))

    result = await pf.ensure_llm_ready("github_copilot/gpt-4")

    assert result.ok is False
    # 2 tentativas de renovação (env), depois aborta.
    assert estado["renew"] == 2
    assert "copilot_auth.py" in result.message
    assert "credencial expirada" in result.message


async def test_renovacao_que_falha_nao_estoura(monkeypatch):
    # _force_renew levanta; ensure_llm_ready deve capturar e retornar ok=False.
    monkeypatch.setenv("AI4ES_PREFLIGHT_RENEW_ATTEMPTS", "1")
    monkeypatch.setattr(pf, "_validate_credential", lambda: (_ for _ in ()).throw(RuntimeError("sem token")))

    def _renew_falha():
        raise RuntimeError("refresh 500")

    monkeypatch.setattr(pf, "_force_renew", _renew_falha)

    result = await pf.ensure_llm_ready("github_copilot/gpt-4")

    assert result.ok is False
    assert "refresh 500" in result.message


async def test_usa_env_model_quando_nao_passado(monkeypatch):
    monkeypatch.setenv("ADK_LLM_MODEL", "github/gpt-4")
    chamado = {"cred": 0}
    monkeypatch.setattr(pf, "_validate_credential", lambda: chamado.__setitem__("cred", chamado["cred"] + 1))
    monkeypatch.setattr(pf, "_ping", lambda m, t: None)

    result = await pf.ensure_llm_ready()

    assert result.ok is True
    assert chamado["cred"] == 1
