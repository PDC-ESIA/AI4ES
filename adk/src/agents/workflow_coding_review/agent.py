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
              Se aprovado: encerra o loop da task
              Se reprovado: ErrorReport → loop volta ao coder, a menos que a
              política de progresso detecte travamento e encerre
  - reviewer: analisa (4 camadas) e persiste relatório de revisão e grava no mem0 as lições desta execução


O LoopAgent garante que o código produzido é EXECUTÁVEL antes de seguir
para revisão. Quem decide quando o loop para é a POLÍTICA DE PROGRESSO
(executor/loop_policy.py, issue #394), não mais a contagem de iterações: o teto
do LoopAgent virou rede de segurança. Vale POR TASK, já que o iterator invoca o
loop uma vez para cada uma.

Cada sub-agente é definido em seu próprio módulo (cr_*.py) para manter
este arquivo slim e facilitar manutenção independente.
"""

from google.adk.agents import LoopAgent, SequentialAgent

from shared.pipeline_flags import aceite_independente, contrato_web, jornada

from .context_engineer import agent as _context_engineer
from .memory_feedforward import agent as _memory_feedforward
from .acceptance.agent import gate as _acceptance_gate
from .contract.agent import author as _contract_author
from .coder import agent as _coder
from .journey.agent import author as _journey_author
from .executor.agent import agent as _executor
from .executor.loop_policy import config_inteiro
from .reviewer.agent import agent as _reviewer
from .task_iterator import TaskIterator
from .manifest import emit_coding_manifest


# Teto alto de propósito: a política de progresso encerra o loop muito antes em
# operação normal. Valor de partida — a issue #394 deixa a calibração fora de
# escopo, e ele é sobrescrevível por `AI4ES_MAX_LOOP_ITERATIONS`.
_TETO_SEGURANCA = 20

# ---------------------------------------------------------------------------
# Loop de codificação + execução: coder produz/corrige → executor testa
#
# O loop encerra por PROGRESSO, não por contagem: a política em
# `executor/loop_policy.py` mede a nota de cada rodada e sinaliza `escalate`
# quando a tarefa é aprovada ou quando a nota empaca (issue #394).
#
# `max_iterations` permanece — mas como REDE DE SEGURANÇA, não como controle
# esperado. Ele protege contra um defeito na própria política (uma exceção no
# cálculo da nota, um empate que o critério de platô não cubra, oscilação por
# teste instável que impeça o platô de fechar): é avaliado pelo `while` do
# LoopAgent, fora do nosso callback, e portanto não depende de nada que a
# política precise executar corretamente. Zerá-lo ou removê-lo faria a rede
# depender exatamente do código contra o qual ela protege.
#
# Os dois mecanismos são independentes e o ADK já os compõe com OR
# (`loop_agent.py`: `while (not max_iterations or times_looped < max_iterations)
# and not should_exit`). A redundância é a propriedade desejada, não duplicação
# a eliminar. Por isso o teto sobe bem acima do antigo 5: em operação normal a
# política encerra muito antes, e chegar aqui é sinal de bug — não de tarefa
# difícil.
# ---------------------------------------------------------------------------
_code_execute_loop = LoopAgent(
    name="code_execute_loop",
    description=(
        "Loop de codificação e execução: "
        "coder produz/corrige código → executor roda o harness → "
        "repete até o veredito aprovar ou a nota de progresso empacar; "
        "max_iterations é apenas a rede de segurança."
    ),
    max_iterations=config_inteiro(
        "AI4ES_MAX_LOOP_ITERATIONS", _TETO_SEGURANCA, minimo=1
    ),
    # Com `AI4ES_ACEITE_INDEPENDENTE` (lida no import), o autor de testes de
    # aceite entra entre o coder e o executor; ele próprio decide se roda na
    # rodada (uma vez por task). Desligada, o loop é o histórico.
    sub_agents=(
        [_coder, _acceptance_gate, _executor]
        if aceite_independente()
        else [_coder, _executor]
    ),
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
    # Com `AI4ES_JORNADA` (lida no import), o autor do teste de jornada é o
    # segundo sub-agente: roda uma vez, depois da última task.
    # Com `AI4ES_CONTRATO_WEB`, o autor do contrato de interface (produto web)
    # roda uma vez, antes da primeira task. Os autores são achados pelo nome.
    sub_agents=(
        [_code_execute_loop]
        + ([_journey_author] if jornada() else [])
        + ([_contract_author] if contrato_web() else [])
    ),
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
