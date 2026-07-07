"""Testes do binding do qa_pipeline ao workspace centralizado."""
from pathlib import Path

import pytest


def test_tests_dir_resolve_via_workspace(monkeypatch, tmp_path):
    """_tests_dir() deve apontar para <WORKSPACE_OUTPUT_DIR>/tests/inputs/"""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))

    # Re-import força reavaliação se o módulo cacheia o env (não cacheia,
    # mas é defensivo).
    from src.agents.qa_agent.subagents.receive_requirements import _tests_dir

    resultado = _tests_dir()
    assert resultado == (tmp_path / "tests" / "inputs").resolve()


def test_doubt_dir_resolve_sibling_de_tests(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))

    from src.agents.qa_agent.subagents.receive_requirements import _doubt_dir

    resultado = _doubt_dir()
    assert resultado == (tmp_path / "tests" / "inputs" / "doubt_artifacts").resolve()


def test_pytest_runner_resolve_dynamic_base(monkeypatch, tmp_path):
    """_normalizar_caminho_arquivo deve resolver paths relativos para o workspace."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))

    # cria estrutura esperada
    tests_inputs = tmp_path / "tests" / "inputs"
    tests_inputs.mkdir(parents=True)
    (tests_inputs / "hu_001").mkdir()
    arquivo = tests_inputs / "hu_001" / "test_hu_001.py"
    arquivo.write_text("def test_x(): assert True\n")

    from adk.shared.tools.pytest_runner import _normalizar_caminho_arquivo

    resultado = _normalizar_caminho_arquivo("hu_001/test_hu_001.py")
    assert resultado == arquivo.resolve()


def test_doubt_tool_resolve_via_workspace(monkeypatch, tmp_path):
    """DoubtArtifactGenerator escreve em workspace, não em path hardcoded."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))

    import importlib
    from adk.shared.tools import doubt_tool as dt
    importlib.reload(dt)

    result = dt.DoubtArtifactGenerator.generate(
        trigger_type="test",
        trecho_suspeito="x",
        caminho_base=Path("doubt_artifacts"),
        id_artefato="TEST-001",
        motivo="teste de binding",
    )

    # extrai path do "SUCESSO: Artefato salvo em ..."
    import re
    match = re.search(r"Artefato salvo em (\S+)", result)
    assert match, f"Mensagem inesperada: {result}"
    saved_path = match.group(1).rstrip(".")

    # path deve estar sob tmp_path/tests/inputs/
    assert str(tmp_path) in saved_path, (
        f"Doubt artifact não foi para workspace: {saved_path}"
    )


def test_doubt_artifact_resolve_via_workspace(monkeypatch, tmp_path):
    """gerar_doubt_artifact (doubt_artifact.py) escreve em workspace, não em path hardcoded."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))

    import importlib
    from adk.shared.tools import doubt_artifact as da
    importlib.reload(da)

    result = da.gerar_doubt_artifact(
        reason_for_invalidation="teste de binding",
        artifact_id="DA-TEST-001",
    )

    assert result["status"] == "ok"
    saved_path = result["path"]

    # path deve estar sob tmp_path
    assert str(tmp_path) in saved_path, (
        f"Doubt artifact não foi para workspace: {saved_path}"
    )
