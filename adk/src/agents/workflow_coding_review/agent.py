"""Workflow coding_review: pipeline enxuto de codificação com revisão.

Pipeline: context_engineer -> memory_feedforward -> TaskIterator[LoopAgent[coder ↔ executor]] -> reviewer
  - context_engineer: fragmenta requisitos em tasks contextualizadas
  - memory_feedforward: consulta o mem0 por lições de execuções
            passadas para a mesma stack, injeta em state["memory_context"]
  - task_iterator: itera as tasks POR CÓDIGO, escopando `state['task_id']` a
            cada uma e invocando o loop uma vez por task (issue #369). Agrega o
            desfecho em `state['task_iteration_summary']`.
  - coder: implementa código a partir das tasks (workspace isolado)
            Em re-execução: corrige código baseado no erro do executor
  - executor: roda o harness e obedece ao veredito do validador
              Se aprovado (ou estagnação): exit_loop → encerra o loop da task
              Se reprovado: ErrorReport → loop volta ao coder
  - reviewer: analisa (4 camadas), persiste relatório de revisão e grava no mem0 as lições desta execução

O LoopAgent garante que o código produzido é EXECUTÁVEL antes de seguir
para revisão. O teto de iterações é o default 5 (1 tentativa + 4 retries),
parametrizável pela env var `AI4ES_MAX_LOOP_ITERATIONS` — e vale POR TASK,
já que o iterator invoca o loop uma vez para cada uma.

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
from .task_iterator import TaskIterator
from .manifest import emit_coding_manifest


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
        "coder produz/corrige código → executor roda o harness → "
        "repete até o veredito aprovar, estagnar ou atingir max_iterations."
    ),
    max_iterations=int(os.environ.get("AI4ES_MAX_LOOP_ITERATIONS", "5")),
    sub_agents=[_coder, _executor],
)

# ---------------------------------------------------------------------------
# Iterador determinístico de tasks: adota o loop como único sub-agente e o
# invoca uma vez por task. O loop NÃO é passado ao SequentialAgent do topo —
# quem o executa é o iterator, e um sub-agente só pode ter um parent.
# ---------------------------------------------------------------------------
_task_iterator = TaskIterator(
    name="task_iterator",
    description=(
        "Itera determinísticamente todas as tasks do context_engineer, "
        "escopando task_id por código e invocando o loop de codificação uma "
        "vez por task; agrega cobertura em task_iteration_summary."
    ),
    sub_agents=[_code_execute_loop],
)

# ---------------------------------------------------------------------------
# Pipeline completo (SequentialAgent)
# ---------------------------------------------------------------------------
agent = SequentialAgent(
    name="coding_review_pipeline",
    description=(
        "Pipeline enxuto de codificação com revisão: "
        "contexto → [por task: codificação ↔ execução] → revisão → manifesto."
    ),
    sub_agents=[_context_engineer, _memory_feedforward, _task_iterator, _reviewer],
    after_agent_callback=emit_coding_manifest,
)
