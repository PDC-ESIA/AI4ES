"""Orchestrator SDLC: aciona os 5 workflows e coordena doubt inbox.

v1 (MVP): protocolo de fases instruido via prompt. Doubts sempre escalam
ao usuario (sem auto-routing — fica para v2).
"""

import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool

from src.agents.workflow_requirements.agent import agent as requirements_pipeline
from src.agents.workflow_design_pipeline.agent import agent as design_pipeline
from src.agents.workflow_coding_review.agent import agent as coding_review_pipeline
from src.agents.workflow_coding.agent import agent as sdlc_pipeline
from src.agents.workflow_qa.agent import agent as qa_pipeline

from shared.tools import (
    tool_criar_arquivo,
    tool_ler_arquivo,
    coletar_doubts_pendentes,
    responder_doubt,
)

from . import prompt

_DEFAULT_MODEL = "github_copilot/gpt-4"

root_agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
    name="orchestrator",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        AgentTool(agent=requirements_pipeline),
        AgentTool(agent=design_pipeline),
        AgentTool(agent=coding_review_pipeline),
        AgentTool(agent=sdlc_pipeline),
        AgentTool(agent=qa_pipeline),
        FunctionTool(tool_criar_arquivo),
        FunctionTool(tool_ler_arquivo),
        FunctionTool(coletar_doubts_pendentes),
        FunctionTool(responder_doubt),
    ],
)
