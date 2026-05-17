"""Tests para shared/agent_factory.py — workspace binding opcional."""

import os
from pathlib import Path

import pytest
from google.adk.tools import FunctionTool

from shared.agent_factory import (
    create_se_agent,
    _bind_tool_to_workspace,
    _FILESYSTEM_TOOL_NAMES,
    _GIT_TOOL_NAMES,
    _WORKSPACE_READ_TOOL_NAMES,
)


def test_create_se_agent_sem_workspace_retro_compat():
    """Sem agent_subdir, comportamento idêntico ao anterior."""
    agent = create_se_agent(
        name="test_agent",
        description="d",
        instruction="i",
        tools=[],
    )
    assert agent.name == "test_agent"
    # tool_ask_clarification_adk sempre presente
    assert len(agent.tools) == 1


def test_create_se_agent_com_workspace_subdir_conhecido(monkeypatch, tmp_path):
    """Com agent_subdir='context_engineer' (em AGENT_DIRS), tools são bound."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.tools import tool_criar_arquivo
    agent = create_se_agent(
        name="ce",
        description="d",
        instruction="i",
        tools=[FunctionTool(tool_criar_arquivo)],
        agent_subdir="context_engineer",
    )
    # 1 tool_ask_clarification + 1 tool_criar_arquivo = 2
    assert len(agent.tools) == 2


def test_create_se_agent_com_subdir_arbitrario(monkeypatch, tmp_path):
    """agent_subdir como path direto também funciona."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    agent = create_se_agent(
        name="custom",
        description="d",
        instruction="i",
        tools=[],
        agent_subdir="meu_dir_custom",
    )
    assert agent.name == "custom"


def test_bind_tool_filesystem_injeta_base_dir(monkeypatch, tmp_path):
    """_bind_tool_to_workspace injeta base_dir em filesystem tools."""
    from shared.tools.filesystem import tool_criar_arquivo
    agent_ws = tmp_path / "ws" / "coder"
    agent_ws.mkdir(parents=True)
    bound = _bind_tool_to_workspace(
        FunctionTool(tool_criar_arquivo),
        agent_workspace=str(agent_ws),
        workspace_root=str(tmp_path / "ws"),
    )
    # Chamar a função bound — deve escrever em agent_ws, não no cwd
    underlying = bound.func if hasattr(bound, "func") else bound
    # Como o partial bind é interno, chamamos a função do FunctionTool
    # diretamente para verificar:
    result = underlying(caminho="out.txt", conteudo="x")
    assert result["sucesso"] is True
    assert (agent_ws / "out.txt").is_file()


def test_bind_tool_workspace_read_injeta_workspace_root(tmp_path):
    """workspace read tools recebem workspace_root, não agent_workspace."""
    from shared.tools.filesystem import tool_ler_workspace
    ws = tmp_path / "ws"
    (ws / "coder").mkdir(parents=True)
    (ws / "coder" / "main.py").write_text("x")
    bound = _bind_tool_to_workspace(
        FunctionTool(tool_ler_workspace),
        agent_workspace=str(ws / "review"),  # outro subdir
        workspace_root=str(ws),
    )
    underlying = bound.func if hasattr(bound, "func") else bound
    # workspace read consegue acessar OUTRO subdir do workspace
    result = underlying(caminho="coder/main.py")
    assert result == "x"


def test_bind_tool_git_injeta_cwd(monkeypatch, tmp_path):
    """Git tools recebem cwd=agent_workspace."""
    from shared.tools.git import tool_git_add
    agent_ws = tmp_path / "ws" / "coder"
    agent_ws.mkdir(parents=True)
    bound = _bind_tool_to_workspace(
        FunctionTool(tool_git_add),
        agent_workspace=str(agent_ws),
        workspace_root=str(tmp_path / "ws"),
    )
    underlying = bound.func if hasattr(bound, "func") else bound
    # Vamos capturar a chamada de subprocess.run
    captured = []
    def fake_run(cmd, **kwargs):
        captured.append(kwargs.get("cwd"))
        class R:
            stdout = ""
            stderr = ""
            returncode = 0
        return R()
    monkeypatch.setattr("shared.tools.git.run", fake_run)
    underlying(arquivos="file.py")
    assert captured[0] == str(agent_ws)


def test_bind_tool_desconhecida_retorna_intacta():
    """Tool não mapeada nas 3 categorias é retornada sem binding."""
    def tool_aleatoria(x: str) -> str:
        return x
    result = _bind_tool_to_workspace(
        tool_aleatoria,
        agent_workspace="/foo",
        workspace_root="/bar",
    )
    # Como não está em nenhum set, retorna intacta
    assert result is tool_aleatoria


def test_constantes_categorias_corretas():
    """Smoke test: as 3 categorias têm as funções esperadas."""
    assert "tool_criar_arquivo" in _FILESYSTEM_TOOL_NAMES
    assert "tool_ler_workspace" in _WORKSPACE_READ_TOOL_NAMES
    assert "tool_git_commit" in _GIT_TOOL_NAMES
    assert "tool_preparar_commit" in _GIT_TOOL_NAMES


def test_filesystem_tool_names_inclui_artefato_requisito_e_doubt():
    """Garante que as duas tools de Time 1 são reconhecidas pelo factory binding."""
    from shared.agent_factory import _FILESYSTEM_TOOL_NAMES
    assert "tool_salvar_artefato_requisito" in _FILESYSTEM_TOOL_NAMES
    assert "gerar_doubt_artifact" in _FILESYSTEM_TOOL_NAMES


def test_bind_tool_salvar_artefato_requisito_injeta_base_dir(tmp_path):
    """_bind_tool_to_workspace deve aplicar partial(base_dir=...) em tool_salvar_artefato_requisito."""
    from google.adk.tools import FunctionTool
    from shared.agent_factory import _bind_tool_to_workspace
    from shared.tools import tool_salvar_artefato_requisito

    base = tmp_path / "agente"
    base.mkdir()
    bound = _bind_tool_to_workspace(
        FunctionTool(tool_salvar_artefato_requisito),
        agent_workspace=str(base),
        workspace_root=str(tmp_path),
    )
    # Chama via func subjacente
    result = bound.func("HU", "HU-007", "# bound\n")
    assert result.startswith("SUCESSO:")
    assert (base / "HUs" / "HU-007.md").is_file()


def test_bind_gerar_doubt_artifact_injeta_base_dir(tmp_path):
    """_bind_tool_to_workspace deve aplicar partial(base_dir=...) em gerar_doubt_artifact."""
    from google.adk.tools import FunctionTool
    from shared.agent_factory import _bind_tool_to_workspace
    from shared.tools import gerar_doubt_artifact

    base = tmp_path / "agente"
    base.mkdir()
    bound = _bind_tool_to_workspace(
        FunctionTool(gerar_doubt_artifact),
        agent_workspace=str(base),
        workspace_root=str(tmp_path),
    )
    caminho = bound.func(
        id_duvida="D-001",
        id_artefato_afetado="HU-001",
        trecho_contexto="x",
        duvida_descricao="x",
        motivo="x",
        impacto="x",
    )
    p = Path(caminho)
    assert p.is_file()
    assert p.parent == base
