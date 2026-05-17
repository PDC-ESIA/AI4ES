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

    from src.agents.qa_agent.tools.pytest_runner import _normalizar_caminho_arquivo

    resultado = _normalizar_caminho_arquivo("hu_001/test_hu_001.py")
    assert resultado == arquivo.resolve()
