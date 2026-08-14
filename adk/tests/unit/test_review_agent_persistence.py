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
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer
    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    result = cr_reviewer._discover_coder_files()
    assert "workspace vazio" in result or "nenhum arquivo" in result


def test_discover_coder_files_lista_arquivos_relativos(tmp_path, monkeypatch):
    """Workspace com arquivos: retorna bullets com paths relativos."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer
    importlib.reload(review_tools)
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
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer
    importlib.reload(review_tools)
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
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer
    importlib.reload(review_tools)
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
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer
    importlib.reload(review_tools)
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
    """_analyzer.after_agent_callback inclui _persist_review.

    Desde o PoC de memória (mem0), o callback é uma lista — ADK roda cada
    item em ordem (google/adk/agents/base_agent.py::_handle_after_agent_callback)
    — e _persist_review continua sendo o primeiro, responsável pela
    persistência do relatório em disco.
    """
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer
    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    callbacks = cr_reviewer._analyzer.after_agent_callback
    assert isinstance(callbacks, list)
    assert callbacks[0] is cr_reviewer._persist_review


def test_agent_e_alias_do_analyzer(tmp_path, monkeypatch):
    """agent é alias direto de _analyzer — sem LlmAgent intermediário para o save."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer
    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    assert cr_reviewer.agent is cr_reviewer._analyzer


def test_persist_review_cria_arquivo_no_review_ws(tmp_path, monkeypatch):
    """_persist_review escreve verificacao_revisao.md no workspace do reviewer."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer
    importlib.reload(review_tools)
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
    """_persist_review não cria arquivo quando review_analysis está ausente ou só whitespace."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer
    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    review_ws = Path(cr_reviewer._REVIEW_WS)
    review_ws.mkdir(parents=True, exist_ok=True)

    relatorio = review_ws / "verificacao_revisao.md"

    for state in [
        {},           # key ausente
        {"review_analysis": None},   # None explícito
        {"review_analysis": "   \n"},  # só whitespace
    ]:
        class _FakeCtx:
            pass
        _FakeCtx.state = state
        cr_reviewer._persist_review(_FakeCtx())
        assert not relatorio.exists(), f"Não deveria criar arquivo para state={state}"


def test_analyzer_tem_before_agent_callback(tmp_path, monkeypatch):
    """_analyzer.before_agent_callback está configurado com _inject_static_findings."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer
    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    assert cr_reviewer._analyzer.before_agent_callback is cr_reviewer._inject_static_findings


def test_inject_static_findings_popula_state(tmp_path, monkeypatch):
    """_inject_static_findings injeta static_findings_block no state do callback."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    monkeypatch.setenv("REVIEWER_STATIC_ANALYSIS", "1")

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer
    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    coder_ws = tmp_path / "ws" / "coder" / "src"
    coder_ws.mkdir(parents=True, exist_ok=True)
    (coder_ws / "app.py").write_text("import os\n")

    class _FakeCtx:
        state = {}

    cr_reviewer._inject_static_findings(_FakeCtx())
    assert "static_findings_block" in _FakeCtx.state
    assert isinstance(_FakeCtx.state["static_findings_block"], str)


def test_inject_static_findings_desabilitado_nao_popula_state(tmp_path, monkeypatch):
    """Com REVIEWER_STATIC_ANALYSIS=0, o state não é modificado."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    monkeypatch.setenv("REVIEWER_STATIC_ANALYSIS", "0")

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer
    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    class _FakeCtx:
        state = {}

    cr_reviewer._inject_static_findings(_FakeCtx())
    assert "static_findings_block" not in _FakeCtx.state


def test_adk_runner_dispara_after_agent_callback(tmp_path, monkeypatch):
    """Verifica que o ADK Runner dispara after_agent_callback após _analyzer completar.

    Usa before_model_callback para bypassar a chamada real ao Gemini — o ADK
    trata a resposta fake como output do agente, salva em state via output_key,
    e então dispara after_agent_callback (_persist_review).
    """
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer
    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    review_ws = Path(cr_reviewer._REVIEW_WS)
    review_ws.mkdir(parents=True, exist_ok=True)

    from google.adk.models.llm_response import LlmResponse
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types as genai_types

    fake_analysis = "## Status: APROVADO\n\n## Issues\nNenhum.\n\n## Resumo\nCodigo ok."

    def _stub_llm(callback_context, llm_request):
        """Bypassa chamada real ao Gemini — retorna análise fake."""
        return LlmResponse(
            content=genai_types.Content(
                role="model",
                parts=[genai_types.Part(text=fake_analysis)],
            )
        )

    _original_cb = cr_reviewer._analyzer.before_model_callback
    cr_reviewer._analyzer.before_model_callback = _stub_llm
    try:
        session_svc = InMemorySessionService()
        runner = Runner(
            agent=cr_reviewer._analyzer,
            app_name="test_persist",
            session_service=session_svc,
            auto_create_session=True,
        )
        list(runner.run(
            user_id="test_user",
            session_id="test_session",
            new_message=genai_types.Content(
                role="user",
                parts=[genai_types.Part(text="revisar")],
            ),
        ))
    finally:
        cr_reviewer._analyzer.before_model_callback = _original_cb

    relatorio = review_ws / "verificacao_revisao.md"
    assert relatorio.exists(), (
        "after_agent_callback não foi disparado pelo ADK Runner — "
        "verificacao_revisao.md não foi criado"
    )
    assert "APROVADO" in relatorio.read_text(encoding="utf-8")
