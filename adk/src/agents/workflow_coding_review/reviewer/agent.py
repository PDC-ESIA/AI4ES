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
from collections.abc import Mapping
from datetime import datetime, timezone

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from shared.coding_review_lesson_memory.config import get_memory, memoria_habilitada
from shared.coding_review_lesson_memory.error_log import (
    limite_lote,
    limpar_erros_pendentes,
    ler_erros_pendentes,
    registrar_erros,
)
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
    reviewer_prompt.instruction.replace(
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
        '1. Salve o relatório detalhado da verificação em Markdown com nome "verificacao_revisao.md".\n'
        "2. Sua **última mensagem** DEVE ser EXCLUSIVAMENTE um JSON conforme o schema\n"
        "   ReviewOutput do sistema:\n"
        "\n"
        "{\n"
        '  "status": "APROVADO",\n'
        '  "issues": [\n'
        '    {"severity": "critical", "description": "Função X não trata exceção Y", "file": "src/service.py", "layer": "corretude"},\n'
        '    {"severity": "warning", "description": "Falta docstring", "file": "src/utils.py", "layer": "arquitetura"}\n'
        "  ],\n"
        '  "report_path": "verificacao_revisao.md"\n'
        "}\n"
        "\n"
        'Use "APROVADO" ou "BLOQUEADO" no campo `status`.',
        "# SAÍDA\n"
        "Sua responsabilidade é PRODUZIR A ANÁLISE em markdown — a persistência em disco\n"
        "é feita automaticamente pelo pipeline após sua resposta.\n"
        "\n"
        "Produza markdown com seções:\n"
        '- "## Status: APROVADO" ou "## Status: BLOQUEADO"\n'
        '- "## Issues" (lista por severidade com arquivo/camada/descrição)\n'
        '- "## Resumo" (1 parágrafo)\n'
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
    "## Como ler a dimensão de aceite\n"
    "`nota` é calculada SÓ sobre os critérios que puderam ser verificados por\n"
    "teste automatizado; `cobertura` diz quantos puderam. São medidas distintas:\n"
    "- Critério listado em `sem teste que os cubra` é lacuna ENDEREÇÁVEL — o\n"
    "  código é testável e ninguém escreveu o teste. Registre como issue de\n"
    "  completude (severidade `warning`), citando o id do critério.\n"
    "- Cobertura baixa por si só NÃO é defeito do código: critérios de jornada de\n"
    "  interface ou subjetivos não têm como ser comprovados por teste de código\n"
    "  neste fluxo. NÃO bloqueie a entrega por causa dela, e não invente issue\n"
    "  para critério que não aparece como endereçável.\n\n"
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
        lines.append(f"  {_linha_de_aceite(result)}")
    return "\n".join(lines)


def _linha_de_aceite(result: Mapping) -> str:
    """Dimensão de aceite da task, em uma linha, para o contexto do reviewer."""
    aceite = result.get("aceite")
    aceite = aceite if isinstance(aceite, Mapping) else {}
    total = aceite.get("total") or 0
    if not total:
        return "critérios de aceite: nenhum registrado"

    atendidos = aceite.get("atendidos") or 0
    nao_atendidos = aceite.get("nao_atendidos") or 0
    sem_cobertura = max(total - atendidos - nao_atendidos, 0)
    nota = result.get("nota_aceite")
    nota_txt = (
        f"{nota:.2f}"
        if isinstance(nota, (int, float)) and not isinstance(nota, bool)
        else "não apurável"
    )
    cobertura = result.get("cobertura_criterios") or 0.0
    enderecaveis = aceite.get("criterios_enderecaveis")
    pendentes = (
        ", ".join(str(item) for item in enderecaveis)
        if isinstance(enderecaveis, list) and enderecaveis
        else "nenhum"
    )
    return (
        f"critérios de aceite: nota={nota_txt}; "
        f"cobertura={cobertura * 100:.0f}% ({atendidos} atendidos, "
        f"{nao_atendidos} não atendidos, {sem_cobertura} sem verificação); "
        f"sem teste que os cubra: {pendentes}"
    )


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
    macro_context_dict = macro_context if isinstance(macro_context, dict) else {}
    return stack_key(macro_context_dict.get("tech_stack") or [])


def _entradas_brutas(error_history: list[dict], chave_stack: str) -> list[dict]:
    """Achata `error_history` numa entrada por estágio que falhou.

    Granularidade de estágio (não de execução inteira) porque o que decide
    se um erro "se repetiu" é o mesmo estágio+código de erro acontecendo de
    novo — não o relatório inteiro, que pode misturar vários estágios numa
    única reprovação.
    """
    agora = datetime.now(timezone.utc).isoformat()
    entradas = []
    for erro in error_history:
        for estagio in erro.get("failed_stages", []):
            entradas.append(
                {
                    "stack_key": chave_stack,
                    "work_item_id": erro.get("work_item_id"),
                    "iteration": erro.get("iteration"),
                    "stage": estagio.get("stage"),
                    "error_code": estagio.get("error_code"),
                    "summary": estagio.get("summary"),
                    "blocking_reason": erro.get("blocking_reason"),
                    "created_at": agora,
                }
            )
    return entradas


def _assinatura_erro(entrada: dict) -> str:
    """Identifica "o mesmo erro" entre entradas — estágio + código do erro
    (ou resumo, quando não há código), normalizados."""
    estagio = (entrada.get("stage") or "").strip().casefold()
    identificador = (
        (entrada.get("error_code") or entrada.get("summary") or "").strip().casefold()
    )
    return f"{estagio}:{identificador[:80]}"


def _filtrar_recorrentes(entradas: list[dict]) -> list[dict]:
    """Mantém só as entradas cuja assinatura apareceu 2+ vezes no lote.

    Erro que só aconteceu uma vez no lote é descartado — não vira lição.
    Versão simplificada por contagem, sem o estado de "candidato pendente"
    entre lotes.
    """
    contagem: dict[str, int] = {}
    for entrada in entradas:
        assinatura = _assinatura_erro(entrada)
        contagem[assinatura] = contagem.get(assinatura, 0) + 1
    return [e for e in entradas if contagem[_assinatura_erro(e)] >= 2]


def _formatar_licao_lote(entradas_recorrentes: list[dict]) -> str:
    """Resume os erros que se repetiram no lote numa mensagem legível.

    O mem0 faz sua própria extração de fatos em cima deste texto — só precisa
    dar contexto suficiente para essa extração funcionar bem.
    """
    partes = [
        f"Erro recorrente: estágio={entrada.get('stage')}, "
        f"motivo={entrada.get('error_code') or entrada.get('summary')}, "
        f"bloqueio={entrada.get('blocking_reason')}."
        for entrada in entradas_recorrentes
    ]
    return "\n".join(partes)


async def _escrever_memoria(callback_context) -> None:
    """`after_agent_callback` adicional do reviewer — PoC de memória em lote.

    Roda em conjunto com `_persist_review` (via lista em `after_agent_callback`
    — o runtime do ADK chama cada callback da lista em ordem; nenhum dos dois
    produz conteúdo de override, então os dois sempre executam).

    Não escreve mais no mem0 a cada reprovação: acumula os erros brutos num
    log local por stack (`shared/coding_review_lesson_memory/error_log.py`, arquivo — sem
    Postgres nesta camada) e só processa o lote quando acumula
    `limite_lote()` erros pendentes. Do lote, só o que se
    repetiu (mesma assinatura 2+ vezes) vira lição; erro isolado é
    descartado, não é considerado padrão.

    Mesma filosofia de degradação da versão anterior: falha aqui nunca deve
    derrubar o pipeline nem invalidar a persistência do relatório de revisão
    (que já aconteceu antes, via `_persist_review`) — TODO o processamento
    do lote roda protegido, não só a chamada ao mem0, porque qualquer bug
    nessa camada (ex.: config inválida) já derrubou uma run inteira antes.
    Se a escrita no mem0 falhar especificamente, o lote pendente NÃO é
    limpo — é reprocessado na próxima reprovação daquela stack.

    Interruptor geral: se `memoria_habilitada()` for falso, a função sai
    imediatamente — nem grava erro no arquivo local, nem toca o mem0.
    """
    if not memoria_habilitada():
        return

    error_history = callback_context.state.get("error_history") or []
    if not error_history:
        return

    chave = _resolver_stack_key(callback_context.state)
    novas_entradas = _entradas_brutas(error_history, chave)
    if not novas_entradas:
        return

    try:
        registrar_erros(chave, novas_entradas)
        pendentes = ler_erros_pendentes(chave)
        if len(pendentes) < limite_lote():
            return

        recorrentes = _filtrar_recorrentes(pendentes)
        if recorrentes:
            licao = _formatar_licao_lote(recorrentes)
            try:
                await get_memory().add(messages=licao, agent_id=chave)
            except Exception:
                logger.exception(
                    "reviewer: falha ao gravar lição em lote no mem0 (stack=%r) — "
                    "lote preservado, será reprocessado na próxima reprovação",
                    chave,
                )
                return

        limpar_erros_pendentes(chave)
    except Exception:
        logger.exception(
            "reviewer: falha inesperada no processamento do lote de memória "
            "(stack=%r) — pipeline e relatório de revisão seguem normalmente",
            chave,
        )


_analyzer.before_agent_callback = _inject_static_findings
_analyzer.after_agent_callback = [_persist_review, _escrever_memoria]

# agent é exportado como LlmAgent (not SequentialAgent) — a persistência acontece
# via after_agent_callback, sem necessidade de um segundo agente no pipeline.
agent = _analyzer
