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


# ============================================================================
# tool_salvar_artefato_requisito — base_dir opcional
# ============================================================================

from shared.tools.filesystem import tool_salvar_artefato_requisito


def test_salvar_artefato_sem_base_dir_mantem_path_legado(tmp_path, monkeypatch):
    """Retro-compat: sem base_dir, escreve em docs/Time_1_Requisitos/HUs/."""
    monkeypatch.chdir(tmp_path)
    result = tool_salvar_artefato_requisito("HU", "HU-001", "# HU-001\n")
    assert result.startswith("SUCESSO:")
    assert (tmp_path / "docs/Time_1_Requisitos/HUs/HU-001.md").is_file()


def test_salvar_artefato_com_base_dir_escreve_em_subpasta_HUs(tmp_path):
    """Com base_dir, HU vai em <base_dir>/HUs/<id>.md."""
    base = tmp_path / "ws_req"
    base.mkdir()
    result = tool_salvar_artefato_requisito(
        "HU", "HU-001", "# HU-001\n", base_dir=str(base)
    )
    assert result.startswith("SUCESSO:")
    assert (base / "HUs" / "HU-001.md").is_file()
    # NÃO escreveu em docs/Time_1_Requisitos
    assert not (tmp_path / "docs").exists()


def test_salvar_artefato_com_base_dir_para_RF_RNF_RN(tmp_path):
    """Cada tipo vai em sua subpasta dentro de base_dir."""
    base = tmp_path / "ws_req"
    base.mkdir()
    tool_salvar_artefato_requisito("RF", "RF-001", "x", base_dir=str(base))
    tool_salvar_artefato_requisito("RNF", "RNF-001", "x", base_dir=str(base))
    tool_salvar_artefato_requisito("RN", "RN-001", "x", base_dir=str(base))
    assert (base / "RFs" / "RF-001.md").is_file()
    assert (base / "RNFs" / "RNF-001.md").is_file()
    assert (base / "RNs" / "RN-001.md").is_file()


def test_salvar_glossario_com_base_dir_escreve_na_raiz(tmp_path):
    """GLOSSARIO vai direto em <base_dir>/Glossario.md, sem subdir."""
    base = tmp_path / "ws_glos"
    base.mkdir()
    result = tool_salvar_artefato_requisito(
        "GLOSSARIO", "IGNORADO", "# Glossário\n", base_dir=str(base)
    )
    assert result.startswith("SUCESSO:")
    assert (base / "Glossario.md").is_file()


def test_salvar_artefato_tipo_desconhecido_com_base_dir(tmp_path):
    """Tipo fora do mapa cai em <base_dir>/Outros/."""
    base = tmp_path / "ws"
    base.mkdir()
    result = tool_salvar_artefato_requisito(
        "DESCONHECIDO", "XX-001", "x", base_dir=str(base)
    )
    assert result.startswith("SUCESSO:")
    assert (base / "Outros" / "XX-001.md").is_file()


def test_salvar_artefato_com_base_dir_rejeita_id_traversal(tmp_path):
    """id_req com '..' continua bloqueado pelo ID_REQ_PATTERN."""
    base = tmp_path / "ws"
    base.mkdir()
    result = tool_salvar_artefato_requisito(
        "HU", "../../escape", "x", base_dir=str(base)
    )
    assert result.startswith("ERRO ao salvar artefato:")
    # Nada escapou
    assert not (tmp_path.parent / "escape.md").exists()
