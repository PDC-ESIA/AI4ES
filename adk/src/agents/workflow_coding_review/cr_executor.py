"""Executor dedicado ao workflow coding_review — espelho do executor consolidado.

Instância-espelho de `src/agents/executor/` (mesma ideia de cr_reviewer → reviewer):
NÃO é mais um `LlmAgent`. A orquestração (rodar o harness → acionar o validador →
decidir a continuidade do loop) é determinística, feita pelo `ExecutorOrchestrator`.
Sem LLM no topo, o veredito não tem como ser reinterpretado — a "salvaguarda" que
vivia em prosa no `executor/prompt.py` virou o próprio fluxo de controle. Deste
prompt só a `description` continua sendo reusada.

O encerramento do loop `[coder → executor]` depende EXCLUSIVAMENTE do veredito do
validador (`ValidationVerdict.status == 'aprovado'`), nunca do status técnico de
execução do harness. A outra saída é a ESTAGNAÇÃO (mesmo código e mesmo bloqueio
por 3 iterações consecutivas), que encerra com status `bloqueado` — NÃO é
aprovação. Ambos os caminhos são código no `ExecutorOrchestrator`, não prompt.

Relatório de erro ao coder (determinístico): quando o veredito é 'reprovado', o
`error_report_builder` injetado (`montar_error_report`, de
`executor/error_report.py`) devolve ao coder um `ErrorReport` — o QUE falhou e a
EVIDÊNCIA BRUTA do POR QUÊ (logs, tracebacks), sem síntese do LLM. Ele NÃO
prescreve correção: diagnosticar causa raiz e decidir a mudança é do coder.

Instância PRÓPRIA do validador via `criar_agente()`: como sub-agente ele ganha
`parent_agent`, e o ADK exige parent único em `sub_agents` — reusar o singleton de
módulo (ou a instância que o executor consolidado já registrou) levantaria
`ValueError` ao tentar adotar um segundo parent.

Binding ao workspace do workflow: o harness já resolve, em tempo de CHAMADA, os
seus base_dirs default — coder/src (get_agent_workspace("cr_coder"), entrada do
coder), coder/execution ("cr_executor", saída da execução) e coder/tasks
("cr_context_engineer", a Task). Esses são exatamente os diretórios deste
workflow; por isso a orquestração compõe o harness direto, como o consolidado,
sem reinjetar paths. NÃO resolvemos esses caminhos no import de propósito:
get_agent_workspace CRIA o diretório sem o marker `.ai4se_workspace`, e isso faria
`init_workspace()` recusar limpar o workspace. Resolvê-los em tempo de chamada
(após init_workspace) evita esse efeito colateral.

Vive no LoopAgent [coder → executor]; o validador é sub-agente do executor. O
cr_reviewer permanece fora do loop.
"""

from src.agents.dockerfile_resolver.agent import criar_agente as criar_dockerfile_resolver
from src.agents.executor import prompt as executor_prompt
from src.agents.executor.error_report import montar_error_report
from src.agents.executor.orchestrator import ExecutorOrchestrator
from src.agents.implementation_validator.agent import criar_agente as criar_validator
from src.agents.test_command_resolver.agent import criar_agente as criar_test_command_resolver

# `name` preservado literalmente: é o identificador já em uso no workflow.
agent = ExecutorOrchestrator(
    name="cr_executor_agent",
    description=executor_prompt.description,
    validator=criar_validator(),
    dockerfile_resolver=criar_dockerfile_resolver(),
    test_command_resolver=criar_test_command_resolver(),
    error_report_builder=montar_error_report,
)
