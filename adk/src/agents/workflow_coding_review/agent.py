"""Workflow coding_review: pipeline enxuto de codificação com revisão.

Instancia agentes dedicados (mesmo prompt/tools dos roles) para evitar
conflito de parent com o sdlc_pipeline.

Isolamento: ao importar este módulo, o workspace_output/ é inicializado
e todas as tools de filesystem/git são bound aos subdirectórios do
workspace — o coder NÃO escreve no repo principal.
"""

import os
from pathlib import Path

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


def _discover_coder_files() -> str:
    """Lista arquivos no _CODER_WS (relativo), formato bullet, pra injetar no prompt do reviewer.

    Executado no momento da invocação do agente (via InstructionProvider) — não no import.
    Quando o coder ainda não rodou, retorna marker informativo.
    """
    coder_dir = Path(_CODER_WS)
    if not coder_dir.exists():
        return "- (nenhum arquivo ainda — coder será executado antes de você)"
    files = sorted(
        str(p.relative_to(coder_dir))
        for p in coder_dir.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )
    if not files:
        return "- (workspace vazio)"
    return "\n".join(f"- {f}" for f in files)


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

_REVIEWER_INSTRUCTION_TEMPLATE = """
# PERFIL
Você é um Engenheiro de Software Sênior responsável por revisar código produzido por outro agente.
Não há ambiente git neste pipeline. Você revisa arquivos diretamente no workspace.

# WORKSPACE
Os arquivos a revisar estão em `__CODER_WS__/` (caminho absoluto do disco).
Para você, use caminhos RELATIVOS — tool_ler_arquivo resolve automaticamente.

# ARQUIVOS A REVISAR
__FILES__

# FERRAMENTAS DISPONÍVEIS
- tool_ler_arquivo(caminho): lê arquivo do workspace do coder (path relativo).
- tool_salvar_relatorio(nome_arquivo, conteudo): salva o relatório no workspace de review.

# FLUXO OBRIGATÓRIO
1. Para cada arquivo da lista acima, chame tool_ler_arquivo(caminho).
2. Avalie em 4 dimensões: COMPLETUDE, ARQUITETURA, CORRETUDE, TESTES.
   - Completude: arquivos esperados foram criados? tests/ existe? requirements.txt?
   - Arquitetura: SRP, separação de concerns, acoplamento.
   - Corretude: bugs visíveis, edge cases, segurança.
   - Testes: existem? cobrem cenários relevantes? assertions significativas?
3. **OBRIGATÓRIO ao fim**: chame tool_salvar_relatorio(nome_arquivo='verificacao_revisao.md', conteudo=<markdown>).
   Sem essa chamada, sua revisão NÃO é entregue — o pipeline falha mesmo que você produza texto.

# REGRAS DE DECISÃO
- Qualquer issue critical → status="BLOQUEADO"
- Apenas warning/info → status="APROVADO" com ressalvas
- Sem issues → status="APROVADO"

# SAÍDA FINAL (texto retornado pelo agente, depois de salvar)
JSON único:
{
  "status": "APROVADO" | "BLOQUEADO",
  "issues": [{"severity": "critical|warning|info", "description": "...", "file": "...", "layer": "completude|arquitetura|corretude|testes"}],
  "report_path": "verificacao_revisao.md"
}
"""


def _reviewer_instruction_provider(_ctx) -> str:
    """InstructionProvider do ADK: resolve no momento da invocação.

    Garante que a lista de arquivos do coder esteja atualizada quando o
    reviewer é chamado (após o coder rodar, não no import do módulo).
    """
    return (
        _REVIEWER_INSTRUCTION_TEMPLATE
        .replace("__CODER_WS__", _CODER_WS)
        .replace("__FILES__", _discover_coder_files())
    )


_reviewer = LlmAgent(
    model=_model,
    name="cr_review_agent",
    description=reviewer_prompt.description,
    instruction=_reviewer_instruction_provider,
    output_key="review",
    tools=[
        _bind(FunctionTool(tool_ler_arquivo), _CODER_WS),
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
