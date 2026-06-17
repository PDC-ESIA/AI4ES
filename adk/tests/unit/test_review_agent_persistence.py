"""Testes para o cr_reviewer do workflow_coding_review.

Cobertura:
- _discover_coder_files lista arquivos do workspace do coder
- O InstructionProvider injeta a lista de arquivos no momento da invocação
- tool_ler_arquivo está bound ao workspace do coder
- _analyzer tem after_agent_callback configurado (_persist_review)
- agent é alias direto de _analyzer (sem LlmAgent intermediário para o save)
- O callback _persist_review escreve verificacao_revisao.md no workspace do reviewer
"""

from pathlib import Path

import pytest


def test_discover_coder_files_workspace_vazio(tmp_path, monkeypatch):
    """Workspace sem arquivos: retorna marker '(workspace vazio)'."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    (tmp_path / "ws" / "coder").mkdir(parents=True)

    import importlib
    from src.agents.workflow_coding_review import cr_reviewer
    importlib.reload(cr_reviewer)

    result = cr_reviewer._discover_coder_files()
    assert "workspace vazio" in result or "nenhum arquivo" in result


def test_discover_coder_files_lista_arquivos_relativos(tmp_path, monkeypatch):
    """Workspace com arquivos: retorna bullets com paths relativos."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import cr_reviewer
    importlib.reload(cr_reviewer)

    coder_ws = Path(cr_reviewer._CODER_WS)
    (coder_ws / "app").mkdir(parents=True, exist_ok=True)
    (coder_ws / "app" / "main.py").write_text("# main")
    (coder_ws / "app" / "models.py").write_text("# models")
    (coder_ws / "requirements.txt").write_text("fastapi")

    result = cr_reviewer._discover_coder_files()
    assert "- app/main.py" in result
    assert "- app/models.py" in result
    assert "- requirements.txt" in result


def test_discover_coder_files_ignora_pycache(tmp_path, monkeypatch):
    """__pycache__ e seus arquivos não aparecem na lista."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import cr_reviewer
    importlib.reload(cr_reviewer)

    coder_ws = Path(cr_reviewer._CODER_WS)
    (coder_ws / "app" / "__pycache__").mkdir(parents=True, exist_ok=True)
    (coder_ws / "app" / "__pycache__" / "main.cpython-312.pyc").write_bytes(b"x")
    (coder_ws / "app" / "main.py").write_text("# main")

    result = cr_reviewer._discover_coder_files()
    assert "main.py" in result
    assert "__pycache__" not in result
    assert ".pyc" not in result


def test_review_analyzer_instruction_provider_inclui_arquivos_descobertos(tmp_path, monkeypatch):
    """O instruction provider do _analyzer chama _discover_coder_files e injeta no template."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import cr_reviewer
    importlib.reload(cr_reviewer)

    coder_ws = Path(cr_reviewer._CODER_WS)
    coder_ws.mkdir(parents=True, exist_ok=True)
    (coder_ws / "app").mkdir(exist_ok=True)
    (coder_ws / "app" / "main.py").write_text("# main")

    instr = cr_reviewer._analyzer.instruction
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


def test_review_analyzer_tool_ler_arquivo_esta_bound_ao_coder_ws(tmp_path, monkeypatch):
    """tool_ler_arquivo do analyzer resolve paths relativos contra _CODER_WS."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import cr_reviewer
    importlib.reload(cr_reviewer)

    coder_ws = Path(cr_reviewer._CODER_WS)
    coder_ws.mkdir(parents=True, exist_ok=True)
    target_file = coder_ws / "test_file.py"
    target_file.write_text("CONTEUDO_ESPERADO")

    tools = cr_reviewer._analyzer.tools
    ler_tool = next(t for t in tools if "ler_arquivo" in t.func.__name__)
    result = ler_tool.func(caminho="test_file.py")
    assert isinstance(result, str)
    assert "CONTEUDO_ESPERADO" in result
    assert not result.startswith("Erro:")


def test_analyzer_tem_after_agent_callback(tmp_path, monkeypatch):
    """_analyzer.after_agent_callback está configurado com _persist_review."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import cr_reviewer
    importlib.reload(cr_reviewer)

    assert cr_reviewer._analyzer.after_agent_callback is cr_reviewer._persist_review


def test_agent_e_alias_do_analyzer(tmp_path, monkeypatch):
    """agent é alias direto de _analyzer — sem LlmAgent intermediário para o save."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import cr_reviewer
    importlib.reload(cr_reviewer)

    assert cr_reviewer.agent is cr_reviewer._analyzer


def test_persist_review_cria_arquivo_no_review_ws(tmp_path, monkeypatch):
    """_persist_review escreve verificacao_revisao.md no workspace do reviewer."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import cr_reviewer
    importlib.reload(cr_reviewer)

    review_ws = Path(cr_reviewer._REVIEW_WS)
    review_ws.mkdir(parents=True, exist_ok=True)

    class _FakeCallbackContext:
        state = {"review_analysis": "## Status: APROVADO\n\n## Resumo\nTudo ok."}

    cr_reviewer._persist_review(_FakeCallbackContext())

    relatorio = review_ws / "verificacao_revisao.md"
    assert relatorio.exists(), "Relatório não foi criado no workspace do reviewer"
    content = relatorio.read_text(encoding="utf-8")
    assert "APROVADO" in content


def test_persist_review_nao_cria_arquivo_se_analysis_vazia(tmp_path, monkeypatch):
    """_persist_review não cria arquivo quando review_analysis está ausente ou vazio."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from src.agents.workflow_coding_review import cr_reviewer
    importlib.reload(cr_reviewer)

    review_ws = Path(cr_reviewer._REVIEW_WS)
    review_ws.mkdir(parents=True, exist_ok=True)

    class _FakeCallbackContext:
        state = {}  # sem review_analysis

    cr_reviewer._persist_review(_FakeCallbackContext())

    relatorio = review_ws / "verificacao_revisao.md"
    assert not relatorio.exists(), "Não deveria criar arquivo com analysis vazia"
