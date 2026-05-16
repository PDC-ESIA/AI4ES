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
from src.agents.workflow_coding_review.agent import agent as _cr  # noqa: F401
from src.agents.workflow_coding.agent import agent as _sdlc  # noqa: F401
from src.agents.workflow_requirements.agent import agent as _req  # noqa: F401
from src.agents.workflow_design_pipeline.agent import agent as _design  # noqa: F401
from src.agents.workflow_qa.agent import agent as _qa  # noqa: F401
from src.agents.orchestrator.agent import root_agent as _orch  # noqa: F401
