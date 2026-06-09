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


def test_review_analyzer_instruction_provider_inclui_arquivos_descobertos(tmp_path, monkeypatch):
    """O instruction provider do _review_analyzer chama _discover_coder_files e injeta no template."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    # Cria arquivos APÓS o reload (init_workspace pode resetar o diretório)
    coder_ws = Path(wcr._CODER_WS)
    coder_ws.mkdir(parents=True, exist_ok=True)
    (coder_ws / "app").mkdir(exist_ok=True)
    (coder_ws / "app" / "main.py").write_text("# main")

    instr = wcr._review_analyzer.instruction
    if callable(instr):
        class _FakeCtx:
            pass
        rendered = instr(_FakeCtx())
        if hasattr(rendered, "__await__"):
            import asyncio
            rendered = asyncio.get_event_loop().run_until_complete(rendered)
    else:
        rendered = instr

    assert "- app/main.py" in rendered


def test_review_persister_instruction_referencia_analysis_e_anti_narracao(tmp_path, monkeypatch):
    """Persister.instruction referencia {review_analysis} e tem texto anti-narração."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    instr = wcr._review_persister.instruction
    # Persister.instruction é string estática com placeholder {review_analysis}
    assert isinstance(instr, str)
    assert "{review_analysis}" in instr
    # Anti-narração explícita
    assert "FAÇA a function call real" in instr or "FAÇA a function call" in instr
    assert "tool_salvar_relatorio" in instr


def test_review_analyzer_tool_ler_arquivo_esta_bound_ao_coder_ws(tmp_path, monkeypatch):
    """tool_ler_arquivo do analyzer resolve paths relativos contra _CODER_WS."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    coder_ws = Path(wcr._CODER_WS)
    coder_ws.mkdir(parents=True, exist_ok=True)
    target_file = coder_ws / "test_file.py"
    target_file.write_text("CONTEUDO_ESPERADO")

    tools = wcr._review_analyzer.tools
    ler_tool = next(t for t in tools if "ler_arquivo" in t.func.__name__)
    result = ler_tool.func(caminho="test_file.py")
    assert isinstance(result, str)
    assert "CONTEUDO_ESPERADO" in result
    assert not result.startswith("Erro:")


def test_reviewer_e_sequential_com_2_subagentes(tmp_path, monkeypatch):
    """_reviewer é SequentialAgent com 2 sub_agents: analyzer primeiro, persister depois."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from google.adk.agents import SequentialAgent
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    assert isinstance(wcr._reviewer, SequentialAgent)
    assert wcr._reviewer.name == "cr_review_agent"
    assert len(wcr._reviewer.sub_agents) == 2
    assert wcr._reviewer.sub_agents[0] is wcr._review_analyzer
    assert wcr._reviewer.sub_agents[1] is wcr._review_persister


def test_review_persister_so_tem_tool_salvar_relatorio(tmp_path, monkeypatch):
    """Persister tem exatamente 1 tool e ela é tool_salvar_relatorio."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import agent as wcr
    importlib.reload(wcr)

    tools = wcr._review_persister.tools
    assert len(tools) == 1
    tool_name = tools[0].func.__name__
    assert "salvar_relatorio" in tool_name
