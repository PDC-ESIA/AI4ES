"""Workflow coding_review: pipeline enxuto de codificação com revisão.

Pipeline: context_engineer -> coder -> reviewer
  - context_engineer: fragmenta requisitos em tasks contextualizadas
  - coder: implementa código a partir das tasks (workspace isolado)
  - reviewer: analisa (4 camadas) e persiste relatório de revisão

Cada sub-agente é definido em seu próprio módulo (cr_*.py) para manter
este arquivo slim e facilitar manutenção independente.
"""

from google.adk.agents import SequentialAgent

from .cr_context_engineer import agent as _context_engineer
from .cr_coder import agent as _coder
from .cr_reviewer import agent as _reviewer

agent = SequentialAgent(
    name="coding_review_pipeline",
    description=(
        "Pipeline enxuto de codificação com revisão: "
        "contexto → codificação → revisão."
    ),
    sub_agents=[_context_engineer, _coder, _reviewer],
)
