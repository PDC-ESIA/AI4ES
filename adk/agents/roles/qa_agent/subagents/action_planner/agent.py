import os
import logging
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool

from .prompt import SYSTEM_PROMPT
from ...tools import (
    create_hitl_checkpoint,
    describe_tools,
    generate_compliance_report,
    list_available_tools,
    plan_validator,
    register_human_validation,
)

logger = logging.getLogger("action_planner")

agent = LlmAgent(
    name="action_planner",
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", "github_copilot/gpt-4")),
    description=(
        "Planeja tarefas complexas de QA, decompoe passos e decide o fluxo "
        "antes da geracao ou execucao de testes."
    ),
    instruction=SYSTEM_PROMPT,
    tools=[
        FunctionTool(list_available_tools),
        FunctionTool(describe_tools),
        FunctionTool(plan_validator),
        FunctionTool(create_hitl_checkpoint),
        FunctionTool(register_human_validation),
        FunctionTool(generate_compliance_report),
    ],
)

