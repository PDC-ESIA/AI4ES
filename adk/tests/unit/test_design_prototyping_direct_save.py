"""C5 — prototyping_specialist grava direto, na mesma pasta de design dos demais."""

from shared.tools import design_filesystem as df


def _tool(agent, nome):
    """Devolve a função chamável da tool (FunctionTool ligada ou função crua)."""
    for t in agent.tools:
        if (getattr(t, "name", None) or getattr(t, "__name__", "")) == nome:
            return getattr(t, "func", t)
    raise AssertionError(f"tool {nome} ausente")


def test_prototyping_grava_em_design_prototypes(tmp_path, monkeypatch):
    from src.agents.prototyping_specialist.agent import agent

    root = tmp_path / "design"
    monkeypatch.setattr(df, "ADK_DIR", tmp_path)
    monkeypatch.setattr(df, "DESIGN_DIR", root)
    monkeypatch.setattr(df, "LOCKS_DIR", root / ".locks")
    monkeypatch.setattr("shared.agent_factory.get_workspace_root", lambda: tmp_path)

    caller = "prototyping_specialist"
    assert _tool(agent, "acquire_lock")(filepath="PROTOTYPE/login.html", caller=caller)["status"] == "ok"
    r = _tool(agent, "save_artifact")(filename="PROTOTYPE/login.html", content="<html></html>", caller=caller)
    assert r["status"] == "ok", r
    assert (root / "prototypes" / "login.html").exists()
    assert not (tmp_path / "prototyping_specialist").exists()
    assert _tool(agent, "release_lock")(filepath="PROTOTYPE/login.html", caller=caller)["status"] == "ok"
