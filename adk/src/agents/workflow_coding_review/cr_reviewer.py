"""Reviewer dedicado ao workflow coding_review.

Instância ajustada do reviewer original (src/agents/reviewer/):
- Analyzer: lê arquivos de coder/src/ (não diff git), produz análise markdown.
- Análise estática pré-LLM via before_agent_callback (Ruff + Bandit).
- Persistência via after_agent_callback Python puro — sem LLM no passo de escrita.
  Isso elimina o risco de "modo narrador" (LLM descreve a chamada em vez de executá-la).
- Evita conflito de parent com o sdlc_pipeline (instância dedicada).

Variáveis de ambiente:
    REVIEWER_STATIC_ANALYSIS: "0" desabilita análise estática pré-LLM (padrão: habilitado).
"""

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from shared.agent_factory import _bind_tool_to_workspace
from shared.review import run_capabilities
from shared.workspace import get_agent_workspace, get_workspace_root
from shared.tools import tool_ler_arquivo, tool_salvar_relatorio
from src.agents.reviewer import prompt as reviewer_prompt

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
else:
    CallbackContext = Any  # type: ignore[misc,assignment]

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)
_STATIC_ANALYSIS_ENABLED = os.environ.get("REVIEWER_STATIC_ANALYSIS", "1") != "0"
_MAX_FINDINGS = 30

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
        p.relative_to(coder_dir).as_posix()
        for p in coder_dir.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )
    if not files:
        return "- (workspace vazio)"
    return "\n".join(f"- {f}" for f in files)


# ---------------------------------------------------------------------------
# Analyzer (reutiliza "alma" de src/agents/reviewer/prompt.py)
# ---------------------------------------------------------------------------
# Composição: prompt original do reviewer ajustado para:
# - Ler arquivos do workspace (não diff git)
# - Produzir markdown — persistência feita via after_agent_callback
# - Não chamar tool_salvar_relatorio — responsabilidade do callback

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
        "Sua responsabilidade é PRODUZIR A ANÁLISE em markdown — a persistência em disco\n"
        "é feita automaticamente pelo pipeline após sua resposta.\n"
        "\n"
        "Produza markdown com seções:\n"
        "- \"## Status: APROVADO\" ou \"## Status: BLOQUEADO\"\n"
        "- \"## Issues\" (lista por severidade com arquivo/camada/descrição)\n"
        "- \"## Resumo\" (1 parágrafo)\n"
        "\n"
        "NÃO produza JSON literal.",
    )
)

# Template final: injeta análise estática, workspace e lista de arquivos em runtime
_ANALYZER_INSTRUCTION_TEMPLATE = (
    _ANALYZER_BASE + "\n\n"
    "# ANÁLISE ESTÁTICA (pré-LLM)\n"
    "Os seguintes problemas foram identificados por ferramentas determinísticas\n"
    "(Ruff e Bandit) antes desta análise. Use-os como ponto de partida e\n"
    "complemente com sua revisão das 4 camadas:\n\n"
    "__STATIC_FINDINGS__\n\n"
    "# WORKSPACE\n"
    "Os arquivos a revisar estão em `__CODER_WS__/`.\n"
    "Use caminhos RELATIVOS — tool_ler_arquivo resolve automaticamente.\n\n"
    "# ARQUIVOS A REVISAR\n"
    "__FILES__\n\n"
    "# RESULTADO DA EXECUÇÃO DAS TASKS\n"
    "Este bloco é evidência determinística do iterator. Se o outcome não for\n"
    "`aprovado`, deixe explícito no relatório que a revisão é parcial ou que o\n"
    "processamento não foi iniciado; não trate tasks pendentes como aprovadas.\n\n"
    "__TASK_EXECUTION__\n"
)


def _format_findings_block(findings) -> str:
    """Formata lista de Finding em bloco legível para o prompt do LLM."""
    if not findings:
        return "Nenhum problema identificado pelas ferramentas de análise estática."
    lines = []
    for f in findings:
        loc = f"{f.arquivo}:{f.linha}" if f.linha else f.arquivo
        lines.append(f"[{f.severidade.upper()}] {f.origem}/{f.regra} — {loc}\n  {f.mensagem}")
    return "\n".join(lines)


def _analyzer_instruction_provider(ctx) -> str:
    """InstructionProvider: injeta findings estáticos e lista de arquivos em runtime."""
    static_block = ""
    task_execution = {"summary": None, "results": []}
    if hasattr(ctx, "state"):
        static_block = ctx.state.get("static_findings_block", "")
        task_execution = {
            "summary": ctx.state.get("task_iteration_summary"),
            "results": ctx.state.get("task_results") or [],
            "error": ctx.state.get("task_iteration_error"),
            "failure_policy": ctx.state.get("task_failure_policy"),
        }
    return (
        _ANALYZER_INSTRUCTION_TEMPLATE
        .replace("__STATIC_FINDINGS__", static_block or "Análise estática não disponível.")
        .replace("__CODER_WS__", _CODER_WS)
        .replace("__FILES__", _discover_coder_files())
        .replace(
            "__TASK_EXECUTION__",
            json.dumps(task_execution, indent=2, ensure_ascii=False),
        )
    )


def _inject_static_findings(callback_context: CallbackContext) -> None:
    """Roda análise estática no workspace do coder antes do LLM analisar.

    Injeta o bloco de findings em state["static_findings_block"] para que
    _analyzer_instruction_provider o inclua no prompt em runtime.
    Retorna None para não interromper a execução do agente.
    """
    if not _STATIC_ANALYSIS_ENABLED:
        return None
    coder_path = Path(_CODER_WS)
    if not coder_path.exists():
        callback_context.state["static_findings_block"] = (
            "Workspace do coder não encontrado — análise estática ignorada."
        )
        return None
    findings = run_capabilities(coder_path)
    capped = findings[:_MAX_FINDINGS]
    callback_context.state["static_findings_block"] = _format_findings_block(capped)
    return None


def _persist_review(callback_context: CallbackContext) -> None:
    """Persiste o relatório de revisão no disco — zero LLM no passo de escrita.

    Executado pelo runtime do ADK após _analyzer terminar.
    Lê review_analysis do callback_context.state e chama tool_salvar_relatorio
    diretamente em Python, eliminando o risco de modo narrador.

    Raises:
        RuntimeError: se tool_salvar_relatorio retornar sucesso=False
            (cobre tanto falha de I/O quanto parâmetros inválidos).
    """
    analysis_raw = callback_context.state.get("review_analysis")
    if analysis_raw is None:
        return
    analysis = str(analysis_raw)
    if not analysis.strip():
        return
    result = tool_salvar_relatorio(
        conteudo=analysis,
        nome_arquivo="verificacao_revisao.md",
        base_dir=_REVIEW_WS,
    )
    if not result.get("sucesso"):
        raise RuntimeError(
            "Falha ao persistir relatório de revisão em "
            f"'{result.get('caminho') or 'verificacao_revisao.md'}': {result.get('erro')}"
        )


_analyzer = LlmAgent(
    model=_model,
    name="cr_review_analyzer",
    description="Revisão de código: lê arquivos do coder, produz análise markdown e persiste via callback.",
    instruction=_analyzer_instruction_provider,
    output_key="review_analysis",
    tools=[
        _bind(FunctionTool(tool_ler_arquivo), _CODER_WS),
    ],
)
_analyzer.before_agent_callback = _inject_static_findings
_analyzer.after_agent_callback = _persist_review

# agent é exportado como LlmAgent (not SequentialAgent) — a persistência acontece
# via after_agent_callback, sem necessidade de um segundo agente no pipeline.
agent = _analyzer
