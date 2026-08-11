"""Workflow coding_review: pipeline enxuto de codificação com revisão.

Pipeline: context_engineer -> coder inicial -> TaskIterator -> reviewer
  - context_engineer: fragmenta requisitos em tasks contextualizadas
    - coder inicial: cria o plano e implementa o sistema completo uma única vez
    - TaskIterator: valida cada task primeiro com o executor; quando reprova,
                                    roda LoopAgent[coder de correção → executor]
  - executor: builda e roda código em Docker
              Se sucesso: exit_loop → pipeline segue para reviewer
              Se falha: reporta erro → loop volta ao coder
  - reviewer: analisa (4 camadas) e persiste relatório de revisão

O executor faz a primeira tentativa sem intervenção do coder de correção. O
LoopAgent garante até 4 correções adicionais antes de seguir para revisão. O
teto total é o default 5 (1 tentativa + 4 retries),
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


def _preparar_construcao_inicial(callback_context):
    """Apresenta a fila inteira ao coder existente como um único contrato."""
    saida = callback_context.state.get("tasks") or {}
    tasks = saida.get("tasks", []) if isinstance(saida, dict) else []
    callback_context.state["current_task"] = {
        "id": "PROJECT-INITIAL",
        "description": "Implementar o sistema completo conforme todas as tasks.",
        "macro_context": saida.get("macro_context", {})
        if isinstance(saida, dict)
        else {},
        "tasks": tasks,
    }
    callback_context.state["current_task_index"] = 1
    callback_context.state["total_tasks"] = 1
    callback_context.state["project_initialized"] = False
    callback_context.state["execution_result"] = None
    return None


def _marcar_construcao_inicial_concluida(callback_context):
    callback_context.state["project_initialized"] = True
    return None


# Mesma implementação, tools e prompt do coder já existente. O clone só evita
# conflito de parent no ADK e recebe callbacks de preparação do state.
_initial_coder = _coder.clone(
    update={
        "name": "cr_initial_coder_agent",
        "description": "Implementa o sistema completo antes da validação por task.",
        "output_key": "initial_implementation",
        "before_agent_callback": _preparar_construcao_inicial,
        "after_agent_callback": _marcar_construcao_inicial_concluida,
    }
)

# ---------------------------------------------------------------------------
# Loop de correção + execução: coder corrige ErrorReport → executor testa
# O loop encerra quando o executor chama exit_loop (aprovação ou estagnação) ou
# após max_iterations (fallback — código segue para review mesmo com falha).
# O teto default é 5, sobrescrevível pela env var AI4ES_MAX_LOOP_ITERATIONS
# (mesmo padrão de configuração por ambiente usado para ADK_LLM_MODEL).
# ---------------------------------------------------------------------------
_max_executor_attempts = max(
    int(os.environ.get("AI4ES_MAX_LOOP_ITERATIONS", "5")), 1
)
_code_execute_loop = LoopAgent(
    name="code_execute_loop",
    description=(
        "Loop de correção e execução: "
        "coder corrige o ErrorReport → executor testa em Docker → "
        "repete até sucesso ou max_iterations."
    ),
    max_iterations=max(_max_executor_attempts - 1, 1),
    sub_agents=[_coder, _executor],
)

# ---------------------------------------------------------------------------
# Camada de validação por task: roda o executor antes do loop de correção. A
# política `fail_fast` para no primeiro fracasso; `continue_independent`
# preserva tasks sem dependências bloqueadas. O executor não sabe que existe
# uma fila — quem troca a task é esta camada (ver task_iterator.py).
# ---------------------------------------------------------------------------
_task_iterator = TaskIterator(
    name="task_iterator",
    description=(
        "Itera as tasks em ordem topológica estável, validando primeiro e "
        "acionando o loop de correção somente após reprovação."
    ),
    code_execute_loop=_code_execute_loop,
    initial_executor=_executor,
    max_executor_attempts=_max_executor_attempts,
)

# ---------------------------------------------------------------------------
# Pipeline completo (SequentialAgent)
# ---------------------------------------------------------------------------
agent = SequentialAgent(
    name="coding_review_pipeline",
    description=(
        "Pipeline enxuto de codificação com revisão: "
        "contexto → construção completa → validação/correção por task → revisão."
    ),
    sub_agents=[_context_engineer, _initial_coder, _task_iterator, _reviewer],
)
