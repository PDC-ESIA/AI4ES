"""Workflow coding_review: pipeline enxuto de codificação com revisão.

Pipeline: context_engineer -> LoopAgent[coder ↔ executor] -> reviewer
  - context_engineer: fragmenta requisitos em tasks contextualizadas
  - coder: implementa código a partir das tasks (workspace isolado)
            Em re-execução: corrige código baseado no erro do executor
  - executor: builda e roda código em Docker
              Se sucesso: exit_loop → pipeline segue para reviewer
              Se falha: reporta erro → loop volta ao coder
  - reviewer: analisa (4 camadas) e persiste relatório de revisão

O LoopAgent garante que o código produzido é EXECUTÁVEL antes de seguir
para revisão. O teto de iterações é o default 5 (1 tentativa + 4 retries),
parametrizável pela env var `AI4ES_MAX_LOOP_ITERATIONS`.

Cada sub-agente é definido em seu próprio módulo (cr_*.py) para manter
este arquivo slim e facilitar manutenção independente.
"""

import os

from google.adk.agents import LoopAgent, SequentialAgent

from .cr_context_engineer import agent as _context_engineer
from .cr_coder import agent as _coder
from .cr_executor import agent as _executor
from .cr_reviewer import agent as _reviewer
from .task_iterator import TaskIterator

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
# Camada de iteração sobre as tasks: envolve o loop de correção e o roda UMA vez
# por task (ordem topológica estável). A política `fail_fast` para no primeiro
# fracasso; `continue_independent` preserva tasks sem dependências bloqueadas. O executor
# não sabe que existe uma fila — quem troca a task é esta camada (ver
# task_iterator.py). O max_iterations do loop passa a valer por-task.
# ---------------------------------------------------------------------------
_task_iterator = TaskIterator(
    name="task_iterator",
    description=(
        "Itera as tasks em ordem topológica estável, rodando o loop de "
        "codificação/execução uma vez por task conforme a política de falha."
    ),
    code_execute_loop=_code_execute_loop,
)

# ---------------------------------------------------------------------------
# Pipeline completo (SequentialAgent)
# ---------------------------------------------------------------------------
agent = SequentialAgent(
    name="coding_review_pipeline",
    description=(
        "Pipeline enxuto de codificação com revisão: "
        "contexto → [iteração de tasks: codificação ↔ execução Docker] → revisão."
    ),
    sub_agents=[_context_engineer, _task_iterator, _reviewer],
)
