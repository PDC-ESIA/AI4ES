import os
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from shared.tools.build_fix_prompt import build_fix_prompt_from_error, build_fix_prompt_from_pytest

from .prompt import CODE_FIX_AGENT_PROMPT

agent = LlmAgent(
    name="code_fix_agent",
    model=os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash"),
    instruction=CODE_FIX_AGENT_PROMPT,
    description=(
        "Recebe logs e relatórios de falha de testes (pytest) e gera prompts de correção "
        "focados na causa raiz, alimentando o ciclo de autocorrect do agente QA."
    ),
    tools=[
        FunctionTool(
            func=build_fix_prompt_from_error
        ),
        FunctionTool(
            func=build_fix_prompt_from_pytest
        ),
    ]
)
