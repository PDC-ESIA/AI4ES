"""Callbacks e helpers de análise estática do cr_reviewer (workflow_coding_review).

- _preflight_coverage_gate (before_agent_callback): encerra deterministicamente,
  SEM chamar o LLM, quando a cobertura das tasks já impede aprovação.
- _inject_static_findings (before_agent_callback): roda Ruff + Bandit sobre o
  workspace do coder e injeta os findings no state para o prompt do analyzer.
- _persist_review (after_agent_callback): aplica o gate determinístico de
  cobertura de tasks e grava a análise em disco, sem passar por uma tool
  exposta ao modelo (evita "modo narrador").
- _discover_coder_files / _format_findings_block / _bind: helpers de suporte.

_analyzer_instruction_provider NÃO está aqui de propósito: ele depende de
_ANALYZER_INSTRUCTION_TEMPLATE, que é montado a partir do prompt do reviewer
e fica em cr_reviewer.py junto com a definição do agente.
"""

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from google.genai import types

from shared.agent_factory import _bind_tool_to_workspace
from shared.review import run_capabilities
from shared.workspace import get_agent_workspace, get_workspace_root
from shared.tools.coding_tools.filesystem_coding import (
    listar_arquivos,
    tool_salvar_relatorio,
)

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
    Usa o mesmo helper (e o mesmo teto) do coder: a lista entra na instrução,
    que é reenviada a cada requisição, então um projeto grande não pode inflá-la
    sem limite.
    """
    return listar_arquivos(
        Path(_CODER_WS),
        inexistente="- (nenhum arquivo ainda — coder será executado antes de você)",
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


# ---------------------------------------------------------------------------
# Gate determinístico de cobertura de tasks
# ---------------------------------------------------------------------------
# O reviewer não pode sinalizar APROVADO quando o TaskIterator não comprovou a
# cobertura das tasks. O gate é aplicado APÓS o LLM, em Python puro: nada disso
# depende do prompt, e o corpo da análise nunca é reescrito — só a linha de
# status e o bloco de nota são sobrepostos, e apenas quando há bloqueio.

_STATUS_BLOQUEADO = "## Status: BLOQUEADO"
_GATE_INICIO = "<!-- task-coverage-gate:start -->"
_GATE_FIM = "<!-- task-coverage-gate:end -->"

# Todas as linhas de status do markdown (não só a primeira) — o LLM pode ter
# escrito mais de uma, e nenhuma delas pode sobreviver a um bloqueio.
_STATUS_RE = re.compile(r"^## Status:\s*.*$", re.MULTILINE)
_BLOCO_GATE_RE = re.compile(
    re.escape(_GATE_INICIO) + r".*?" + re.escape(_GATE_FIM), re.DOTALL
)

_NOTA_SUMMARY_INVALIDO = (
    "Cobertura bloqueada automaticamente: o resumo de iteração está ausente "
    "ou inválido; não foi possível determinar com segurança as tasks pendentes."
)


def _normalizar_summary(summary: Any) -> Optional[dict]:
    """Valida e copia o contrato do `task_iteration_summary`.

    O gate é fail-closed: um booleano `cobertura_completa=True` isolado não é
    prova suficiente. Todos os campos produzidos pelo TaskIterator precisam
    existir com os tipos esperados para que o summary seja utilizável.
    """
    if not isinstance(summary, dict):
        return None

    input_valid = summary.get("input_valid")
    input_errors = summary.get("input_errors")
    expected = summary.get("expected_task_ids")
    processed = summary.get("processed_task_ids")
    approved = summary.get("approved_task_ids")
    task_results = summary.get("task_results")
    cobertura = summary.get("cobertura_completa")

    if type(input_valid) is not bool or type(cobertura) is not bool:
        return None
    if not isinstance(input_errors, list) or not all(
        isinstance(erro, dict) for erro in input_errors
    ):
        return None
    if not all(
        isinstance(ids, list) and all(isinstance(task_id, str) for task_id in ids)
        for ids in (expected, processed, approved)
    ):
        return None
    if not isinstance(task_results, dict) or not all(
        isinstance(task_id, str) and isinstance(resultado, dict)
        for task_id, resultado in task_results.items()
    ):
        return None

    return {
        "input_valid": input_valid,
        "input_errors": [dict(erro) for erro in input_errors],
        "expected_task_ids": list(expected),
        "processed_task_ids": list(processed),
        "approved_task_ids": list(approved),
        "task_results": {
            task_id: dict(resultado) for task_id, resultado in task_results.items()
        },
        "cobertura_completa": cobertura,
    }


def _cobertura_recalculada(summary: dict) -> bool:
    """Recalcula a cobertura sem confiar apenas no booleano publicado."""
    expected = summary["expected_task_ids"]
    processed = summary["processed_task_ids"]
    approved = summary["approved_task_ids"]
    return (
        summary["input_valid"] is True
        and len(expected) > 0
        and set(expected) == set(processed)
        and set(expected) == set(approved)
    )


def cobertura_comprovada(state: Any) -> bool:
    """True somente quando o summary é válido e sua cobertura é consistente."""
    summary = _normalizar_summary(state.get("task_iteration_summary"))
    return bool(
        summary is not None
        and summary["cobertura_completa"] is True
        and _cobertura_recalculada(summary)
    )


def _linhas_de_pendencia(summary: dict) -> list[str]:
    """Descreve o que impediu a cobertura, na ordem original das tasks.

    Usa apenas vocabulário controlado (ids validados, status e motivos do
    próprio TaskIterator): nada de texto livre de terceiros no relatório.
    """
    linhas: list[str] = []

    for erro in summary.get("input_errors") or []:
        if isinstance(erro, dict):
            linhas.append(
                f"- Entrada inválida ({erro.get('type')}): {erro.get('detalhe')}"
            )

    esperadas = summary.get("expected_task_ids") or []
    aprovadas = set(summary.get("approved_task_ids") or [])
    resultados = summary.get("task_results")
    resultados = resultados if isinstance(resultados, dict) else {}

    for task_id in esperadas:
        if task_id in aprovadas:
            continue
        resultado = resultados.get(task_id)
        if isinstance(resultado, dict):
            linhas.append(
                f"- {task_id}: {resultado.get('status')} "
                f"(motivo: {resultado.get('motivo_terminacao')})"
            )
        else:
            linhas.append(f"- {task_id}: não processada")

    if not linhas:
        linhas.append(
            "- Cobertura não comprovada pelo iterador de tasks "
            "(nenhuma pendência individual identificada)."
        )
    return linhas


def _montar_nota_gate(summary: Any) -> str:
    """Bloco delimitado com o motivo do bloqueio, pronto para o markdown."""
    normalizado = _normalizar_summary(summary)
    if normalizado is not None:
        corpo = "\n".join(
            ["Cobertura de tasks incompleta — pendências:", ""]
            + _linhas_de_pendencia(normalizado)
        )
    else:
        corpo = _NOTA_SUMMARY_INVALIDO
    return f"{_GATE_INICIO}\n{corpo}\n{_GATE_FIM}"


def aplicar_gate_de_cobertura(analysis: str, summary: Any) -> str:
    """Sobrepõe status e nota de bloqueio, preservando o corpo da análise.

    Idempotente: remove TODAS as linhas de status e qualquer bloco de gate
    anterior antes de inserir exatamente um de cada, de modo que reaplicar
    sobre um texto já ajustado devolva o mesmo texto.
    """
    corpo = _BLOCO_GATE_RE.sub("", _STATUS_RE.sub("", analysis)).strip()
    partes = [_STATUS_BLOQUEADO, "", _montar_nota_gate(summary)]
    if corpo:
        partes.extend(["", corpo])
    return "\n".join(partes)


def _salvar_relatorio(conteudo: str) -> None:
    """Grava o relatório de revisão no workspace do reviewer.

    Raises:
        RuntimeError: se tool_salvar_relatorio retornar sucesso=False
            (cobre tanto falha de I/O quanto parâmetros inválidos).
    """
    result = tool_salvar_relatorio(
        conteudo=conteudo,
        nome_arquivo="verificacao_revisao.md",
        base_dir=_REVIEW_WS,
    )
    if not result.get("sucesso"):
        raise RuntimeError(
            "Falha ao persistir relatório de revisão em "
            f"'{result.get('caminho') or 'verificacao_revisao.md'}': {result.get('erro')}"
        )


def _preflight_coverage_gate(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """Interrompe o reviewer ANTES do LLM quando a cobertura é incompleta.

    Sem cobertura comprovada o veredito final já está decidido, então gastar uma
    chamada de modelo é desperdício — e arriscado: o reviewer recebe o histórico
    da invocação, que cresce com o nº de tasks e pode estourar a janela de
    contexto do provedor. Bloquear aqui também torna o gate resistente a uma
    falha do próprio LLM, que deixaria o `after_agent_callback` sem rodar.

    Qualquer `review_analysis` remanescente no state é ignorado de propósito:
    sem cobertura, o relatório deve depender só do summary determinístico desta
    execução, nunca de uma análise sobrevivente de outra invocação.

    ATENÇÃO — o relatório é gravado AQUI, e não em `_persist_review`: quando um
    `before_agent_callback` devolve Content, o ADK marca `end_invocation=True` e
    retorna antes de `_handle_after_agent_callback` (ver base_agent.py). Se este
    callback não persistisse, o bloqueio existiria como evento mas não haveria
    `verificacao_revisao.md` em disco.

    Returns:
        None quando a cobertura está comprovada (o reviewer roda normalmente);
        o Content bloqueado caso contrário, encerrando a invocação.
    """
    state = callback_context.state
    if cobertura_comprovada(state):
        return None

    # A análise estática já rodou (`_inject_static_findings` vem antes na
    # cadeia) e entra como corpo do relatório: bloquear a chamada ao LLM não
    # deve custar o diagnóstico determinístico sobre o código reprovado.
    findings = state.get("static_findings_block") or ""
    corpo = f"## Análise estática (determinística)\n\n{findings}" if findings else ""
    texto_final = aplicar_gate_de_cobertura(corpo, state.get("task_iteration_summary"))
    state["review_analysis"] = texto_final
    _salvar_relatorio(texto_final)
    return types.Content(role="model", parts=[types.Part(text=texto_final)])


def _persist_review(callback_context: CallbackContext) -> Optional[types.Content]:
    """Aplica o gate de cobertura e persiste o relatório — zero LLM na escrita.

    Executado pelo runtime do ADK após _analyzer terminar. Lê review_analysis
    do state e chama tool_salvar_relatorio diretamente em Python, eliminando o
    risco de modo narrador.

    Com `_preflight_coverage_gate` ligado no `before`, o caminho bloqueado aqui
    só é alcançado se aquele callback for removido do wiring — ele permanece
    como defesa em profundidade, para que o gate nunca dependa de um único
    ponto de aplicação.

    Com cobertura comprovada, o comportamento é idêntico ao histórico
    (inclusive o retorno cedo silencioso quando não há análise) e nada é
    retornado. Sem cobertura comprovada, o texto bloqueado é persistido E
    devolvido como Content: retornar um Content faz o ADK emitir um evento novo
    com esse conteúdo no lugar da saída do agente, então o consumidor a jusante
    enxerga o bloqueio — e não o APROVADO que o LLM possa ter escrito.

    Returns:
        None no caminho aprovado; o Content bloqueado caso contrário.
    """
    state = callback_context.state
    analysis_raw = state.get("review_analysis")

    if cobertura_comprovada(state):
        if analysis_raw is None:
            return None
        analysis = str(analysis_raw)
        if not analysis.strip():
            return None
        _salvar_relatorio(analysis)
        return None

    summary = state.get("task_iteration_summary")
    analysis = "" if analysis_raw is None else str(analysis_raw)
    texto_final = aplicar_gate_de_cobertura(analysis, summary)

    state["review_analysis"] = texto_final
    _salvar_relatorio(texto_final)
    return types.Content(role="model", parts=[types.Part(text=texto_final)])
