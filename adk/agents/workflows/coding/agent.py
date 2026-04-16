"""Workflow coding: pipeline SDLC sequencial."""

from google.adk.agents import SequentialAgent

from agents.roles.requirements.agent import agent as requirements_agent
from agents.roles.architect.agent import agent as architecture_agent
from agents.roles.test_planner.agent import agent as test_planning_agent
from agents.roles.coder.agent import agent as implementation_agent
from agents.roles.reviewer.agent import agent as review_agent
from agents.roles.qa_agent.agent import agent as qa_agent
from agents.roles.finalizer.agent import agent as finalization_agent

agent = SequentialAgent(
    name="sdlc_pipeline",
    description="Pipeline completo: requisitos → arquitetura → plano de testes → implementação → revisão → QA → finalização.",
    sub_agents=[
        requirements_agent,
        architecture_agent,
        test_planning_agent,
        implementation_agent,
        review_agent,
        qa_agent,
        finalization_agent,
    ],
)
