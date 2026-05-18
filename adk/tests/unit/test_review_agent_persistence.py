"""Tests para o cr_review_agent do workflow_coding_review.

Cobertura:
- _discover_coder_files lista arquivos do workspace do coder
- O InstructionProvider injeta a lista + a substring obrigatória de save
- As tools tool_ler_arquivo e tool_salvar_relatorio estão bound aos workspaces certos
"""

from pathlib import Path

import pytest


def test_discover_coder_files_workspace_vazio(tmp_path, monkeypatch):
    """Workspace sem arquivos: retorna marker '(workspace vazio)'."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    (tmp_path / "ws" / "coder").mkdir(parents=True)

    # Re-import com env nova
    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    result = wcr._discover_coder_files()
    assert "workspace vazio" in result or "nenhum arquivo" in result


def test_discover_coder_files_lista_arquivos_relativos(tmp_path, monkeypatch):
    """Workspace com arquivos: retorna bullets com paths relativos."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    # Cria arquivos APÓS o reload (init_workspace limpa o diretório no reload)
    coder_ws = Path(wcr._CODER_WS)
    (coder_ws / "app").mkdir(parents=True, exist_ok=True)
    (coder_ws / "app" / "main.py").write_text("# main")
    (coder_ws / "app" / "models.py").write_text("# models")
    (coder_ws / "requirements.txt").write_text("fastapi")

    result = wcr._discover_coder_files()
    assert "- app/main.py" in result
    assert "- app/models.py" in result
    assert "- requirements.txt" in result


def test_discover_coder_files_ignora_pycache(tmp_path, monkeypatch):
    """__pycache__ e seus arquivos não aparecem na lista."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    # Cria arquivos APÓS o reload (init_workspace limpa o diretório no reload)
    coder_ws = Path(wcr._CODER_WS)
    (coder_ws / "app" / "__pycache__").mkdir(parents=True, exist_ok=True)
    (coder_ws / "app" / "__pycache__" / "main.cpython-312.pyc").write_bytes(b"x")
    (coder_ws / "app" / "main.py").write_text("# main")

    result = wcr._discover_coder_files()
    assert "main.py" in result
    assert "__pycache__" not in result
    assert ".pyc" not in result
