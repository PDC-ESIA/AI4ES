"""Agentes de design sem a clarificação genérica da fábrica.

create_se_agent (shared/agent_factory.py, não alterado) injeta
tool_ask_clarification e anexa a política "diante de ambiguidade, pare e
pergunte". Isso conflita com o protocolo Aviso/Doubt do design e grava um
Doubt_Artifact com "EXECUÇÃO PAUSADA" que bloqueia o pipeline. Cada agent.py
do design chama remover_clarificacao_generica(agent) logo após a fábrica.
"""

import importlib

import pytest

from shared.agent_factory import _SE_AGENT_POLICY

AGENTES = ["design_architect", "mermaid_specialist", "markdown_specialist",
           "prototyping_specialist", "validator", "io_agent"]


@pytest.mark.parametrize("nome", AGENTES)
def test_agente_de_design_sem_clarificacao_generica(nome):
    agent = importlib.import_module(f"src.agents.{nome}.agent").agent
    nomes = [getattr(t, "name", None) or getattr(t, "__name__", "") for t in agent.tools]
    assert "tool_ask_clarification" not in nomes
    assert _SE_AGENT_POLICY not in agent.instruction
