"""TacoJourneyOrchestrator — Composição Research → Architect.

Orquestrador sequencial que primeiro mapeia os conceitos pedagógicos
(TacoResearchAgent) e depois projeta a jornada de exercícios
(TacoArchitectAgent). Pode ser usado como app única para o Cenário 3
do TACO, ou os sub-agentes podem ser chamados isoladamente.
"""

import os

from google.adk.agents import SequentialAgent

from src.agents.taco_research.agent import agent as research_agent
from src.agents.taco_architect.agent import agent as architect_agent

agent = SequentialAgent(
    name="taco_journey_orchestrator",
    description=(
        "Pipeline de geração de jornadas: mapeia conceitos pedagógicos "
        "(Research) e depois projeta exercícios encadeados (Architect)."
    ),
    sub_agents=[research_agent, architect_agent],
)

root_agent = agent
