"""Tests para shared/workspace.py — workspace centralizado dos agentes."""

import os
from pathlib import Path

import pytest


def test_get_workspace_root_default(monkeypatch, tmp_path):
    """Sem env var, usa ./workspace_output relativo ao cwd."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("WORKSPACE_OUTPUT_DIR", raising=False)
    from shared.workspace import get_workspace_root
    root = get_workspace_root()
    assert root == (tmp_path / "workspace_output").resolve()


def test_get_workspace_root_absoluto(monkeypatch, tmp_path):
    """Caminho absoluto é usado diretamente."""
    target = tmp_path / "custom_ws"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(target))
    from shared.workspace import get_workspace_root
    root = get_workspace_root()
    assert root == target.resolve()


def test_get_workspace_root_til_expandido(monkeypatch, tmp_path):
    """~ é expandido para home (usamos um fake HOME via tmp_path)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", "~/meu_ws")
    from shared.workspace import get_workspace_root
    root = get_workspace_root()
    assert root == (tmp_path / "meu_ws").resolve()


def test_init_workspace_cria_somente_raiz(monkeypatch, tmp_path):
    """init_workspace cria apenas a raiz + marker; subpastas são lazy."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import init_workspace, AGENT_DIRS
    root = init_workspace()
    assert root.is_dir()
    # Nenhuma subpasta de agente deve existir logo após init
    for subdir in set(AGENT_DIRS.values()):
        assert not (root / subdir).is_dir(), (
            f"Subpasta '{subdir}' não deveria existir antes de get_agent_workspace()"
        )


def test_get_agent_workspace_cria_subpasta_sob_demanda(monkeypatch, tmp_path):
    """get_agent_workspace() cria a subpasta na primeira chamada (lazy)."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import init_workspace, get_agent_workspace, AGENT_DIRS
    root = init_workspace()
    # Antes: subpasta não existe
    agent = "context_engineer"
    subdir = AGENT_DIRS[agent]
    assert not (root / subdir).is_dir()
    # Depois: get_agent_workspace cria sob demanda
    path = get_agent_workspace(agent)
    assert path.is_dir()
    assert path == (root / subdir).resolve()


def test_init_workspace_limpa_existente(monkeypatch, tmp_path):
    """init_workspace remove o workspace antigo (idempotência por prompt)."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import init_workspace
    root = init_workspace()
    # Cria um arquivo de poluição
    (root / "lixo.txt").write_text("dados antigos")
    assert (root / "lixo.txt").is_file()
    # Reinit — deve apagar
    root = init_workspace()
    assert not (root / "lixo.txt").exists()


def test_get_agent_workspace_agente_conhecido(monkeypatch, tmp_path):
    """Retorna path correto para agente mapeado em AGENT_DIRS."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import get_agent_workspace, AGENT_DIRS
    path = get_agent_workspace("context_engineer")
    assert path == (tmp_path / "ws" / AGENT_DIRS["context_engineer"]).resolve()


def test_get_agent_workspace_agente_desconhecido(monkeypatch, tmp_path):
    """Levanta ValueError para agente não mapeado."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import get_agent_workspace
    with pytest.raises(ValueError, match="não possui subpasta mapeada"):
        get_agent_workspace("agente_inexistente_xyz")


def test_agent_dirs_cobre_agentes_principais():
    """Smoke test: AGENT_DIRS tem entradas pros agentes principais dos 4 Times."""
    from shared.workspace import AGENT_DIRS
    esperados = [
        "requirements_agent", "context_engineer",
        "design_architect", "qa_agent",
        "coder_agent", "review_agent",
        "orchestrator",
    ]
    for agente in esperados:
        assert agente in AGENT_DIRS, f"Agente {agente} ausente em AGENT_DIRS"


def test_init_workspace_cria_marker(monkeypatch, tmp_path):
    """init_workspace cria o marker .ai4se_workspace na raiz."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import init_workspace, _WORKSPACE_MARKER
    root = init_workspace()
    marker = root / _WORKSPACE_MARKER
    assert marker.is_file()
    assert "AI4SE" in marker.read_text(encoding="utf-8")


def test_init_workspace_recusa_rmtree_sem_marker(monkeypatch, tmp_path):
    """init_workspace levanta RuntimeError se diretório existe sem marker."""
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    (ws_dir / "arquivo_qualquer.txt").write_text("dados")
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws_dir))
    from shared.workspace import init_workspace
    with pytest.raises(RuntimeError, match="não contém o marker"):
        init_workspace()
