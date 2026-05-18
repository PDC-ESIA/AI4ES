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


def test_reviewer_instruction_provider_inclui_arquivos_descobertos(tmp_path, monkeypatch):
    """O instruction provider do _reviewer chama _discover_coder_files e injeta no template."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    # Cria arquivos APÓS o reload (init_workspace pode resetar o diretório)
    coder_ws = Path(wcr._CODER_WS)
    coder_ws.mkdir(parents=True, exist_ok=True)
    (coder_ws / "app").mkdir(exist_ok=True)
    (coder_ws / "app" / "main.py").write_text("# main")

    # _reviewer.instruction deve ser callable (InstructionProvider) ou string já contendo o glob
    instr = wcr._reviewer.instruction
    if callable(instr):
        # Stub mínimo de ReadonlyContext — o provider só precisa do callable
        class _FakeCtx:
            pass
        rendered = instr(_FakeCtx())
        # Provider pode retornar str ou Awaitable[str]
        if hasattr(rendered, "__await__"):
            import asyncio
            rendered = asyncio.get_event_loop().run_until_complete(rendered)
    else:
        rendered = instr

    assert "- app/main.py" in rendered


def test_reviewer_instruction_contem_save_obrigatorio(tmp_path, monkeypatch):
    """Instruction final do reviewer DEVE conter a frase que torna o save mandatório."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    instr = wcr._reviewer.instruction
    if callable(instr):
        class _FakeCtx:
            pass
        rendered = instr(_FakeCtx())
        if hasattr(rendered, "__await__"):
            import asyncio
            rendered = asyncio.get_event_loop().run_until_complete(rendered)
    else:
        rendered = instr

    assert "tool_salvar_relatorio" in rendered
    assert "OBRIGATÓRIO" in rendered


def test_reviewer_tool_ler_arquivo_esta_bound_ao_coder_ws(tmp_path, monkeypatch):
    """tool_ler_arquivo do reviewer resolve paths relativos contra _CODER_WS."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    # Cria arquivos APÓS o reload
    coder_ws = Path(wcr._CODER_WS)
    coder_ws.mkdir(parents=True, exist_ok=True)
    target_file = coder_ws / "test_file.py"
    target_file.write_text("CONTEUDO_ESPERADO")

    # tool_ler_arquivo deve ser o primeiro tool do _reviewer
    tools = wcr._reviewer.tools
    ler_tool = next(t for t in tools if "ler_arquivo" in t.func.__name__)
    # tool_ler_arquivo retorna str (não dict) — bound ao _CODER_WS via functools.partial
    result = ler_tool.func(caminho="test_file.py")
    assert isinstance(result, str)
    assert "CONTEUDO_ESPERADO" in result
    assert not result.startswith("Erro:")
