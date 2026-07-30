"""CorrectionSpec — feedback estruturado (spec-driven) do executor pro coder.

Quando o `implementation_validator` reprova um Work Item, o `cr_executor_agent`
(ver `cr_executor.py`) é instruído (`src/agents/executor/prompt.py`, passo 3)
a emitir um markdown de formato fixo com um bloco `### CORRECAO` por critério
não atendido/inconclusivo — em vez da prosa livre usada anteriormente.

Este módulo é o `after_agent_callback` que faz o parse desse markdown e o
CONFERE contra o ValidationVerdict REAL (nunca contra o que o próprio LLM
disse sobre si mesmo) antes de montar o `CorrectionSpec` final que o coder vai
consumir na próxima iteração — mesma filosofia de `implementation_validator`
(`_parse_e_aplicar_politica`/`montar_veredito`): o LLM nunca decide sozinho o
que vira "verdade".

O veredito real chega via `callback_context.state["validation"]` — escrito
pelo próprio `after_agent_callback` do `implementation_validator` quando ele
roda como `AgentTool` dentro do turno do executor. `AgentTool.run_async`
encaminha `event.actions.state_delta` do sub-agente pro `tool_context.state`
do agente pai a cada evento (google/adk/tools/agent_tool.py), por isso essa
chave chega aqui mesmo sem o executor nunca ter escrito nela diretamente.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from google.genai import types

from src.agents.executor.schemas import CorrectionItem, CorrectionSpec
from src.agents.implementation_validator.schemas import CriterionStatus

logger = logging.getLogger(__name__)

_BLOCKING_RE = re.compile(r"^BLOCKING_REASON:\s*(?P<reason>.+?)\s*$", re.MULTILINE)

_CORRECAO_RE = re.compile(
    r"### CORRECAO\s*\n"
    r"CRITERIO:\s*(?P<criterio>.+)\s*\n"
    r"CAUSA_RAIZ:\s*(?P<causa>.+)\s*\n"
    r"ARQUIVOS_AFETADOS:\s*(?P<arquivos>.+)\s*\n"
    r"MUDANCA_REQUERIDA:\s*(?P<mudanca>.+)\s*\n"
    r"(?:EVIDENCIA_REF:\s*(?P<evidencia>.+)\s*\n?)?",
    re.IGNORECASE,
)


def _parse_arquivos(raw: str) -> list[str]:
    """`"a.py, b.py"` -> `["a.py", "b.py"]`; `"-"`/vazio -> `[]`."""
    raw = (raw or "").strip()
    if not raw or raw == "-":
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def _evidencia(
    bloco_evidencia: Optional[str], fallback: Optional[str]
) -> Optional[str]:
    """Usa a evidência do bloco do LLM, exceto quando vazia/"-" — aí usa o
    evidence_ref do CriterionVerdict real, se houver."""
    evid = (bloco_evidencia or "").strip()
    return evid if evid and evid != "-" else fallback


def _status_seguro(valor: str) -> CriterionStatus:
    """CriterionStatus a partir de string do veredito real, com fallback
    conservador para INCONCLUSIVO se o valor for inesperado."""
    try:
        return CriterionStatus(valor)
    except ValueError:
        return CriterionStatus.INCONCLUSIVO


def _como_content(spec: CorrectionSpec) -> types.Content:
    """Serializa a CorrectionSpec como saída final do agente (mesma técnica de
    `implementation_validator._como_content`: o callback substitui a resposta
    do agente, então o coder recebe o JSON validado, não a prosa/markdown cru)."""
    return types.Content(
        role="model",
        parts=[types.Part(text=json.dumps(spec.model_dump(), ensure_ascii=False))],
    )


def parse_e_montar_correction_spec(callback_context) -> Optional[types.Content]:
    """`after_agent_callback` do `cr_executor_agent`.

    Retorna `None` (mantém a saída original do executor) quando:
    - o veredito real é 'aprovado' (nada a corrigir);
    - nenhum bloco `### CORRECAO` foi encontrado — cobre tanto o caminho de
      aprovação quanto o de ESTAGNAÇÃO (passo 4 do prompt, que usa outro
      formato de propósito e já chama exit_loop, então este execution_result
      nunca é lido pelo coder mesmo). Se o LLM simplesmente ignorar o formato
      num reprovado real "normal", o efeito é degradar de volta pra prosa
      livre (comportamento pré-existente) — nunca um crash.

    Caso contrário, monta e retorna o `CorrectionSpec` (JSON) substituindo a
    saída do turno.
    """
    raw = callback_context.state.get("execution_result", "") or ""

    blocos = list(_CORRECAO_RE.finditer(raw))
    if not blocos:
        return None

    m = _BLOCKING_RE.search(raw)
    blocking_reason_llm = m.group("reason").strip() if m else None

    validation = callback_context.state.get("validation")
    if not validation:
        # Mecanismo de propagação de state não disparou (não deveria acontecer
        # em produção — ver tests/unit/test_cr_executor_correction_spec.py).
        # Fail-safe conservador: monta a partir só do que o LLM escreveu, sem
        # cross-check — nunca descarta o diagnóstico silenciosamente.
        logger.warning(
            "cr_executor_correction: state['validation'] ausente; "
            "montando CorrectionSpec sem validação cruzada contra o veredito real."
        )
        try:
            items = [
                CorrectionItem(
                    criterion=b.group("criterio").strip(),
                    status=CriterionStatus.INCONCLUSIVO,
                    root_cause=b.group("causa").strip(),
                    affected_files=_parse_arquivos(b.group("arquivos")),
                    required_change=b.group("mudanca").strip(),
                    evidence_ref=_evidencia(b.group("evidencia"), None),
                )
                for b in blocos
            ]
            spec = CorrectionSpec(
                work_item_id="desconhecido",
                blocking_reason=blocking_reason_llm,
                items=items,
            )
        except Exception:
            logger.exception(
                "cr_executor_correction: falha ao montar CorrectionSpec (fallback)"
            )
            return None
        callback_context.state["correction_spec"] = spec.model_dump()
        return _como_content(spec)

    if validation.get("status") != "reprovado":
        # Aprovado: nada a corrigir, mantém a saída original do executor.
        return None

    # ---- validação cruzada contra o ValidationVerdict REAL ----
    diagnosticados = {b.group("criterio").strip(): b for b in blocos}

    items: list[CorrectionItem] = []
    for cv in validation.get("criteria_verdicts", []) or []:
        status = cv.get("status")
        if status == "atendido":
            continue  # critério atendido não precisa de correção

        criterio = cv.get("criterion", "")
        bloco = diagnosticados.get(criterio)
        if bloco is not None:
            items.append(
                CorrectionItem(
                    criterion=criterio,
                    status=_status_seguro(status),
                    root_cause=bloco.group("causa").strip(),
                    affected_files=_parse_arquivos(bloco.group("arquivos")),
                    required_change=bloco.group("mudanca").strip(),
                    evidence_ref=_evidencia(
                        bloco.group("evidencia"), cv.get("evidence_ref")
                    ),
                )
            )
        else:
            # Critério real não atendido, mas o executor não o diagnosticou —
            # spec de fallback em vez de deixá-lo sumir silenciosamente (mesma
            # filosofia conservadora de `montar_veredito`).
            items.append(
                CorrectionItem(
                    criterion=criterio,
                    status=_status_seguro(status),
                    root_cause="Não diagnosticado pelo executor.",
                    affected_files=[],
                    required_change="Revisar manualmente — sem diagnóstico automático.",
                    evidence_ref=cv.get("evidence_ref"),
                )
            )

    try:
        spec = CorrectionSpec(
            work_item_id=validation.get("work_item_id", "desconhecido"),
            blocking_reason=validation.get("blocking_reason") or blocking_reason_llm,
            items=items,
        )
    except Exception:
        logger.exception("cr_executor_correction: falha ao montar CorrectionSpec")
        return None

    callback_context.state["correction_spec"] = spec.model_dump()
    return _como_content(spec)
