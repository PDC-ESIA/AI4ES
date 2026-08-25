"""Reviewer dedicado ao workflow coding_review.

- Analyzer: lê arquivos de coder/src/ (não diff git), produz análise markdown.
- Análise estática pré-LLM via before_agent_callback (Ruff + Bandit).
- Persistência via after_agent_callback Python puro — sem LLM no passo de escrita.
  Isso elimina o risco de "modo narrador" (LLM descreve a chamada em vez de executá-la).
- Instância dedicada com prompt próprio, evitando conflito de parent no pipeline.

Variáveis de ambiente:
    REVIEWER_STATIC_ANALYSIS: "0" desabilita análise estática pré-LLM (padrão: habilitado).

Os callbacks/helpers de análise estática (Ruff+Bandit) e persistência vivem em
shared/tools/coding_tools/review_tools.py.
"""

import os
from collections.abc import Mapping

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from shared.tools.coding_tools.filesystem_coding import tool_ler_arquivo
from shared.tools.coding_tools.review_tools import (
    _CODER_WS,
    _REVIEW_WS,
    _bind,
    _discover_coder_files,
    _inject_static_findings,
    _persist_review,
)

from . import prompt as reviewer_prompt

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

# Re-exportados para uso/teste via atributo do módulo (ex.: agent._CODER_WS,
# agent._discover_coder_files) — mantém compatibilidade com quem referencia esses
# nomes diretamente aqui, embora a implementação viva em review_tools.py.
__all__ = [
    "agent",
    "_analyzer",
    "_CODER_WS",
    "_REVIEW_WS",
    "_discover_coder_files",
    "_inject_static_findings",
    "_persist_review",
]


# ---------------------------------------------------------------------------
# Analyzer (usa a "alma" do prompt local)
# ---------------------------------------------------------------------------
# Composição: prompt base ajustado para:
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
    "# RESULTADO DETERMINÍSTICO DAS TASKS\n"
    "Este bloco vem do TaskIterator. Use-o para distinguir aprovação plena,\n"
    "aceitação com ressalvas e bloqueio; não invente nem altere esses status.\n"
    "__TASK_OUTCOMES__\n\n"
    "# ANÁLISE ESTÁTICA (pré-LLM)\n"
    "Os seguintes problemas foram identificados por ferramentas determinísticas\n"
    "de análise estática da stack (linters/analisadores, ex.: Ruff/Bandit em\n"
    "Python, ESLint em Node, SpotBugs/PMD em Java, go vet em Go) antes desta\n"
    "análise. Podem estar vazios se a stack não tiver analisador configurado.\n"
    "Use-os como ponto de partida e complemente com sua revisão das 4 camadas:\n\n"
    "__STATIC_FINDINGS__\n\n"
    "# WORKSPACE\n"
    "Os arquivos a revisar estão em `__CODER_WS__/`.\n"
    "Use caminhos RELATIVOS — tool_ler_arquivo resolve automaticamente.\n\n"
    "# ARQUIVOS A REVISAR\n"
    "__FILES__\n"
)


def _render_task_outcomes(state) -> str:
    """Renderiza somente os campos de decisão necessários ao reviewer."""
    if not isinstance(state, Mapping):
        return "Resumo de tasks não disponível."
    summary = state.get("task_iteration_summary")
    if not isinstance(summary, Mapping):
        return "Resumo de tasks não disponível."

    expected = summary.get("expected_task_ids")
    results = summary.get("task_results")
    accepted = summary.get("accepted_task_ids")
    lines = [
        f"Cobertura completa: {summary.get('cobertura_completa') is True}",
        f"Qualidade completa: {summary.get('qualidade_completa') is True}",
        "Tasks aceitas com ressalvas: "
        + (", ".join(str(item) for item in accepted) if isinstance(accepted, list) and accepted else "nenhuma"),
    ]
    if not isinstance(expected, list) or not isinstance(results, Mapping):
        return "\n".join(lines)

    for task_id in expected:
        result = results.get(task_id)
        if not isinstance(result, Mapping):
            lines.append(f"- {task_id}: resultado ausente")
            continue
        lines.append(
            f"- {task_id}: status={result.get('status')}; "
            f"conceito={result.get('conceito')}; nota={result.get('nota_final')}; "
            f"término={result.get('motivo_terminacao')}"
        )
    return "\n".join(lines)


def _analyzer_instruction_provider(ctx) -> str:
    """InstructionProvider: injeta findings estáticos e lista de arquivos em runtime."""
    static_block = ""
    state = None
    if hasattr(ctx, "state"):
        state = ctx.state
        static_block = state.get("static_findings_block", "")
    return (
        _ANALYZER_INSTRUCTION_TEMPLATE
        .replace("__TASK_OUTCOMES__", _render_task_outcomes(state))
        .replace("__STATIC_FINDINGS__", static_block or "Análise estática não disponível.")
        .replace("__CODER_WS__", _CODER_WS)
        .replace("__FILES__", _discover_coder_files())
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
