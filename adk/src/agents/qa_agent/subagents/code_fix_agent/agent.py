import os
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from shared.tools.build_fix_prompt import build_fix_prompt_from_error, build_fix_prompt_from_pytest
from shared.tools.qa_test_files import read_qa_test, write_qa_test

from .prompt import CODE_FIX_AGENT_PROMPT

agent = LlmAgent(
    name="code_fix_agent",
    model=os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash"),
    instruction=CODE_FIX_AGENT_PROMPT,
    description=(
        "Recebe logs de falha do pytest, lê o test_*.py afetado e aplica "
        "fisicamente a correção antes da nova execução do QA."
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
    ]
)
