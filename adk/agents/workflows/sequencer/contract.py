"""Contrato universal do pipeline SDLC.

Define a ordem canônica dos estágios, mapeia cada output_key ao seu
schema Pydantic e expõe validate_state para inspeção do session.state
após cada etapa do SequentialAgent.
"""

from __future__ import annotations

from typing import Any

from agents.roles.requirements.schemas import RequirementsOutput
from agents.roles.architect.schemas import ArchitectureOutput
from agents.roles.test_planner.schemas import TestPlanOutput
from agents.roles.reviewer.schemas import ReviewOutput
from agents.roles.finalizer.schemas import FinalizationOutput

# ---------------------------------------------------------------------------
# Contrato canônico do pipeline
# ---------------------------------------------------------------------------
# O coder_agent e o review_agent não declaram output_schema no LlmAgent
# (usam texto livre via output_key). Os schemas existem nos módulos
# schemas.py respectivos e são referenciados aqui apenas para documentação
# e validação opcional downstream.
# ---------------------------------------------------------------------------

PIPELINE_STAGES: list[dict[str, Any]] = [
    {
        "name": "requirements_agent",
        "output_key": "requirements",
        "output_schema": RequirementsOutput,
        "validates_schema": True,
    },
    {
        "name": "architecture_agent",
        "output_key": "architecture",
        "output_schema": ArchitectureOutput,
        "validates_schema": True,
    },
    {
        "name": "test_planning_agent",
        "output_key": "test_plan",
        "output_schema": TestPlanOutput,
        "validates_schema": True,
    },
    {
        "name": "coder_agent",
        "output_key": "implementation",
        "output_schema": None,  # texto livre — sem output_schema no LlmAgent
        "validates_schema": False,
    },
    {
        "name": "review_agent",
        "output_key": "review",
        "output_schema": ReviewOutput,
        "validates_schema": True,
    },
    {
        "name": "finalization_agent",
        "output_key": "finalization",
        "output_schema": FinalizationOutput,
        "validates_schema": True,
    },
]

# Lookup rápido: output_key → estágio
_STAGE_BY_KEY: dict[str, dict[str, Any]] = {s["output_key"]: s for s in PIPELINE_STAGES}


def validate_state(
    session_state: dict[str, Any],
    up_to_stage: int | None = None,
) -> tuple[bool, list[str]]:
    """Verifica se o session.state contém todas as output_keys esperadas.

    Args:
        session_state: O dicionário ``session.state`` do ADK.
        up_to_stage: Índice (0-based) do último estágio a verificar.
            ``None`` valida o pipeline completo.

    Returns:
        Tupla ``(sucesso, chaves_ausentes)``.
        - ``sucesso`` é ``True`` quando todas as chaves estão presentes.
        - ``chaves_ausentes`` lista as output_keys faltando.
    """
    stages = (
        PIPELINE_STAGES[: up_to_stage + 1]
        if up_to_stage is not None
        else PIPELINE_STAGES
    )
    missing: list[str] = [
        stage["output_key"]
        for stage in stages
        if stage["output_key"] not in session_state
    ]
    return (len(missing) == 0, missing)


def stage_index(identifier: str) -> int:
    """Retorna o índice (0-based) de um estágio por agent name ou output_key."""
    for i, stage in enumerate(PIPELINE_STAGES):
        if stage["name"] == identifier or stage["output_key"] == identifier:
            return i
    raise KeyError(
        f"'{identifier}' não encontrado em PIPELINE_STAGES "
        f"(verifique 'name' e 'output_key')."
    )
