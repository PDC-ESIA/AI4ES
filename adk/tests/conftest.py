"""conftest.py global da suite de testes do ADK.

A suite é organizada em 2 camadas de validação de sistemas agênticos
(ver `tests/README.md` para o racional completo, baseado em MASEval,
na survey da ACL 2026 sobre avaliação de agentes LLM e em "Testing
LLM-Based Agents"):

    1. `1_infraestrutura/` — testes determinísticos (unit + integração leve)
       que NÃO dependem de julgamento de qualidade: schemas Pydantic,
       ferramentas, workspace, harness Docker, orquestração.
    2. `2_trajetoria/`      — validam a SEQUÊNCIA de decisões dos agentes
       (trajectory evaluation): quem chamou o quê, em que ordem, com
       coleta de trace estruturado (canonical + raw layer).
    
Este conftest é carregado antes de qualquer coleta de teste e cuida de
duas responsabilidades transversais às 2 camadas:

- registrar os markers usados para selecionar camadas via
  `pytest -m <marker>`;
- pré-carregar (pré-cachear) os módulos de agente que dependem de
  Pydantic, para blindar a suite contra o teste `test_git_tools.py`
  (Camada 1), que substitui `pydantic.BaseModel` por `object` em
  `sys.modules` para isolar testes de git. Sem o pré-cache, qualquer
  teste coletado *depois* dele — em qualquer camada — poderia importar
  módulos de agente com um `BaseModel` corrompido.
"""

from __future__ import annotations

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


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Marca cada teste coletado com a camada correspondente à sua pasta.

    Sem isso, `pytest -m infraestrutura`/`-m trajetoria` só selecionaria
    testes marcados manualmente — o que a suite hoje não faz, contando com
    seleção por caminho (`pytest tests/1_infraestrutura/`). Este hook deriva
    o marker automaticamente de `1_infraestrutura/` ou `2_trajetoria/` no
    caminho do arquivo, para que a seleção por marker (usada no exemplo de
    CI do README) funcione sem exigir marcação manual em cada teste.
    """
    for item in items:
        partes = item.path.parts
        if "1_infraestrutura" in partes:
            item.add_marker(pytest.mark.infraestrutura)
        elif "2_trajetoria" in partes:
            item.add_marker(pytest.mark.trajetoria)


# ---------------------------------------------------------------------------
# Pré-cache de módulos ADK/Pydantic
# ---------------------------------------------------------------------------
# Nenhum destes imports é exercitado diretamente pelos testes — servem
# apenas para popular `sys.modules` com o Pydantic real ANTES que
# `1_infraestrutura/test_git_tools.py` o substitua por um stub.

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


# ---------------------------------------------------------------------------
# Fixture transversal de coleta de trace
# ---------------------------------------------------------------------------

@pytest.fixture
def trace_collector():
    """`TraceCollector` vazio, disponível para qualquer camada.

    A Camada 2 (`2_trajetoria/conftest.py`) expõe uma versão mais completa
    (com dump automático em JSON ao final do teste); esta fixture global
    serve para testes fora dessa camada que só precisam registrar alguns
    eventos pontualmente (ex.: um teste de infraestrutura que quer
    documentar a ordem de chamadas de tool sem todo o aparato da Camada 2).
    """
    from tests.fixtures.trace_helpers import TraceCollector

    return TraceCollector()
