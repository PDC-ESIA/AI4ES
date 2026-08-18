import os
from google.adk.agents import LlmAgent
from google.adk.models.llm_response import LlmResponse
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool
from .subagents.action_planner.agent import agent as action_planner_agent
from .subagents.code_fix_agent.agent import agent as code_fix_agent
from .subagents.e2e_test_generator.agent import agent as e2e_test_generator_agent

from .subagents.receive_requirements import agent as receber_requisitos_agent
from shared.cache import create_qa_agent_response_cache
from shared.tools.pytest_runner import executar_pytest_tool
from shared.tools.doubt_tool import DoubtArtifactGenerator

from .callbacks import (
    bloquear_reexecucao_e2e,
    emitir_resultado_e2e_sem_reinterpretacao,
    registrar_resultado_e2e,
)
from .prompt import QA_PROMPT

_qa_cache = create_qa_agent_response_cache(prompt_text=QA_PROMPT)


async def _after_model_callback(callback_context, llm_response: LlmResponse) -> LlmResponse | None:
    """Chains cache storage and E2E result emission."""
    await _qa_cache.after_model_callback(callback_context, llm_response)
    return emitir_resultado_e2e_sem_reinterpretacao(callback_context, llm_response)


agent = LlmAgent(
    name="qa_agent",
    model=os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash"),
    description=(
        "Agente QA do Time 3 — PDC-AI4SE. "
        "Recebe artefatos de requisito (RF, HU, UC, RNF, RN), "
        "gera testes pytest e cobertura, ou planos E2E Playwright quando solicitado."
    ),
    instruction=QA_PROMPT,
    tools=[
        AgentTool(agent=action_planner_agent),
        AgentTool(agent=e2e_test_generator_agent),
        FunctionTool(executar_pytest_tool),
        FunctionTool(DoubtArtifactGenerator.generate),
        AgentTool(agent=receber_requisitos_agent),
        AgentTool(agent=code_fix_agent),
    ],
    before_model_callback=_qa_cache.before_model_callback,
    after_model_callback=_after_model_callback,
    on_model_error_callback=_qa_cache.on_model_error_callback,
    before_tool_callback=bloquear_reexecucao_e2e,
    after_tool_callback=registrar_resultado_e2e,
)

# ADK framework expects this export
root_agent = agent
