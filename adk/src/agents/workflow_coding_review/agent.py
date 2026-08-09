"""Workflow coding_review: pipeline enxuto de codificação com revisão.

Pipeline: context_engineer -> LoopAgent[coder → executor → checker] -> reviewer
  - context_engineer: fragmenta requisitos em tasks contextualizadas
  - coder: implementa código a partir das tasks (workspace isolado)
            Em re-execução: corrige código baseado no erro do executor
  - executor: builda e roda código em Docker, emite ErrorReport determinístico
  - convergence_checker: decide, sem LLM, se o loop continua ou encerra
              (early-stopping por progresso). É a fonte REAL de terminação.
  - reviewer: analisa (4 camadas) e persiste relatório de revisão

O LoopAgent garante que o código produzido é EXECUTÁVEL antes de seguir
para revisão. A terminação do loop saiu do LLM: quem encerra é o
convergence_checker (emite escalate quando convergiu/estagnou). O
`max_iterations` (env `AI4ES_LOOP_MAX_ITERATIONS`, default 300) é apenas a
rede de segurança final.

Cada sub-agente é definido em seu próprio package (context_engineer/, coder/,
executor/, convergence_checker/, reviewer/) para manter este arquivo slim e
facilitar manutenção independente.
"""

import os

from google.adk.agents import LoopAgent, SequentialAgent

from .context_engineer.agent import agent as _context_engineer
from .coder.agent import agent as _coder
from .executor.agent import agent as _executor
from .convergence_checker.agent import agent as _convergence_checker
from .reviewer.agent import agent as _reviewer

# ---------------------------------------------------------------------------
# Loop de codificação + execução + convergência:
#   coder produz/corrige → executor testa → checker decide continuar/encerrar.
# O loop encerra quando o convergence_checker emite escalate (convergência,
# estagnação dura ou sem progresso) ou, na pior das hipóteses, ao atingir o teto
# max_iterations (rede de segurança). O executor NÃO controla mais a terminação.
# O teto default é 300, sobrescrevível pela env var AI4ES_LOOP_MAX_ITERATIONS
# (mesmo padrão de configuração por ambiente usado para ADK_LLM_MODEL).
# ---------------------------------------------------------------------------
_code_execute_loop = LoopAgent(
    name="code_execute_loop",
    description=(
        "Loop de codificação e execução: "
        "coder produz/corrige código → executor testa em Docker → "
        "convergence_checker decide continuar ou encerrar (early-stopping)."
    ),
    max_iterations=int(os.environ.get("AI4ES_LOOP_MAX_ITERATIONS", "300")),
    sub_agents=[_coder, _executor, _convergence_checker],
)

# ---------------------------------------------------------------------------
# Pipeline completo (SequentialAgent)
# ---------------------------------------------------------------------------
agent = SequentialAgent(
    name="coding_review_pipeline",
    description=(
        "Pipeline enxuto de codificação com revisão: "
        "contexto → [codificação → execução Docker → convergência] → revisão."
    ),
    sub_agents=[_context_engineer, _code_execute_loop, _reviewer],
)
