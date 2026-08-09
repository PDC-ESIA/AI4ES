"""Testes da configuração por ambiente do loop de codificação (coding_review).

Cobre `workflow_coding_review/config.py`:
- defaults quando as envs estão ausentes (300 / 3);
- envs novas respeitadas (`AI4ES_LOOP_MAX_ITERATIONS` / `AI4ES_LOOP_PATIENCE`);
- valor inválido → cai no default (sem explodir);
- env ANTIGA `AI4ES_MAX_LOOP_ITERATIONS`: emite `DeprecationWarning` e é
  IGNORADA (migração forçada, sem fallback silencioso);
- ausência da env antiga não emite `DeprecationWarning`.
"""

import importlib

import pytest

_ENV_KEYS = (
    "AI4ES_LOOP_MAX_ITERATIONS",
    "AI4ES_LOOP_PATIENCE",
    "AI4ES_MAX_LOOP_ITERATIONS",
)


def _reload_config(monkeypatch, **env):
    """Limpa as envs relevantes, aplica o cenário e recarrega o módulo config."""
    for chave in _ENV_KEYS:
        monkeypatch.delenv(chave, raising=False)
    for chave, valor in env.items():
        monkeypatch.setenv(chave, valor)
    from src.agents.workflow_coding_review import config

    return importlib.reload(config)


# ===========================================================================
# Defaults e envs novas
# ===========================================================================


def test_defaults_quando_ausentes(monkeypatch):
    cfg = _reload_config(monkeypatch)
    assert cfg.LOOP_MAX_ITERATIONS == 300
    assert cfg.LOOP_PATIENCE == 3


def test_envs_novas_respeitadas(monkeypatch):
    cfg = _reload_config(
        monkeypatch,
        AI4ES_LOOP_MAX_ITERATIONS="42",
        AI4ES_LOOP_PATIENCE="7",
    )
    assert cfg.LOOP_MAX_ITERATIONS == 42
    assert cfg.LOOP_PATIENCE == 7


def test_valor_invalido_cai_no_default(monkeypatch):
    cfg = _reload_config(
        monkeypatch,
        AI4ES_LOOP_MAX_ITERATIONS="abc",
        AI4ES_LOOP_PATIENCE="",
    )
    assert cfg.LOOP_MAX_ITERATIONS == 300
    assert cfg.LOOP_PATIENCE == 3


# ===========================================================================
# Deprecação forçada da env antiga
# ===========================================================================


def test_env_antiga_emite_deprecation_e_e_ignorada(monkeypatch):
    """`AI4ES_MAX_LOOP_ITERATIONS` está obsoleta: avisa e IGNORA o valor."""
    for chave in _ENV_KEYS:
        monkeypatch.delenv(chave, raising=False)
    # Valor "atrativo" na env antiga — deve ser ignorado, não vira o teto.
    monkeypatch.setenv("AI4ES_MAX_LOOP_ITERATIONS", "999")

    from src.agents.workflow_coding_review import config

    with pytest.warns(DeprecationWarning, match="AI4ES_MAX_LOOP_ITERATIONS"):
        cfg = importlib.reload(config)

    assert cfg.LOOP_MAX_ITERATIONS == 300  # valor da env antiga foi IGNORADO


def test_env_antiga_nao_sobrepoe_env_nova(monkeypatch):
    """Mesmo com a env antiga presente, a env NOVA é quem vale."""
    for chave in _ENV_KEYS:
        monkeypatch.delenv(chave, raising=False)
    monkeypatch.setenv("AI4ES_MAX_LOOP_ITERATIONS", "999")
    monkeypatch.setenv("AI4ES_LOOP_MAX_ITERATIONS", "50")

    from src.agents.workflow_coding_review import config

    with pytest.warns(DeprecationWarning):
        cfg = importlib.reload(config)

    assert cfg.LOOP_MAX_ITERATIONS == 50


def test_sem_env_antiga_nao_avisa(monkeypatch, recwarn):
    cfg = _reload_config(monkeypatch)
    deprecacoes = [w for w in recwarn.list if issubclass(w.category, DeprecationWarning)]
    assert deprecacoes == []
    assert cfg.LOOP_MAX_ITERATIONS == 300
