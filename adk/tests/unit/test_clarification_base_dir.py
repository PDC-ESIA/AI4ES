"""Tests para tool_ask_clarification — suporte a base_dir + registro no factory.

Sem base_dir injetado, a tool gravava em CWD (que em produção é `adk/`),
criando arquivos como `adk/Doubt_Artifact_*.md` fora do workspace_output.
Este teste confirma que base_dir agora isola o artefato no diretório do agente.
"""

from pathlib import Path


def test_tool_ask_clarification_base_dir_isola_no_diretorio(tmp_path):
    """Com base_dir, arquivo vai para tmp_path/nome_arquivo (não CWD)."""
    from shared.tools.clarification import tool_ask_clarification

    result = tool_ask_clarification(
        titulo="Dúvida de teste",
        secao="Test section",
        descricao="Test descricao",
        impacto="Test impacto",
        base_dir=str(tmp_path),
    )

    assert result["sucesso"] is True
    expected = tmp_path / "Doubt_Artifact_Clarification.md"
    assert expected.is_file()
    assert "Dúvida de teste" in expected.read_text(encoding="utf-8")


def test_tool_ask_clarification_base_dir_none_mantem_legado(tmp_path, monkeypatch):
    """Sem base_dir (default None), comportamento legado: grava relativo ao CWD."""
    from shared.tools.clarification import tool_ask_clarification

    monkeypatch.chdir(tmp_path)
    result = tool_ask_clarification(
        titulo="Legacy",
        secao="Test",
        descricao="Test",
        impacto="Test",
        nome_arquivo="Doubt_Artifact_Legacy.md",
    )

    assert result["sucesso"] is True
    assert (tmp_path / "Doubt_Artifact_Legacy.md").is_file()


def test_tool_ask_clarification_no_filesystem_tool_names():
    """tool_ask_clarification deve estar em _FILESYSTEM_TOOL_NAMES para
    receber base_dir injetado automaticamente pelo agent_factory."""
    from shared.agent_factory import _FILESYSTEM_TOOL_NAMES

    assert "tool_ask_clarification" in _FILESYSTEM_TOOL_NAMES
