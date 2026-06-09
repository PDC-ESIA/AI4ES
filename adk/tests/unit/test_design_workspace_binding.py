"""Testes do binding ao workspace dos especialistas de Time 2 com filesystem tools.

Escopo: design_architect, mermaid_specialist, markdown_specialist, io_agent.
Validator é stateless (recebe content inline, sem filesystem tools) —
binding ao workspace não se aplica a ele.
"""
from functools import partial
from pathlib import Path

import pytest

# validator é stateless (recebe content inline, sem filesystem tools) —
# binding ao workspace não se aplica.
ESPECIALISTAS = [
    ("design_architect", "design"),
    ("mermaid_specialist", "design/diagrams"),
    ("markdown_specialist", "design/reports"),
    ("io_agent", "design/staging"),
]


@pytest.mark.parametrize("nome,subdir_esperado", ESPECIALISTAS)
def test_especialista_binda_tools_ao_subdir(nome, subdir_esperado, monkeypatch, tmp_path):
    """Tools de filesystem dos especialistas devem ter base_dir pré-bindado."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))

    import importlib
    modulo = importlib.import_module(f"src.agents.{nome}.agent")
    importlib.reload(modulo)

    agente = modulo.agent
    expected_path = (tmp_path / subdir_esperado).resolve()

    encontrou_binding = False
    for t in agente.tools:
        func = getattr(t, "func", None)
        if isinstance(func, partial):
            kw = getattr(func, "keywords", {}) or {}
            if "base_dir" in kw:
                assert Path(kw["base_dir"]).resolve() == expected_path
                encontrou_binding = True

    assert encontrou_binding, (
        f"{nome} não tem nenhuma tool com base_dir pré-bindado. "
        f"Esperava pelo menos uma para subdir {subdir_esperado!r}."
    )
