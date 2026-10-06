"""validate_analysis_sections presa à pasta de design da sessão (review Copilot).

A tool não está na allowlist de binding da fábrica; o design faz o binding
localmente para que o LLM não veja `base_dir` nem consiga apontar outro
workspace.
"""

import inspect

import pytest

from shared.tools import design_filesystem as df

AGENTES = [
    ("src.agents.workflow_design_pipeline.agent", "pipeline_controller"),
    ("src.agents.design_architect.agent", "agent"),
    ("src.agents.io_agent.agent", "agent"),
]


def _tool(agent):
    return next(t for t in agent.tools
                if (getattr(t, "name", None) or getattr(t, "__name__", "")) == "validate_analysis_sections")


@pytest.mark.parametrize("modulo,attr", AGENTES)
def test_schema_nao_expoe_base_dir(modulo, attr):
    import importlib
    agent = getattr(importlib.import_module(modulo), attr)
    tool = _tool(agent)
    assert "base_dir" not in inspect.signature(tool.func).parameters


def test_chamada_usa_pasta_de_design_da_sessao(tmp_path, monkeypatch):
    from src.agents.workflow_design_pipeline.agent import pipeline_controller

    sessao = tmp_path / "sessao" / "design"
    outra = tmp_path / "outra" / "design"
    for raiz in (sessao, outra):
        (raiz / "analysis").mkdir(parents=True)
    # só a OUTRA sessão tem um arquivo de análise
    (outra / "analysis" / "analise_tecnica_HU-001.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(df, "ADK_DIR", tmp_path)
    monkeypatch.setattr(df, "DESIGN_DIR", sessao)
    monkeypatch.setattr("shared.agent_factory.get_agent_workspace", lambda name: sessao)

    r = _tool(pipeline_controller).func(
        filename="analise_tecnica_HU-001.md", caller="pipeline_controller")
    assert r.get("complete") is not True  # não enxerga a análise da outra sessão
