"""Reviewer dedicado ao workflow coding_review (2 fases: analyzer + persister).

Instância ajustada do reviewer original (src/agents/reviewer/):
- Analyzer: lê arquivos de coder/src/ (não diff git), produz markdown.
- Persister: persiste o relatório em coder/review/ via tool_salvar_relatorio.
- Evita conflito de parent com o sdlc_pipeline (instância dedicada).
"""

import os
from pathlib import Path

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool

from shared.agent_factory import _bind_tool_to_workspace
from shared.workspace import get_agent_workspace, get_workspace_root
from shared.tools import tool_ler_arquivo, tool_salvar_relatorio
from src.agents.reviewer import prompt as reviewer_prompt

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

_WORKSPACE_ROOT = str(get_workspace_root())
_CODER_WS = str(get_agent_workspace("cr_coder"))
_REVIEW_WS = str(get_agent_workspace("cr_reviewer"))


def _bind(tool, agent_ws):
    return _bind_tool_to_workspace(tool, agent_ws, _WORKSPACE_ROOT)


def _discover_coder_files() -> str:
    """Lista arquivos no _CODER_WS (relativo), formato bullet.

    Executado no momento da invocação do agente (via InstructionProvider).
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


# ---------------------------------------------------------------------------
# Fase 1: Analyzer (reutiliza "alma" de src/agents/reviewer/prompt.py)
# ---------------------------------------------------------------------------
# Composição: prompt original do reviewer ajustado para:
# - Ler arquivos do workspace (não diff git)
# - Produzir markdown (não JSON) — a persistência é do persister
# - Não chamar tool_salvar_relatorio — responsabilidade do persister

_ANALYZER_BASE = (
    reviewer_prompt.instruction
    .replace(
        "para ir à branch principal.",
        "para prosseguir no pipeline.",
    )
    .replace(
        "Consulte o diff acumulado da branch para listar TODOS os arquivos modificados/criados.",
        "Leia os arquivos criados pelo coder no workspace (listados abaixo em ARQUIVOS A REVISAR).",
    )
    .replace(
        "Examine os arquivos modificados no diff.",
        "Examine os arquivos listados em ARQUIVOS A REVISAR.",
    )
    .replace(
        "Examine o corpo das funções de lógica core no diff.",
        "Examine o corpo das funções de lógica core nos arquivos.",
    )
    .replace(
        "Verifique se arquivos de teste foram criados no diff.",
        "Verifique se arquivos de teste foram criados no workspace.",
    )
    .replace(
        "# SAÍDA FINAL\n"
        "Após completar as 4 camadas:\n"
        "1. Salve o relatório detalhado da verificação em Markdown com nome \"verificacao_revisao.md\".\n"
        "2. Sua **última mensagem** DEVE ser EXCLUSIVAMENTE um JSON conforme o schema\n"
        "   ReviewOutput do sistema:\n"
        "\n"
        "{\n"
        "  \"status\": \"APROVADO\",\n"
        "  \"issues\": [\n"
        "    {\"severity\": \"critical\", \"description\": \"Função X não trata exceção Y\", \"file\": \"src/service.py\", \"layer\": \"corretude\"},\n"
        "    {\"severity\": \"warning\", \"description\": \"Falta docstring\", \"file\": \"src/utils.py\", \"layer\": \"arquitetura\"}\n"
        "  ],\n"
        "  \"report_path\": \"verificacao_revisao.md\"\n"
        "}\n"
        "\n"
        "Use \"APROVADO\" ou \"BLOQUEADO\" no campo `status`.",
        "# SAÍDA\n"
        "Você é a FASE 1 de um pipeline de revisão de 2 fases. Sua única responsabilidade\n"
        "é PRODUZIR A ANÁLISE — outro agente vai persistir o relatório no próximo passo.\n"
        "\n"
        "Produza markdown com seções:\n"
        "- \"## Status: APROVADO\" ou \"## Status: BLOQUEADO\"\n"
        "- \"## Issues\" (lista por severidade com arquivo/camada/descrição)\n"
        "- \"## Resumo\" (1 parágrafo)\n"
        "\n"
        "NÃO produza JSON literal. NÃO tente salvar nada — você não tem essa capacidade nesta fase.",
    )
)

# Template final: injeta workspace e lista de arquivos em runtime
_ANALYZER_INSTRUCTION_TEMPLATE = (
    _ANALYZER_BASE + "\n\n"
    "# WORKSPACE\n"
    "Os arquivos a revisar estão em `__CODER_WS__/`.\n"
    "Use caminhos RELATIVOS — tool_ler_arquivo resolve automaticamente.\n\n"
    "# ARQUIVOS A REVISAR\n"
    "__FILES__\n"
)


def _analyzer_instruction_provider(_ctx) -> str:
    """InstructionProvider: injeta lista de arquivos do coder no momento da invocação."""
    return (
        _ANALYZER_INSTRUCTION_TEMPLATE
        .replace("__CODER_WS__", _CODER_WS)
        .replace("__FILES__", _discover_coder_files())
    )


_analyzer = LlmAgent(
    model=_model,
    name="cr_review_analyzer",
    description="Fase 1 de revisão: lê código do coder e produz análise em markdown.",
    instruction=_analyzer_instruction_provider,
    output_key="review_analysis",
    tools=[
        _bind(FunctionTool(tool_ler_arquivo), _CODER_WS),
    ],
)

# ---------------------------------------------------------------------------
# Fase 2: Persister
# ---------------------------------------------------------------------------

_PERSISTER_INSTRUCTION = """
Você é a FASE 2 de um pipeline de revisão de código.

A análise foi produzida pela fase anterior e está disponível abaixo:

---ANALISE---
{review_analysis}
---FIM ANALISE---

AÇÃO ÚNICA E OBRIGATÓRIA:
Chame tool_salvar_relatorio com:
  - nome_arquivo: "verificacao_revisao.md"
  - conteudo: o texto entre ---ANALISE--- e ---FIM ANALISE--- acima, EXATAMENTE como recebido.

NÃO responda com texto além da chamada da tool.
NÃO escreva a chamada como código Python descritivo (ex: NÃO escreva
`default_api.tool_salvar_relatorio(...)` como texto). FAÇA a function call real.
NÃO modifique o conteúdo da análise — apenas persista.
"""

_persister = LlmAgent(
    model=_model,
    name="cr_review_persister",
    description="Fase 2 de revisão: persiste o relatório produzido pelo analyzer.",
    instruction=_PERSISTER_INSTRUCTION,
    output_key="review",
    tools=[
        _bind(FunctionTool(tool_salvar_relatorio), _REVIEW_WS),
    ],
)

# ---------------------------------------------------------------------------
# Agente exportado: SequentialAgent que agrupa as 2 fases
# ---------------------------------------------------------------------------

agent = SequentialAgent(
    name="cr_review_agent",
    description="Pipeline de revisão em 2 fases: análise + persistência.",
    sub_agents=[_analyzer, _persister],
)
