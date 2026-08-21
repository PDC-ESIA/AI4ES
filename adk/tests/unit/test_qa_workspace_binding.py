"""Testes do binding do qa_pipeline ao workspace centralizado."""
import os
from pathlib import Path
import subprocess
from subprocess import CompletedProcess
import sys

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


@pytest.mark.parametrize(
    "caminho",
    [
        "tests/inputs/rf_001/test_rf_001.py",
        "workspace_output/tests/inputs/rf_001/test_rf_001.py",
    ],
)
def test_pytest_runner_nao_duplica_prefixo_do_workspace(
    monkeypatch,
    tmp_path,
    caminho,
):
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    arquivo = workspace / "tests" / "inputs" / "rf_001" / "test_rf_001.py"
    arquivo.parent.mkdir(parents=True)
    arquivo.write_text("def test_x(): assert True\n", encoding="utf-8")

    from adk.shared.tools.pytest_runner import _normalizar_caminho_arquivo

    assert _normalizar_caminho_arquivo(caminho) == arquivo.resolve()


def test_pytest_runner_aceita_caminho_absoluto_no_workspace(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    arquivo = workspace / "tests" / "inputs" / "rf_001" / "test_rf_001.py"
    arquivo.parent.mkdir(parents=True)
    arquivo.write_text("def test_x(): assert True\n", encoding="utf-8")

    from adk.shared.tools.pytest_runner import _normalizar_caminho_arquivo

    assert _normalizar_caminho_arquivo(str(arquivo)) == arquivo.resolve()


def test_pytest_runner_mapeia_workspace_output_para_raiz_configurada(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))
    arquivo = tmp_path / "tests" / "inputs" / "rf_001" / "test_rf_001.py"
    arquivo.parent.mkdir(parents=True)
    arquivo.write_text("def test_x(): assert True\n", encoding="utf-8")

    from adk.shared.tools.pytest_runner import _normalizar_caminho_arquivo

    caminho = "workspace_output/tests/inputs/rf_001/test_rf_001.py"
    assert _normalizar_caminho_arquivo(caminho) == arquivo.resolve()


def test_pytest_runner_nao_aprova_suite_totalmente_ignorada(tmp_path):
    from adk.shared.tools.pytest_runner import _parse_resultados_pytest

    teste = tmp_path / "test_rf_001.py"
    resultado_pytest = CompletedProcess(
        args=["pytest"],
        returncode=0,
        stdout="================ 12 skipped in 0.10s ================",
        stderr="",
    )

    resultado = _parse_resultados_pytest(
        teste,
        resultado_pytest,
        tmp_path / "coverage.json",
    )

    assert resultado["status"] == "falha"
    assert resultado["resultado_resumo"] == "falha_total"
    assert resultado["testes_passaram"] == 0
    assert resultado["testes_ignorados"] == 12
    assert resultado["erros"][0]["codigo"] == "ERR_NENHUM_TESTE_EXECUTADO"


def test_pytest_runner_importa_pacote_src_materializado(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    suite = workspace / "tests" / "inputs" / "rf_test_001"
    source = suite / "src"
    source.mkdir(parents=True)
    (source / "__init__.py").write_text("", encoding="utf-8")
    (source / "price_rules.py").write_text("RATE = 5\n", encoding="utf-8")
    (source / "checkout.py").write_text(
        "from .price_rules import RATE\n\n"
        "def calculate():\n"
        "    return RATE\n",
        encoding="utf-8",
    )
    test_file = suite / "test_rf_test_001.py"
    test_file.write_text(
        "from src.checkout import calculate\n\n"
        "def test_integracao():\n"
        "    assert calculate() == 5\n",
        encoding="utf-8",
    )

    from shared.tools.pytest_runner import executar_pytest_tool

    result = executar_pytest_tool(
        "tests/inputs/rf_test_001/test_rf_test_001.py"
    )

    assert result["status"] == "sucesso"
    assert result["testes_passaram"] == 1
    assert result["testes_ignorados"] == 0


def test_bootstrap_reprioriza_suite_ja_presente_no_pythonpath(
    monkeypatch,
    tmp_path,
):
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    suite = workspace / "tests" / "inputs" / "rf_test_001"
    source = suite / "src"
    source.mkdir(parents=True)
    # Reproduz a sessão real: o Coder entregou init.py em vez de __init__.py.
    (source / "init.py").write_text("", encoding="utf-8")
    (source / "checkout.py").write_text(
        "def calculate():\n"
        "    return 42\n",
        encoding="utf-8",
    )
    test_file = suite / "test_rf_test_001.py"
    test_file.write_text(
        "from src.checkout import calculate\n\n"
        "def test_integracao():\n"
        "    assert calculate() == 42\n",
        encoding="utf-8",
    )

    from src.agents.qa_agent.subagents.receive_requirements.io import (
        _salvar_bootstrap_pytest,
    )

    bootstrap = _salvar_bootstrap_pytest(suite)
    assert bootstrap == suite / "conftest.py"
    assert (source / "__init__.py").is_file()
    env = os.environ.copy()
    # Reproduz o runner: os paths já chegam no PYTHONPATH, mas o pytest insere
    # a raiz do ADK à frente deles ao descobrir o pyproject.toml.
    env["PYTHONPATH"] = os.pathsep.join((str(suite), str(source)))
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(test_file)],
        cwd=suite,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout


def test_pytest_runner_localiza_basename_unico_para_code_fix(
    monkeypatch,
    tmp_path,
):
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    test_file = (
        workspace
        / "tests"
        / "inputs"
        / "rf_e2e_001"
        / "test_rf_e2e_001.py"
    )
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok(): assert True\n", encoding="utf-8")

    from shared.tools.pytest_runner import _normalizar_caminho_arquivo

    assert _normalizar_caminho_arquivo("test_rf_e2e_001.py") == test_file.resolve()


def test_pytest_runner_rejeita_basename_ambiguo(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    for slug in ("rf_001", "rf_002"):
        test_file = workspace / "tests" / "inputs" / slug / "test_repetido.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("def test_ok(): assert True\n", encoding="utf-8")

    from shared.tools.pytest_runner import _normalizar_caminho_arquivo

    with pytest.raises(ValueError, match="Nome de teste ambíguo"):
        _normalizar_caminho_arquivo("test_repetido.py")


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
    match = re.search(r"Artefato salvo em (.+?\.md)\.", result)
    assert match, f"Mensagem inesperada: {result}"
    saved_path = match.group(1)

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
