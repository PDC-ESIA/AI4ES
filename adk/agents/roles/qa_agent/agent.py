import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool
from .subagents.action_planner.agent import agent as action_planner_agent
from .subagents.code_fix_agent.agent import agent as code_fix_agent
from .subagents.qa_runner_agent import agent as qa_runner_agent

from .subagents.receive_requirements import agent as receber_requisitos_agent
from .tools.pytest_runner import executar_pytest_tool

from .qa_prompt import QA_PROMPT

agent = LlmAgent(
    name="qa_agent",
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", "github_copilot/gpt-4")),
    description=(
        "Agente QA do Time 3 — PDC-AI4SE. "
        "Recebe artefatos de requisito (RF, HU, UC, RNF, RN), "
        "gera testes pytest automaticamente em paralelo e reporta cobertura."
    ),
    instruction=QA_PROMPT,
    tools=[
        AgentTool(agent=receber_requisitos_agent),
        FunctionTool(executar_pytest_tool),
        AgentTool(agent=action_planner_agent),
        AgentTool(agent=code_fix_agent),
        AgentTool(agent=qa_runner_agent),
    ],
)

# ADK framework expects this export
root_agent = agent