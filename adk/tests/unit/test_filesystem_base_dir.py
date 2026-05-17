"""Tests para base_dir opcional em filesystem tools + tool_ler/listar_workspace."""

import pytest
from pathlib import Path

from shared.tools.filesystem import (
    tool_criar_arquivo,
    tool_ler_arquivo,
    tool_substituir_trecho,
    tool_salvar_relatorio,
    tool_ler_workspace,
    tool_listar_workspace,
    _resolver_caminho,
)


def test_criar_arquivo_sem_base_dir_funciona(tmp_path, monkeypatch):
    """Retro-compat: sem base_dir, comportamento atual."""
    monkeypatch.chdir(tmp_path)
    result = tool_criar_arquivo("test.txt", "conteudo")
    assert result["sucesso"] is True
    assert (tmp_path / "test.txt").read_text() == "conteudo"


def test_criar_arquivo_com_base_dir_resolve_corretamente(tmp_path):
    """Com base_dir, caminho é resolvido relativo a ele."""
    base = tmp_path / "agente_x"
    base.mkdir()
    result = tool_criar_arquivo("output.txt", "x", base_dir=str(base))
    assert result["sucesso"] is True
    assert (base / "output.txt").is_file()
    # NÃO existe na raiz do projeto
    assert not (tmp_path / "output.txt").exists()


def test_criar_arquivo_base_dir_rejeita_absoluto(tmp_path):
    """Anti-traversal: caminho absoluto rejeitado com base_dir."""
    base = tmp_path / "agente_x"
    base.mkdir()
    result = tool_criar_arquivo("/etc/passwd.md", "x", base_dir=str(base))
    assert result["sucesso"] is False
    assert "absoluto" in result["erro"].lower()


def test_criar_arquivo_base_dir_rejeita_dotdot(tmp_path):
    """Anti-traversal: '..' rejeitado com base_dir."""
    base = tmp_path / "agente_x"
    base.mkdir()
    result = tool_criar_arquivo("../escape.txt", "x", base_dir=str(base))
    assert result["sucesso"] is False
    assert "traversal" in result["erro"].lower()


def test_ler_arquivo_com_base_dir(tmp_path):
    """tool_ler_arquivo respeita base_dir."""
    base = tmp_path / "agente_y"
    base.mkdir()
    (base / "x.txt").write_text("hello")
    conteudo = tool_ler_arquivo("x.txt", base_dir=str(base))
    assert conteudo == "hello"


def test_ler_workspace_requer_base_dir():
    """tool_ler_workspace sem base_dir retorna erro."""
    result = tool_ler_workspace("foo.txt")
    assert "requer base_dir" in result.lower()


def test_ler_workspace_le_de_subpasta(tmp_path):
    """tool_ler_workspace lê de qualquer subpasta do workspace."""
    ws = tmp_path / "workspace"
    (ws / "coder").mkdir(parents=True)
    (ws / "coder" / "main.py").write_text("print('ok')")
    conteudo = tool_ler_workspace("coder/main.py", base_dir=str(ws))
    assert conteudo == "print('ok')"


def test_ler_workspace_rejeita_traversal(tmp_path):
    """tool_ler_workspace rejeita .."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    result = tool_ler_workspace("../secret", base_dir=str(ws))
    assert "Erro" in result and "traversal" in result.lower()


def test_listar_workspace_requer_base_dir():
    result = tool_listar_workspace()
    assert isinstance(result, str) and "requer base_dir" in result.lower()


def test_listar_workspace_lista_subpastas(tmp_path):
    ws = tmp_path / "workspace"
    (ws / "coder").mkdir(parents=True)
    (ws / "review").mkdir()
    (ws / "tasks").mkdir()
    result = tool_listar_workspace(".", base_dir=str(ws))
    assert isinstance(result, list)
    assert set(result) == {"coder", "review", "tasks"}


def test_listar_workspace_subdir(tmp_path):
    ws = tmp_path / "workspace"
    coder = ws / "coder"
    coder.mkdir(parents=True)
    (coder / "main.py").touch()
    (coder / "utils.py").touch()
    result = tool_listar_workspace("coder", base_dir=str(ws))
    assert isinstance(result, list)
    assert set(result) == {"main.py", "utils.py"}


def test_resolver_caminho_sem_base_dir():
    """_resolver_caminho sem base_dir retorna Path(caminho) direto."""
    p = _resolver_caminho("foo/bar.txt")
    assert p == Path("foo/bar.txt")


def test_resolver_caminho_com_base_dir(tmp_path):
    base = tmp_path / "ws"
    base.mkdir()
    p = _resolver_caminho("file.txt", str(base))
    assert p == (base / "file.txt").resolve() or p == base / "file.txt"
