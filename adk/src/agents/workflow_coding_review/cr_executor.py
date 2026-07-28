"""Executor dedicado ao workflow coding_review — espelho do executor consolidado.

Instância-espelho de `src/agents/executor/` (mesma ideia de cr_reviewer → reviewer):
- REUSA a "alma" (fluxo + salvaguarda) de `executor/prompt.py`; a instrução NÃO
  é mais definida aqui — este espelho apenas a reusa.
- Compõe harness + AgentTool(validador) + exit_loop, derivado do consolidado.
- O loop encerra em DUAS condições: quando o veredito do validador é 'aprovado',
  OU quando o protocolo de estagnação detecta que o coder não fez alterações e o
  bloqueio se repete (encerramento por estagnação, com status `bloqueado` — NÃO é
  aprovação). O status técnico de execução do harness, sozinho, nunca encerra.

Binding ao workspace do workflow: o harness já resolve, em tempo de CHAMADA, os
seus base_dirs default — coder/src (get_agent_workspace("cr_coder"), entrada do
coder), coder/execution ("cr_executor", saída da execução) e coder/tasks
("cr_context_engineer", a Task). Esses são exatamente os diretórios deste
workflow; por isso compomos o harness direto, como o consolidado, sem reinjetar
paths. NÃO resolvemos esses caminhos no import de propósito: get_agent_workspace
CRIA o diretório sem o marker `.ai4se_workspace`, e isso faria `init_workspace()`
recusar limpar o workspace. Resolvê-los em tempo de chamada (após init_workspace)
evita esse efeito colateral.

Vive no LoopAgent [coder → executor]; o validador é AgentTool interna do
executor. O cr_reviewer permanece fora do loop.
"""

import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, exit_loop
from google.adk.tools.agent_tool import AgentTool
from google.genai import types

from shared.tools.harness_execucao import executar_harness_validacao
from src.agents.executor import prompt as executor_prompt
from src.agents.implementation_validator import root_agent as implementation_validator

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)


# A instrução (fluxo + salvaguarda) é reusada VERBATIM do consolidado: não há
# diferenças de workspace/contexto a ajustar — os nomes de tool e o fluxo já
# valem para o workflow. (Se surgirem diferenças, adaptar aqui via .replace,
# como o cr_reviewer faz com reviewer_prompt.)
agent = LlmAgent(
    model=_model,
    name="cr_executor_agent",
    description=executor_prompt.description,
    instruction=executor_prompt.instruction,
    output_key="execution_result",
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=8192,
    ),
    tools=[
        FunctionTool(executar_harness_validacao),
        AgentTool(agent=implementation_validator),
        FunctionTool(exit_loop),
    ],
)
