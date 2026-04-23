"""Contrato do pipeline SDLC — schemas Pydantic e validação de estado.

Consolida os ``output_schema`` e ``output_key`` dos 6 especialistas que
compõem o ``sdlc_pipeline`` (SequentialAgent).  Este módulo é a fonte
única de verdade sobre a ordem das etapas e o formato esperado em
``session.state`` após cada uma delas.
"""

from __future__ import annotations

from typing import Optional

from agents.roles.requirements.schemas import RequirementsOutput
from agents.roles.architect.schemas import ArchitectureOutput
from agents.roles.test_planner.schemas import TestPlanOutput
from agents.roles.coder.schemas import ImplementationOutput
from agents.roles.reviewer.schemas import ReviewOutput
from agents.roles.finalizer.schemas import FinalizationOutput

# ──────────────────────────────────────────────────────────────────────
# Estágios do pipeline — ordem idêntica à de sub_agents no
# agents/workflows/coding/agent.py
# ──────────────────────────────────────────────────────────────────────

PIPELINE_STAGES: list[dict] = [
    {
        "name": "requirements_agent",
        "output_key": "requirements",
        "output_schema": RequirementsOutput,
    },
    {
        "name": "architecture_agent",
        "output_key": "architecture",
        "output_schema": ArchitectureOutput,
    },
    {
        "name": "test_planning_agent",
        "output_key": "test_plan",
        "output_schema": TestPlanOutput,
    },
    {
        "name": "coder_agent",
        "output_key": "implementation",
        "output_schema": ImplementationOutput,  # declarado em schemas.py mas não vinculado ao agente
    },
    {
        "name": "review_agent",
        "output_key": "review",
        "output_schema": ReviewOutput,  # declarado em schemas.py mas não vinculado ao agente
    },
    {
        "name": "finalization_agent",
        "output_key": "finalization",
        "output_schema": FinalizationOutput,
    },
]


def validate_state(
    session_state: dict,
    up_to_stage: Optional[str] = None,
) -> tuple[bool, list[str]]:
    """Verifica se ``session_state`` contém as chaves esperadas.

    Parameters
    ----------
    session_state:
        Dicionário ``session.state`` do ADK.
    up_to_stage:
        Nome do agente até o qual validar (inclusive).  Se ``None``,
        valida todas as etapas do pipeline.

    Returns
    -------
    tuple[bool, list[str]]
        ``(True, [])`` se todas as chaves esperadas estão presentes.
        ``(False, [chaves_ausentes])`` caso contrário.
    """
    missing: list[str] = []

    for stage in PIPELINE_STAGES:
        key = stage["output_key"]
        if key not in session_state:
            missing.append(key)

        if up_to_stage is not None and stage["name"] == up_to_stage:
            break

        dado_salvo = session_state[key]
        schema_esperado = stage["output_schema"]
        
        try:
            schema_esperado.model_validate(dado_salvo)
        except Exception:
            missing.append(f"{key} (Formato Invalido)")

    return (len(missing) == 0, missing)
