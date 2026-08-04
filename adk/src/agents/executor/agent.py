"""Agente Executor consolidado.

Não é mais um `LlmAgent`: a orquestração (rodar o harness → acionar o validador
→ decidir a continuidade do loop) é determinística, feita pelo
`ExecutorOrchestrator`. Sem LLM no topo, o veredito não tem como ser
reinterpretado — a "salvaguarda" que o `prompt.py` precisava escrever em prosa
virou o próprio fluxo de controle.

O encerramento do loop continua dependendo EXCLUSIVAMENTE do veredito do
validador (ValidationVerdict.status == 'aprovado'), nunca do status técnico de
execução do harness.

O validador é injetado por `criar_agente()` (instância própria, não o singleton
de módulo): como sub-agente ele ganha `parent_agent`, e o ADK exige parent único.
"""

from src.agents.implementation_validator.agent import criar_agente

from . import prompt
from .error_report import montar_error_report
from .orchestrator import ExecutorOrchestrator

agent = ExecutorOrchestrator(
    name="executor",
    description=prompt.description,
    validator=criar_agente(),
    error_report_builder=montar_error_report,
)

# ADK CLI busca por `root_agent` ao carregar um app diretamente.
root_agent = agent
