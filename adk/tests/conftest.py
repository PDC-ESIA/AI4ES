"""conftest.py global da suite de testes do ADK.

A suite é organizada em 2 camadas de validação de sistemas agênticos
(ver `tests/README.md` para o racional completo, baseado em MASEval,
na survey da ACL 2026 sobre avaliação de agentes LLM e em "Testing
LLM-Based Agents"):

    1. `unit/`        — testes determinísticos (unit + integração leve)
       que NÃO dependem de julgamento de qualidade: schemas Pydantic,
       ferramentas, workspace, harness Docker, orquestração.
    2. `integration/` — validam a SEQUÊNCIA de decisões dos agentes
       (trajectory evaluation): quem chamou o quê, em que ordem, com
       coleta de trace estruturado (canonical + raw layer).

Ortogonal a essas 2 camadas há uma dimensão de escopo por agente:
`coder_isolado/` reúne, em subpastas próprias, os testes que exercitam
exclusivamente o pipeline `workflow_coding_review`: `infraestrutura/` e
`trajetoria/` replicam a mesma separação de camada de cima, 100%
determinísticas; `evals/` (Camada 3) e `sandbox/` (Camada 4) usam LLM
real (GitHub Copilot), com skip automático sem credencial e sem rodar no
CI padrão. Ver `tests/README.md` para o racional completo.

Este conftest é carregado antes de qualquer coleta de teste e cuida de
quatro responsabilidades transversais a todas as camadas/escopos:

- registrar os markers usados para selecionar camadas via
  `pytest -m <marker>`;
- pré-carregar (pré-cachear) os módulos de agente que dependem de
  Pydantic, para blindar a suite contra o teste `test_git_tools.py`
  (Camada 1), que substitui `pydantic.BaseModel` por `object` em
  `sys.modules` para isolar testes de git. Sem o pré-cache, qualquer
  teste coletado *depois* dele — em qualquer camada — poderia importar
  módulos de agente com um `BaseModel` corrompido;
- restaurar `pydantic.BaseModel`/`Field`/`field_validator` reais logo
  após a coleta terminar (`pytest_collection_finish`), desfazendo a
  sabotagem de `test_git_tools.py` incondicionalmente — não só quando
  esse arquivo é selecionado para execução. Ver docstring do hook para
  o porquê de precisar ser um hook de coleta, não uma fixture;
- neutralizar o health-check de LLM do orchestrator (`ensure_llm_ready`)
  durante toda a suite, para que nenhum teste dependa de rede real ou
  credencial configurada — o comportamento do preflight em si é coberto
  isoladamente por `tests/unit/test_preflight_healthcheck.py`.
"""

from __future__ import annotations

import os as _os
import sys as _sys

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
        "markers", "integration: testes que executam ferramentas externas (ruff, bandit) — requerem instalação no ambiente"
    )
    config.addinivalue_line(
        "markers", "infraestrutura: Camada 1 — testes determinísticos (unit/integração leve): schemas, tools, workspace, harness Docker, orquestração"
    )
    config.addinivalue_line(
        "markers", "trajetoria: Camada 2 — validação da sequência de decisões dos agentes (trajectory evaluation), com coleta de trace estruturado"
    )
    config.addinivalue_line(
        "markers", "coder_isolado: testes que exercitam exclusivamente o pipeline workflow_coding_review"
    )
    config.addinivalue_line(
        "markers", "evals: Camada 3 — avaliação de qualidade com LLM real (custo de API, não roda no CI padrão)"
    )
    config.addinivalue_line(
        "markers", "sandbox: Camada 4 — pipeline completo ponta-a-ponta com LLM real (custo de API, não roda no CI padrão)"
    )

# ---------------------------------------------------------------------------
# Pré-cache de módulos ADK/Pydantic
# ---------------------------------------------------------------------------
# Nenhum destes imports é exercitado diretamente pelos testes — servem
# apenas para popular `sys.modules` com o Pydantic real ANTES que
# `unit/test_git_tools.py` o substitua por um stub.

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
# unit/test_git_tools.py stubar pydantic.BaseModel = object — para
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
# Restaura pydantic real após a sabotagem de unit/test_git_tools.py
# ---------------------------------------------------------------------------

