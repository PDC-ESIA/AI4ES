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

import logging
import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from shared.memory.config import get_memory
from shared.tools.coding_tools.filesystem_coding import tool_ler_arquivo
from shared.tools.coding_tools.review_tools import (
    _CODER_WS,
    _REVIEW_WS,
    _bind,
    _discover_coder_files,
    _inject_static_findings,
    _persist_review,
)

from ..memory_feedforward import stack_key
from . import prompt as reviewer_prompt

logger = logging.getLogger(__name__)

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


def _analyzer_instruction_provider(ctx) -> str:
    """InstructionProvider: injeta findings estáticos e lista de arquivos em runtime."""
    static_block = ""
    if hasattr(ctx, "state"):
        static_block = ctx.state.get("static_findings_block", "")
    return (
        _ANALYZER_INSTRUCTION_TEMPLATE
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


def _resolver_stack_key(state) -> str:
    """`memory_stack_key` gravado pelo `memory_feedforward` — com fallback.

    O fallback recalcula a partir de `tasks.macro_context.tech_stack` (mesma
    função `stack_key`) só para o caso raro de `memory_feedforward` ter
    falhado silenciosamente antes de gravar o state_delta.
    """
    chave = state.get("memory_stack_key")
    if chave:
        return chave
    tasks = state.get("tasks") or {}
    macro_context = tasks.get("macro_context") if isinstance(tasks, dict) else None
    return stack_key((macro_context or {}).get("tech_stack") or [])


def _formatar_licao(error_history: list[dict], review_analysis: str) -> str:
    """Resume o histórico de reprovações desta run numa mensagem legível.

    O mem0 faz sua própria extração de fatos em cima deste texto — só precisa
    dar contexto suficiente para essa extração funcionar bem; não precisa ser
    o ErrorReport bruto (JSON denso, ruim de "ler" para o LLM de extração).
    """
    partes = []
    for i, erro in enumerate(error_history, start=1):
        estagios = "; ".join(
            f"{e.get('stage')}: {e.get('error_code') or e.get('summary')}"
            for e in erro.get("failed_stages", [])
        )
        partes.append(
            f"Iteração {i}: motivo do bloqueio = {erro.get('blocking_reason')}. "
            f"Estágios com falha: {estagios or 'nenhum registrado'}."
        )
    status_final = (
        "APROVADO" if "APROVADO" in (review_analysis or "") else "revisão concluída"
    )
    partes.append(f"Status final após revisão: {status_final}.")
    return "\n".join(partes)


async def _escrever_memoria(callback_context) -> None:
    """`after_agent_callback` adicional do reviewer — PoC mem0.

    Roda em conjunto com `_persist_review` (via lista em `after_agent_callback`
    — o runtime do ADK chama cada callback da lista em ordem; nenhum dos dois
    produz conteúdo de override, então os dois sempre executam). Só grava no
    mem0 quando houve pelo menos uma reprovação no loop (`error_history`
    não-vazio) — não há lição a aprender de uma run que passou de primeira.

    Mesma filosofia de degradação do `memory_feedforward`: falha do mem0 aqui
    nunca deve derrubar o pipeline nem invalidar a persistência do relatório
    de revisão (que já aconteceu antes, via `_persist_review`).
    """
    error_history = callback_context.state.get("error_history") or []
    if not error_history:
        return

    chave = _resolver_stack_key(callback_context.state)
    review_analysis = str(callback_context.state.get("review_analysis") or "")
    licao = _formatar_licao(error_history, review_analysis)

    try:
        await get_memory().add(messages=licao, agent_id=chave)
    except Exception:
        logger.exception(
            "reviewer: falha ao gravar lição no mem0 (stack=%r) — relatório "
            "de revisão já persistido normalmente, sem impacto no pipeline",
            chave,
        )


_analyzer.before_agent_callback = _inject_static_findings
_analyzer.after_agent_callback = [_persist_review, _escrever_memoria]

# agent é exportado como LlmAgent (not SequentialAgent) — a persistência acontece
# via after_agent_callback, sem necessidade de um segundo agente no pipeline.
agent = _analyzer
