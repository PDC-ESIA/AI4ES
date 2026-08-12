"""conftest.py — fixtures para a suíte de testes de integração."""

import pytest

from shared.preflight import PreflightResult


@pytest.fixture(autouse=True)
def _stub_llm_preflight(monkeypatch):
    """Neutraliza o health-check de LLM do orchestrator nos testes de integração.

    ensure_llm_ready faria chamadas de rede reais (validação de credencial +
    ping ao endpoint). Substituímos por um no-op ok=True para manter os testes
    determinísticos e offline; o comportamento do preflight é coberto por
    tests/unit/test_preflight_healthcheck.py.
    """

    async def _ok(model=None):
        return PreflightResult(ok=True)

    monkeypatch.setattr(
        "src.agents.orchestrator.agent.ensure_llm_ready", _ok, raising=False
    )
