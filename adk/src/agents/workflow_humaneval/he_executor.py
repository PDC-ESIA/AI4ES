"""Executor dedicado ao workflow HumanEval.

Versão simplificada do cr_executor:
- Usa mode="function_only" no harness (pula healthcheck HTTP)
- Sem implementation_validator (pytest É o veredito)
- exit_loop quando pytest passa; reporta erro quando falha
- Wrapper do harness aponta para os diretórios humaneval/* (não coder/*)
"""

import logging
import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, exit_loop, ToolContext
from google.genai import types

from shared.tools.harness_execucao import executar_harness_validacao
from shared.workspace import get_agent_workspace

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)


def _he_harness_tool(
    task_id: str,
    iteration: int = 1,
    mode: str = "local",
    tool_context: ToolContext | None = None,
) -> dict:
    """Wrapper do harness que resolve os diretórios do workflow humaneval.

    Sem este wrapper, executar_harness_tool resolve para os diretórios do
    workflow coding_review (coder/src, coder/tasks, coder/execution) — que
    não são os diretórios deste workflow.

    Usa mode='local' por padrão: roda pytest diretamente no host (sem Docker).
    """
    return executar_harness_validacao(
        task_id,
        iteration,
        mode=mode,
        coder_base_dir=get_agent_workspace("he_coder"),
        execution_base_dir=get_agent_workspace("he_executor"),
        tasks_base_dir=get_agent_workspace("he_tasks"),
        tool_context=tool_context,
    )


_INSTRUCTION = """
# PERFIL
Você é o Executor do benchmark HumanEval. Sua função é validar a implementação
do coder executando os testes unitários localmente (pytest no host, sem Docker).

# FLUXO OBRIGATÓRIO (siga EXATAMENTE nesta ordem)

## PASSO 1 — Executar o harness
Chame `_he_harness_tool` com:
- `task_id`: o identificador da task (recebido no contexto)
- `iteration`: número da iteração atual
- `mode`: "local"

## PASSO 2 — Analisar resultado
Analise o resultado do harness, focando no estágio de testes automatizados
(estágio 6 — `testes_automatizados`).

## PASSO 3 — Decidir
- Se os testes PASSARAM (estágio 6 status "sucesso"):
  Chame `exit_loop` para encerrar o loop. O benchmark passou.
- Se os testes FALHARAM:
  Produza um relatório de erro com os detalhes da falha (logs, traceback)
  para que o coder possa corrigir. NÃO chame exit_loop.

# REGRAS
- SEMPRE execute o harness ANTES de tomar qualquer decisão.
- NUNCA invente resultados — use APENAS o que o harness retornou.
- O campo `mode` DEVE ser "local" (pytest no host, sem Docker/healthcheck).
"""

agent = LlmAgent(
    model=_model,
    name="he_executor_agent",
    description="Valida implementação HumanEval via pytest local (mode=local, sem Docker).",
    instruction=_INSTRUCTION,
    output_key="execution_result",
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=4096,
    ),
    tools=[
        FunctionTool(_he_harness_tool),
        FunctionTool(exit_loop),
    ],
)
