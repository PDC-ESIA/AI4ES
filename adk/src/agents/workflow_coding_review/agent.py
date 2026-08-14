"""Workflow coding_review: pipeline enxuto de codificação com revisão.

Pipeline: context_engineer -> memory_feedforward -> LoopAgent[coder ↔ executor] -> reviewer
  - context_engineer: fragmenta requisitos em tasks contextualizadas
  - memory_feedforward: [PoC] consulta o mem0 por lições de execuções
            passadas para a mesma stack, injeta em state["memory_context"]
  - coder: implementa código a partir das tasks (workspace isolado)
            Em re-execução: corrige código baseado no erro do executor
  - executor: builda e roda código em Docker
              Se sucesso: exit_loop → pipeline segue para reviewer
              Se falha: reporta erro → loop volta ao coder
  - reviewer: analisa (4 camadas), persiste relatório de revisão e
            [PoC] grava no mem0 as lições desta execução

O LoopAgent garante que o código produzido é EXECUTÁVEL antes de seguir
para revisão. O teto de iterações é o default 5 (1 tentativa + 4 retries),
parametrizável pela env var `AI4ES_MAX_LOOP_ITERATIONS`.

Cada sub-agente é definido em seu próprio módulo (cr_*.py) para manter
este arquivo slim e facilitar manutenção independente.
"""

import os

from google.adk.agents import LoopAgent, SequentialAgent

from .context_engineer import agent as _context_engineer
from .memory_feedforward import agent as _memory_feedforward
from .coder import agent as _coder
from .executor.agent import agent as _executor
from .reviewer.agent import agent as _reviewer

# ---------------------------------------------------------------------------
# Loop de codificação + execução: coder produz/corrige → executor testa
# O loop encerra quando o executor chama exit_loop (aprovação ou estagnação) ou
# após max_iterations (fallback — código segue para review mesmo com falha).
# O teto default é 5, sobrescrevível pela env var AI4ES_MAX_LOOP_ITERATIONS
# (mesmo padrão de configuração por ambiente usado para ADK_LLM_MODEL).
# ---------------------------------------------------------------------------
_code_execute_loop = LoopAgent(
    name="code_execute_loop",
    description=(
        "Loop de codificação e execução: "
        "coder produz/corrige código → executor testa em Docker → "
        "repete até sucesso ou max_iterations."
    ),
    max_iterations=int(os.environ.get("AI4ES_MAX_LOOP_ITERATIONS", "5")),
    sub_agents=[_coder, _executor],
)

# ---------------------------------------------------------------------------
# Pipeline completo (SequentialAgent)
# ---------------------------------------------------------------------------
agent = SequentialAgent(
    name="coding_review_pipeline",
    description=(
        "Pipeline enxuto de codificação com revisão: "
        "contexto → [codificação ↔ execução Docker] → revisão."
    ),
    sub_agents=[_context_engineer, _memory_feedforward, _code_execute_loop, _reviewer],
)
