"""Callbacks e helpers de análise estática do cr_reviewer (workflow_coding_review).

- _inject_static_findings (before_agent_callback): roda Ruff + Bandit sobre o
  workspace do coder e injeta os findings no state para o prompt do analyzer.
- _persist_review (after_agent_callback): grava a análise do LLM em disco,
  sem passar por uma tool exposta ao modelo (evita "modo narrador").
- _discover_coder_files / _format_findings_block / _bind: helpers de suporte.

_analyzer_instruction_provider NÃO está aqui de propósito: ele depende de
_ANALYZER_INSTRUCTION_TEMPLATE, que é montado a partir do prompt do reviewer
e fica em cr_reviewer.py junto com a definição do agente.
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from shared.agent_factory import _bind_tool_to_workspace
from shared.review import run_capabilities
from shared.workspace import get_agent_workspace, get_workspace_root
from shared.tools.coding_tools.filesystem_coding import tool_salvar_relatorio

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
else:
    CallbackContext = Any  # type: ignore[misc,assignment]

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


def _format_findings_block(findings) -> str:
    """Formata lista de Finding em bloco legível para o prompt do LLM."""
    if not findings:
        return "Nenhum problema identificado pelas ferramentas de análise estática."
    lines = []
    for f in findings:
        loc = f"{f.arquivo}:{f.linha}" if f.linha else f.arquivo
        lines.append(f"[{f.severidade.upper()}] {f.origem}/{f.regra} — {loc}\n  {f.mensagem}")
    return "\n".join(lines)


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
