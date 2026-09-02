import os
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from shared.tools.build_fix_prompt import build_fix_prompt_from_error, build_fix_prompt_from_pytest
from shared.tools.qa_test_files import (
    executar_teste_unitario_corrigido,
    read_qa_test,
    write_qa_test,
)

from .prompt import CODE_FIX_AGENT_PROMPT

agent = LlmAgent(
    name="code_fix_agent",
    model=os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash"),
    instruction=CODE_FIX_AGENT_PROMPT,
    description=(
        "Recebe falhas unitárias de Python, Node/TypeScript, Java ou Go, "
        "corrige somente o teste existente e o reexecuta pelo perfil detectado."
    ),
    tools=[
        FunctionTool(
            func=build_fix_prompt_from_error
        ),
        FunctionTool(
            func=build_fix_prompt_from_pytest
        ),
        FunctionTool(func=read_qa_test),
        FunctionTool(func=write_qa_test),
        FunctionTool(func=executar_teste_unitario_corrigido),
    ]
)
