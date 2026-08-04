"""Montagem determinística do `ErrorReport` entregue ao coder.

Relatório que substitui a prosa do LLM quando o veredito é 'reprovado'. É
montado a partir de duas fontes que JÁ existem, sem nenhuma síntese:
- `state['validation']` — o ValidationVerdict real, escrito pela política
  determinística do `implementation_validator`;
- o ExecutionReport em disco (`state['report_path']`, gravado pelo harness) —
  de onde saem os estágios em falha com sua EVIDÊNCIA BRUTA (logs, tracebacks).

O ErrorReport diz o QUE falhou e mostra o material bruto do POR QUÊ. Ele NÃO
prescreve correção: diagnosticar causa raiz, escolher arquivos e decidir a
mudança é trabalho do coder — não do executor.

Vive aqui, e não dentro do `ExecutorOrchestrator`, porque é um HOOK injetável:
quem instancia a orquestração escolhe o builder (ou nenhum). Assim a decisão de
encerrar o loop — que é do orquestrador — fica separada do formato do relatório
devolvido ao coder.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from google.genai import types

from src.agents.executor.schemas import ErrorReport, FailedCriterion, FailedStage
from src.agents.implementation_validator.agent import _report_path_valido

logger = logging.getLogger(__name__)

# Marcador emitido no encerramento por ESTAGNAÇÃO. Nesse caminho o resumo
# `bloqueado` é destinado ao reviewer (o loop já vai encerrar), então o builder
# NÃO o substitui pelo ErrorReport. O protocolo que PRODUZ esse marcador ainda
# não existe no orquestrador determinístico (Fatia B2); a checagem fica aqui
# para que o contrato não mude quando ele chegar.
_MARCADOR_ESTAGNACAO = "STATUS: bloqueado"

# Estágios apenas PULADOS são consequência em cascata do que falhou antes
# ("Abortado: ..."), não trazem evidência útil — só falha/erro entram no report.
_STATUS_COM_EVIDENCIA = ("falha", "erro")


def _como_content(report: ErrorReport) -> types.Content:
    """Serializa o ErrorReport como saída do turno do executor."""
    return types.Content(
        role="model",
        parts=[types.Part(text=json.dumps(report.model_dump(), ensure_ascii=False))],
    )


def _carregar_execution_report(callback_context) -> dict:
    """Lê o ExecutionReport do disco a partir do `report_path` do state.

    O caminho é validado com o mesmo helper estrito do validador: precisa ser
    `<task_id>.report.json` dentro do workspace do cr_executor. Em qualquer
    falha devolve {} — o ErrorReport ainda sai, só sem a seção de estágios (o
    veredito, que é o essencial, nunca depende do disco).
    """
    caminho = callback_context.state.get("report_path")
    task_id = callback_context.state.get("task_id")
    if not caminho:
        return {}
    if not _report_path_valido(caminho, task_id or ""):
        logger.warning(
            "executor: report_path recusado pela validação de workspace (%s); "
            "ErrorReport seguirá sem a evidência de estágios.",
            caminho,
        )
        return {}
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except Exception:
        logger.warning("executor: falha ao ler o ExecutionReport em %s", caminho)
        return {}


def montar_error_report(callback_context) -> Optional[types.Content]:
    """Monta o ErrorReport determinístico a partir do state da invocação.

    Recebe qualquer contexto com `.state` de leitura/escrita — o
    `CallbackContext` que o `ExecutorOrchestrator` constrói a partir do seu
    `InvocationContext` serve, assim como o `callback_context` de um
    `after_agent_callback`.

    Retorna `None` (nenhum relatório a emitir) quando:
    - `state['validation']` está ausente — o mecanismo de propagação não
      disparou; não emite relatório vazio;
    - o veredito real é 'aprovado' — não há erro a relatar;
    - o turno é o encerramento por ESTAGNAÇÃO — o resumo `bloqueado` é destinado
      ao reviewer e não pode ser sobrescrito.
    """
    validation = callback_context.state.get("validation")
    if not validation:
        logger.warning(
            "executor: state['validation'] ausente; nenhum ErrorReport "
            "determinístico nesta iteração."
        )
        return None

    if validation.get("status") != "reprovado":
        return None

    raw = callback_context.state.get("execution_result", "") or ""
    if _MARCADOR_ESTAGNACAO.casefold() in raw.casefold():
        return None

    exec_report = _carregar_execution_report(callback_context)

    criterios = [
        FailedCriterion(
            criterion=cv.get("criterion", ""),
            status=cv.get("status", ""),
            reasoning=cv.get("reasoning", ""),
            evidence_ref=cv.get("evidence_ref"),
        )
        for cv in validation.get("criteria_verdicts", [])
        if cv.get("status") != "atendido"
    ]

    estagios = [
        FailedStage(
            stage=s.get("stage", ""),
            status=s.get("status", ""),
            error_code=s.get("error_code"),
            summary=s.get("summary", ""),
            evidence=s.get("evidence") or {},
        )
        for s in exec_report.get("stages", [])
        if s.get("status") in _STATUS_COM_EVIDENCIA
    ]

    try:
        report = ErrorReport(
            work_item_id=validation.get("work_item_id")
            or exec_report.get("work_item_id", "desconhecido"),
            iteration=exec_report.get("iteration"),
            verdict_status=validation.get("status", "reprovado"),
            blocking_reason=validation.get("blocking_reason"),
            failed_criteria=criterios,
            failed_stages=estagios,
            report_path=callback_context.state.get("report_path"),
        )
    except Exception:
        logger.exception("executor: falha ao montar o ErrorReport")
        return None

    callback_context.state["error_report"] = report.model_dump()
    return _como_content(report)