def pytest_collection_finish(session: pytest.Session) -> None:
    """Restaura `pydantic.BaseModel`/`Field`/`field_validator` após a coleta.

    Por que um hook de COLETA, e não uma fixture (mesmo autouse): a
    sabotagem em `unit/test_git_tools.py` roda de forma incondicional no
    IMPORT do módulo (nível de módulo, fora de qualquer função de teste) —
    e a fase de coleta do pytest SEMPRE importa os 439 arquivos de teste
    para descobrir os testes neles, **independente de qual seleção por
    `-m` será aplicada na execução**. Uma fixture só dispara quando um
    teste do módulo em que ela vive é de fato selecionado E executado —
    com `pytest -m evals`, por exemplo, `test_git_tools.py` inteiro é
    deselecionado da execução, então uma fixture de restauração ali nunca
    rodaria, mas a sabotagem (que já aconteceu na coleta) permaneceria.
    A restauração precisa da mesma garantia "sempre roda" que a sabotagem
    tem — daí um hook de sessão disparado logo após `pytest_collection_finish`,
    antes de qualquer teste (de qualquer marker) executar.

    Passivo de propósito: só restaura SE `tests.unit.test_git_tools` já
    foi importado (via `sys.modules`, sem importar o módulo aqui) — do
    contrário, uma seleção que nunca toca esse arquivo (ex.: `pytest
    tests/coder_isolado/evals/`) faria este hook IMPORTAR o módulo e
    disparar a sabotagem pela primeira vez, o que seria pior que o
    problema original.

    Busca por SUFIXO do nome qualificado (não a chave exata
    `"tests.unit.test_git_tools"`): o projeto tem um `adk/__init__.py` na
    raiz, então o modo de import "prepend" do pytest registra o módulo em
    `sys.modules` como `adk.tests.unit.test_git_tools` (prefixo extra
    `adk.`, com a raiz de import sendo o diretório PAI de `adk/`) — não a
    chave "óbvia" sem prefixo. Buscar por sufixo é robusto a isso sem
    depender de um detalhe de configuração de import alheio a este hook.
    """
    modulo = next(
        (
            mod for nome, mod in _sys.modules.items()
            if nome.endswith("tests.unit.test_git_tools")
        ),
        None,
    )
    originais = getattr(modulo, "_pydantic_originais", None)
    if not originais:
        return
    pydantic_mod = _sys.modules.get("pydantic")
    if pydantic_mod is None:
        return
    for atributo, valor in originais.items():
        setattr(pydantic_mod, atributo, valor)


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
    `tests/unit/test_preflight_healthcheck.py`.
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
    """`TraceCollector` vazio, disponível para qualquer camada/escopo.

    `tests/coder_isolado/conftest.py` expõe uma versão mais completa (com
    dump automático em JSON ao final do teste), usada pelos testes de
    trajetória do coding_review; esta fixture global serve para testes
    fora desse escopo que só precisam registrar alguns eventos pontualmente
    (ex.: um teste de infraestrutura que quer documentar a ordem de
    chamadas de tool sem todo o aparato da Camada 2).
    """
    from tests.fixtures.trace_helpers import TraceCollector

    return TraceCollector()

# ---------------------------------------------------------------------------
# Aplicação automática dos markers de camada, por pasta
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Marca cada teste com sua camada e, se aplicável, com `coder_isolado`.

    Os arquivos de teste não precisam de marker explícito — este hook
    deriva os markers das partes do caminho do teste, permitindo selecionar
    camada e/ou escopo via `pytest -m infraestrutura` / `-m trajetoria` /
    `-m coder_isolado` (combináveis: `-m "infraestrutura and coder_isolado"`)
    mesmo quando a suite completa é coletada a partir da raiz.

    Mapeamento:
    - `tests/unit/`                        → `infraestrutura`
    - `tests/integration/`                 → `trajetoria`
    - `tests/coder_isolado/infraestrutura/` → `infraestrutura` + `coder_isolado`
    - `tests/coder_isolado/trajetoria/`     → `trajetoria` + `coder_isolado`
    - `tests/coder_isolado/evals/`          → `evals` + `coder_isolado`
    - `tests/coder_isolado/sandbox/`        → `sandbox` + `coder_isolado`
    """
    for item in items:
        partes = item.nodeid.replace("\\", "/").split("/")

        if "coder_isolado" in partes:
            item.add_marker(pytest.mark.coder_isolado)
            if "infraestrutura" in partes:
                item.add_marker(pytest.mark.infraestrutura)
            elif "trajetoria" in partes:
                item.add_marker(pytest.mark.trajetoria)
            elif "evals" in partes:
                item.add_marker(pytest.mark.evals)
            elif "sandbox" in partes:
                item.add_marker(pytest.mark.sandbox)
        elif "unit" in partes:
            item.add_marker(pytest.mark.infraestrutura)
        elif "integration" in partes:
            item.add_marker(pytest.mark.trajetoria)