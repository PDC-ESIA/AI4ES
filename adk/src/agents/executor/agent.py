"""Agente Executor consolidado.

Slim, no molde de `reviewer/agent.py`: construído via `create_se_agent`, compõe
o harness de validação, o Agente de Validação de Implementação (AgentTool) e o
`exit_loop`. NÃO tem `output_schema` — o executor orquestra ferramentas e
encerra o loop; não emite saída estruturada própria.

O encerramento do loop depende EXCLUSIVAMENTE do veredito do validador
(ValidationVerdict.status == 'aprovado'), nunca do status técnico de execução do
harness. A "alma" (fluxo + salvaguarda) vive em `prompt.py`.
"""

from google.adk.tools import FunctionTool, exit_loop
from google.adk.tools.agent_tool import AgentTool

from shared.agent_factory import create_se_agent
from shared.tools.harness_execucao import executar_harness_validacao
from src.agents.implementation_validator import root_agent as implementation_validator

from . import prompt

agent = create_se_agent(
    name="executor",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        FunctionTool(executar_harness_validacao),
        AgentTool(agent=implementation_validator),
        exit_loop,
    ],
)

# ADK CLI busca por `root_agent` ao carregar um app diretamente.
root_agent = agent
