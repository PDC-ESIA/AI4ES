"""conftest.py global da suite de testes do ADK.

A suite é organizada em 2 camadas de validação de sistemas agênticos
(ver `tests/README.md` para o racional completo, baseado em MASEval,
na survey da ACL 2026 sobre avaliação de agentes LLM e em "Testing
LLM-Based Agents"):

    1. `infraestrutura/` — testes determinísticos (unit + integração leve)
       que NÃO dependem de julgamento de qualidade: schemas Pydantic,
       ferramentas, workspace, harness Docker, orquestração.
    2. `trajetoria/`      — validam a SEQUÊNCIA de decisões dos agentes
       (trajectory evaluation): quem chamou o quê, em que ordem, com
       coleta de trace estruturado (canonical + raw layer).

Este conftest é carregado antes de qualquer coleta de teste e cuida de
três responsabilidades transversais às 2 camadas:

- registrar os markers usados para selecionar camadas via
  `pytest -m <marker>`;
- pré-carregar (pré-cachear) os módulos de agente que dependem de
  Pydantic, para blindar a suite contra o teste `test_git_tools.py`
  (Camada 1), que substitui `pydantic.BaseModel` por `object` em
  `sys.modules` para isolar testes de git. Sem o pré-cache, qualquer
  teste coletado *depois* dele — em qualquer camada — poderia importar
  módulos de agente com um `BaseModel` corrompido;
- neutralizar o health-check de LLM do orchestrator (`ensure_llm_ready`)
  durante toda a suite, para que nenhum teste dependa de rede real ou
  credencial configurada — o comportamento do preflight em si é coberto
  isoladamente por `tests/infraestrutura/test_preflight_healthcheck.py`.
"""

from __future__ import annotations

import os as _os

import pytest


# ---------------------------------------------------------------------------
# Markers das 2 camadas
# ---------------------------------------------------------------------------
# Também declarados em pytest.ini (fonte "oficial" lida por ferramentas
# externas); registrados aqui também via addinivalue_line para que a suite
# funcione mesmo se for coletada com um rootdir/config diferente.

def pytest_configure(config: pytest.Config) -> None:
    """Registra os markers de camada, evitando warnings de marker desconhecido."""
    config.addinivalue_line(
        "markers", "infraestrutura: Camada 1 — testes determinísticos (unit/integração leve)"
    )
    config.addinivalue_line(
        "markers", "trajetoria: Camada 2 — validação da sequência de decisões dos agentes"
    )

# ---------------------------------------------------------------------------
# Pré-cache de módulos ADK/Pydantic
# ---------------------------------------------------------------------------
# Nenhum destes imports é exercitado diretamente pelos testes — servem
# apenas para popular `sys.modules` com o Pydantic real ANTES que
# `infraestrutura/test_git_tools.py` o substitua por um stub.

from src.agents.requirements import schemas as _req_schemas  # noqa: F401,E402
from src.agents.workflow_coding_review.reviewer import schemas as _rev_schemas  # noqa: F401,E402
from shared.tools.coding_tools import harness_schemas as _harness_schemas  # noqa: F401,E402
from src.agents.implementation_validator import schemas as _implval_schemas  # noqa: F401,E402
from src.agents.workflow_coding_review.context_engineer import schemas as _ce_schemas  # noqa: F401,E402
from shared.tools.coding_tools.context_engineer_tools import tool_salvar_task as _tool_salvar_task  # noqa: F401,E402
from src.agents.workflow_coding_review.agent import agent as _cr_agent  # noqa: F401,E402
from src.agents.workflow_requirements.agent import agent as _req_agent  # noqa: F401,E402
from src.agents.workflow_design_pipeline.agent import agent as _design_agent  # noqa: F401,E402
from src.agents.workflow_qa.agent import agent as _qa_agent  # noqa: F401,E402
from src.agents.orchestrator.agent import root_agent as _orch_agent  # noqa: F401,E402

# app.main dispara a cadeia de import da ADK (google.adk.cli.fast_api →
# evaluation) e cria a FastAPI app no import. Pré-importamos aqui — antes de
# infraestrutura/test_git_tools.py stubar pydantic.BaseModel = object — para
# cachear esses módulos com o Pydantic real. Forçamos ADK_LLM_MODEL para um
# provider não-Copilot para que o preflight de credencial executado no
# import retorne cedo, sem tentar autenticação de rede; o valor original é
# restaurado logo em seguida.
_prev_model = _os.environ.get("ADK_LLM_MODEL")
_os.environ["ADK_LLM_MODEL"] = "none/x"
try:
    import app.main as _main  # noqa: F401
finally:
    if _prev_model is None:
        _os.environ.pop("ADK_LLM_MODEL", None)
    else:
        _os.environ["ADK_LLM_MODEL"] = _prev_model


# ---------------------------------------------------------------------------
# Neutraliza chamadas de rede reais (preflight de LLM)
# ---------------------------------------------------------------------------

from shared.preflight import PreflightResult  # noqa: E402


@pytest.fixture(autouse=True)
def _stub_llm_preflight(monkeypatch: pytest.MonkeyPatch):
    """Neutraliza o health-check de LLM do orchestrator em toda a suite.

    `ensure_llm_ready` faria chamadas de rede reais (validação de credencial
    + ping ao endpoint). Substituímos por um no-op ok=True para manter os
    testes determinísticos e offline, nas 2 camadas; o comportamento do
    preflight em si é coberto isoladamente por
    `tests/infraestrutura/test_preflight_healthcheck.py`.
    """

    async def _ok(model=None):
        return PreflightResult(ok=True)

    monkeypatch.setattr(
        "src.agents.orchestrator.agent.ensure_llm_ready", _ok, raising=False
    )


# ---------------------------------------------------------------------------
# Fixture transversal de coleta de trace
# ---------------------------------------------------------------------------

@pytest.fixture
def trace_collector():
    """`TraceCollector` vazio, disponível para qualquer camada.

    A Camada 2 (`trajetoria/conftest.py`) expõe uma versão mais completa
    (com dump automático em JSON ao final do teste); esta fixture global
    serve para testes fora dessa camada que só precisam registrar alguns
    eventos pontualmente (ex.: um teste de infraestrutura que quer
    documentar a ordem de chamadas de tool sem todo o aparato da Camada 2).
    """
    from tests.fixtures.trace_helpers import TraceCollector

    return TraceCollector()

# ---------------------------------------------------------------------------
# Aplicação automática dos markers de camada, por pasta
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Marca cada teste com `infraestrutura` ou `trajetoria` conforme a pasta.

    Os arquivos de teste não precisam de `@pytest.mark.infraestrutura` (ou
    `trajetoria`) explícito — este hook aplica o marker correspondente com
    base nas partes do caminho do teste, permitindo selecionar a camada
    inteira via `pytest -m infraestrutura` / `pytest -m trajetoria` mesmo
    quando a suite completa é coletada a partir da raiz.
    """
    for item in items:
        partes = item.nodeid.replace("\\", "/").split("/")
        if "infraestrutura" in partes:
            item.add_marker(pytest.mark.infraestrutura)
        elif "trajetoria" in partes:
            item.add_marker(pytest.mark.trajetoria)