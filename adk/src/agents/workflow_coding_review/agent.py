"""Workflow coding_review: pipeline enxuto de codificação com revisão.

Instancia agentes dedicados (mesmo prompt/tools dos roles) para evitar
conflito de parent com o sdlc_pipeline.

Isolamento: ao importar este módulo, o workspace_output/ é inicializado
e todas as tools de filesystem/git são bound aos subdirectórios do
workspace — o coder NÃO escreve no repo principal.
"""

import os

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool

from src.agents.requirements import prompt as req_prompt
from src.agents.requirements import schemas as req_schemas
from src.agents.coder import prompt as coder_prompt
from src.agents.reviewer import prompt as reviewer_prompt
from shared.agent_factory import _bind_tool_to_workspace
from shared.workspace import (
    get_agent_workspace,
    get_workspace_root,
    init_workspace,
)
from shared.tools import (
    tool_criar_arquivo,
    tool_git_add,
    tool_git_commit,
    tool_git_checkout,
    tool_ler_arquivo,
    tool_substituir_trecho,
    tool_ler_diff,
    tool_salvar_relatorio,
    tool_salvar_artefato_requisito,
    gerar_doubt_artifact,
    run_slicer,
    ler_chunk,
)

# Inicializa o workspace na importação. O orchestrator cria sessões isoladas
# por pipeline, mas todas compartilham o mesmo workspace_output em disco.
_WORKSPACE_ROOT = str(init_workspace())
_REQ_WS = str(get_agent_workspace("requirements"))
_CODER_WS = str(get_agent_workspace("coder"))
_REVIEW_WS = str(get_agent_workspace("reviewer"))


def _bind(tool, agent_ws):
    return _bind_tool_to_workspace(tool, agent_ws, _WORKSPACE_ROOT)

# NOTA: as tools originais `tool_ler_prd_arquivo_adk` e `tool_gerar_doubt_artifact_adk`
# viviam em adk/agents/roles/requirements/tools_requirements.py e foram removidas na
# consolidacao com Time 1 (refatoracao da arquitetura de requisitos).
# Substituicao funcional: tool_ler_arquivo (leitura generica) + gerar_doubt_artifact
# (geracao de doubt artifact via shared.tools). Donos podem refinar se preciso.

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

_requirements = LlmAgent(
    model=_model,
    name="cr_requirements_agent",
    description=req_prompt.description,
    instruction=req_prompt.instruction,
    # output_schema + tools são mutuamente exclusivos em ADK
    # (https://google.github.io/adk-docs/agents/llm-agents/#structured-output).
    # Mantemos tools (precisamos de tool_ler_arquivo + gerar_doubt_artifact)
    # e abandonamos output_schema. O downstream parseia o texto via output_key.
    output_key="requirements",
    tools=[
        _bind(FunctionTool(tool_ler_arquivo), _REQ_WS),
        _bind(FunctionTool(gerar_doubt_artifact), _REQ_WS),
        _bind(FunctionTool(tool_salvar_artefato_requisito), _REQ_WS),
        FunctionTool(run_slicer),
        FunctionTool(ler_chunk),
    ],
)

_CODER_INSTRUCTION = f"""
# PERFIL
Você é um Engenheiro de Software Sênior. Sua única função é IMPLEMENTAR código
funcional a partir dos requisitos recebidos.

# WORKSPACE
Todos os arquivos que você criar serão salvos automaticamente em
`{_CODER_WS}/`. Use caminhos RELATIVOS (ex: `app/main.py`, `tests/test_x.py`).
NÃO USE git, NÃO crie branches, NÃO faça commits. Você não tem essas ferramentas
disponíveis e tentar usá-las causa erro fatal.

# FERRAMENTAS DISPONÍVEIS (APENAS ESTAS — não invente outras)
- `tool_criar_arquivo(caminho, conteudo)`: cria/sobrescreve arquivo (caminho relativo).
- `tool_ler_arquivo(caminho)`: lê arquivo já existente no workspace.
- `tool_substituir_trecho(caminho, trecho_antigo, trecho_novo)`: edita trecho de arquivo existente.

# DIRETRIZES
1. **Modularidade**: arquivos com responsabilidade única (SRP). Divida se passar de ~200 linhas.
2. **ESTRUTURA OBRIGATÓRIA DE PROJETO PYTHON** (para app FastAPI/Flask/CLI):
   - Raiz do workspace contém: `requirements.txt`, `conftest.py` (vazio basta), `pyproject.toml` opcional.
   - Pacote principal em `app/` com `app/__init__.py` (vazio) e `app/main.py`.
   - Testes em `tests/` com `tests/__init__.py` (vazio) e `tests/test_*.py`.
   - Imports de teste SEMPRE absolutos a partir da raiz (`from app.main import app`), nunca `from main import app`.
   - Sem `__init__.py` na raiz do workspace.
   - Para CLI/script único: dispense `app/`, mas mantenha `tests/__init__.py` e `conftest.py` na raiz.

   Os arquivos `__init__.py` e `conftest.py` são OBRIGATÓRIOS mesmo vazios — sem eles, `pytest` falha
   em coletar testes com erro `ModuleNotFoundError: No module named 'app'`. Crie-os explicitamente
   via `tool_criar_arquivo`.

   Estrutura padrão para apps FastAPI:
   - `app/models.py` (SQLAlchemy ou Pydantic) — se aplicável
   - `app/routers/<recurso>.py` (rotas por recurso) — se aplicável
   - `app/templates/*.html` (Jinja2) — se aplicável
3. **Qualidade**: tratamento de erros, type hints, código executável.
4. **Não pare cedo**: implemente TODOS os arquivos necessários para o feature funcionar.

# FLUXO
1. Leia os requisitos fornecidos.
2. Liste mentalmente os arquivos que precisa criar.
3. Crie cada arquivo via `tool_criar_arquivo` em sequência.
4. Retorne resumo: lista de arquivos criados + breve descrição de cada um.

# SAÍDA FINAL
Texto curto (não JSON) listando arquivos criados. Sem perguntas, sem dúvidas.
"""

_coder = LlmAgent(
    model=_model,
    name="cr_coder_agent",
    description="Implementa código funcional a partir de requisitos, sem git.",
    instruction=_CODER_INSTRUCTION,
    output_key="implementation",
    tools=[
        _bind(FunctionTool(tool_criar_arquivo), _CODER_WS),
        _bind(FunctionTool(tool_ler_arquivo), _CODER_WS),
        _bind(FunctionTool(tool_substituir_trecho), _CODER_WS),
    ],
)

_reviewer = LlmAgent(
    model=_model,
    name="cr_review_agent",
    description=reviewer_prompt.description,
    instruction=(
        reviewer_prompt.instruction
        + f"\n\n# WORKSPACE\n"
        + f"Os arquivos a revisar estão em `{_CODER_WS}/`. "
        + f"Como o ambiente não é git, use tool_ler_arquivo (apontando para `{_CODER_WS}/<file>`) "
        + f"para ler cada arquivo. Salve o relatório em `{_REVIEW_WS}/` via tool_salvar_relatorio."
    ),
    output_key="review",
    tools=[
        FunctionTool(tool_ler_arquivo),
        _bind(FunctionTool(tool_salvar_relatorio), _REVIEW_WS),
    ],
)

agent = SequentialAgent(
    name="coding_review_pipeline",
    description=(
        "Pipeline enxuto de codificação com revisão: "
        "requisitos → codificação → revisão."
    ),
    sub_agents=[_requirements, _coder, _reviewer],
)
