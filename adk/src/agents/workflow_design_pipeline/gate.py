"""Gate determinístico entre a Etapa 1 (análise técnica) e a Etapa 2+
(especialistas) do pipeline de design.

Problema que este módulo resolve: `design_pipeline` (`agent.py`) é um
`SequentialAgent` com `sub_agents=[pipeline_controller, parallel_branch]`.
Um `SequentialAgent` roda cada sub-agente incondicionalmente — não existe,
por padrão, nenhum código que impeça `parallel_branch` de rodar quando
`pipeline_controller` detecta (via `validate_analysis_sections`) que a
análise técnica está incompleta e encerra com "PIPELINE_ERROR" em vez de
"PIPELINE_STAGE_1_COMPLETE".

Até aqui, essa barreira existia só como convenção textual: a `description`
de `parallel_branch` instrui "não ativar enquanto o status não for
PIPELINE_STAGE_1_COMPLETE", mas nada verificava isso. Numa run real
(2026-08-23), `pipeline_controller` corretamente recusou avançar — e mesmo
assim `parallel_branch` rodou por inteiro (prototyping_specialist,
mermaid_specialist, validator, markdown_specialist). O pipeline só não
produziu artefatos quebrados porque cada especialista, na própria avaliação
da LLM, percebeu a análise incompleta e recusou o trabalho — uma proteção
narrativa e dependente de modelo, não uma regra garantida.

Este módulo substitui essa proteção por uma checagem de código, no mesmo
espírito de `manifest.py` (nunca confiar no autorrelato de uma LLM) e de
`workflow_coding_review/executor/agent.py::recusar_execucao_incompleta`
(gate estrutural via `before_agent_callback`, mesmo padrão adotado aqui).

Diferença deliberada em relação a `manifest.py`: o emissor de manifesto
nunca derruba o pipeline (falha vira log, degrada para "partial"/"blocked").
Este gate é o oposto — sua função é impedir trabalho sobre um estado
inválido ou desconhecido, então falha FECHADA: se a checagem não puder
ser executada, os especialistas são bloqueados, nunca liberados às cegas.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from google.genai import types

from shared.tools.design_filesystem import validate_analysis_sections

from .manifest import _design_root

logger = logging.getLogger(__name__)

_ANALYSIS_GLOB = "analise_tecnica_*.md"


def _analysis_completeness(design_root: Path) -> tuple[bool, str]:
    """Verifica, por código, se toda análise técnica publicada está completa.

    Cobre dois casos, ambos "não pronto para os especialistas": nenhum
    arquivo de análise foi publicado ainda, ou algum arquivo publicado está
    incompleto (seções ausentes/vazias) segundo a mesma checagem estrutural
    que `pipeline_controller` já usa via `validate_analysis_sections`.
    """
    analysis_dir = design_root / "analysis"
    if not analysis_dir.exists():
        return False, "a pasta design/analysis/ ainda não existe."

    files = sorted(analysis_dir.glob(_ANALYSIS_GLOB))
    if not files:
        return False, "nenhum arquivo 'analise_tecnica_*.md' encontrado em design/analysis/."

    base_dir = str(design_root)
    for f in files:
        result = validate_analysis_sections(
            f.name, caller="parallel_branch_gate", base_dir=base_dir
        )
        if result.get("status") != "ok":
            return False, f"falha ao validar {f.name}: {result.get('error')}."
        if not result.get("complete"):
            missing = result.get("missing_sections") or []
            empty = result.get("empty_sections") or []
            return False, (
                f"{f.name} está incompleto — seções ausentes: {missing}, "
                f"seções vazias: {empty}."
            )

    return True, ""


def gate_parallel_branch(callback_context: Any) -> Optional[types.Content]:
    """`before_agent_callback` de `parallel_branch`.

    Retorna `None` — deixa o `ParallelAgent` rodar normalmente
    (`prototyping_specialist` e `diagram_flow`) — apenas quando a análise
    técnica está estruturalmente completa. Qualquer outro caso, incluindo
    falha da própria checagem, retorna `types.Content`: por contrato do ADK
    (`BaseAgent._handle_before_agent_callback`), isso marca a invocação como
    encerrada e cancela a execução do agente e de todos os seus sub-agentes.
    """
    try:
        ok, motivo = _analysis_completeness(_design_root())
    except Exception as exc:  # gate falha fechado — nunca libera às cegas
        logger.warning("[design_gate] falha ao checar completude da análise: %s", exc)
        ok, motivo = False, f"falha ao verificar completude da análise técnica ({exc})."

    if ok:
        return None

    logger.info("[design_gate] bloqueando parallel_branch: %s", motivo)
    return types.Content(
        role="model",
        parts=[types.Part(text=(
            "PIPELINE_ERROR: análise técnica incompleta ou ausente — "
            f"{motivo} Os especialistas de protótipo, diagrama e relatório "
            "não foram acionados nesta rodada."
        ))],
    )
