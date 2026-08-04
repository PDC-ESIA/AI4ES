"""Workflow HumanEval: benchmark de funções puras com loop coder <-> executor.

Pipeline: LoopAgent[he_coder <-> he_executor]
  - he_coder: implementa a função a partir do prompt HumanEval
  - he_executor: roda pytest localmente no host (mode=local, sem Docker)

Sem context_engineer (problemas HumanEval já são atômicos).
Sem reviewer (benchmark mede corretude via testes, não estilo).
"""

import os

from google.adk.agents import LoopAgent

from .he_coder import agent as _coder
from .he_executor import agent as _executor

agent = LoopAgent(
    name="humaneval_pipeline",
    description=(
        "Benchmark HumanEval: coder implementa função -> "
        "executor valida via pytest -> repete até sucesso ou max_iterations."
    ),
    max_iterations=int(os.environ.get("AI4ES_MAX_LOOP_ITERATIONS", "5")),
    sub_agents=[_coder, _executor],
)
