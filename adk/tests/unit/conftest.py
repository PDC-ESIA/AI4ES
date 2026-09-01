"""conftest.py — fixtures e pre-importações para a suite de testes unitários.

test_git_tools.py estufa pydantic.BaseModel = object no sys.modules para
isolar os testes de git. Isso corrompe módulos importados posteriormente que
dependem do Pydantic real (ex.: schemas dos agentes e ADK LlmAgent).

Solução: pre-importar todos os módulos de agente que usam BaseModel antes
que qualquer test module seja coletado. conftest.py é executado pelo pytest
antes da coleta, então os módulos ficam cacheados no sys.modules com o
BaseModel correto.

collect_ignore: exclui arquivos com problemas pré-existentes:
- test_filesystem_tools.py — conflito de merge não resolvido (SyntaxError)
- test_geracao_condicional.py — importa adk.agents.roles.* (caminho removido
  na consolidação dos Times)
"""

collect_ignore = [
    "test_filesystem_tools.py",
    "test_geracao_condicional.py",
]

# Pré-cache de todos os módulos de agente com dependência em pydantic/ADK.
# Nenhum desses imports é executado durante os testes — servem apenas para
# popular sys.modules antes que test_git_tools.py substitua pydantic.BaseModel.

from src.agents.requirements import schemas as _req_schemas  # noqa: F401
from src.agents.workflow_coding_review.reviewer import schemas as _rev_schemas  # noqa: F401
from shared.tools.coding_tools import harness_schemas as _harness_schemas  # noqa: F401
from src.agents.implementation_validator import schemas as _implval_schemas  # noqa: F401
from src.agents.workflow_coding_review.context_engineer import schemas as _ce_schemas  # noqa: F401
from shared.tools.coding_tools.context_engineer_tools import tool_salvar_task_cr  # noqa: F401
from src.agents.workflow_coding_review.agent import agent as _cr  # noqa: F401
from src.agents.workflow_requirements.agent import agent as _req  # noqa: F401
from src.agents.workflow_design_pipeline.agent import agent as _design  # noqa: F401
from src.agents.workflow_qa.agent import agent as _qa  # noqa: F401
from src.agents.orchestrator.agent import root_agent as _orch  # noqa: F401

# app.main dispara a cadeia de import da ADK (google.adk.cli.fast_api →
# evaluation) e cria a FastAPI app no import. Pré-importamos aqui — antes de
# test_git_tools.py stubar pydantic.BaseModel = object — para cachear esses
# módulos com o Pydantic real. Forçamos ADK_LLM_MODEL para um provider
# não-Copilot para que o preflight de credencial executado no import retorne
# cedo, sem tentar autenticação de rede; o valor original é restaurado depois.
import os as _os  # noqa: E402

_prev_model = _os.environ.get("ADK_LLM_MODEL")
_os.environ["ADK_LLM_MODEL"] = "none/x"
try:
    import app.main as _main  # noqa: F401
finally:
    if _prev_model is None:
        _os.environ.pop("ADK_LLM_MODEL", None)
    else:
        _os.environ["ADK_LLM_MODEL"] = _prev_model


import pytest  # noqa: E402
from shared.preflight import PreflightResult  # noqa: E402


@pytest.fixture(autouse=True)
def _stub_llm_preflight(monkeypatch):
    """Neutraliza o health-check de LLM do orchestrator nos testes unitários.

    ensure_llm_ready faria chamadas de rede reais (validação de credencial +
    ping ao endpoint). Substituímos por um no-op ok=True para manter os testes
    determinísticos e offline; o comportamento do preflight em si é coberto por
    test_preflight_healthcheck.py chamando shared.preflight diretamente.
    """

    async def _ok(model=None):
        return PreflightResult(ok=True)

    monkeypatch.setattr(
        "src.agents.orchestrator.agent.ensure_llm_ready", _ok, raising=False
    )
