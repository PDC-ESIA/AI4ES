"""Testes de regressão (P6.5) documentando garantias já existentes nas 4
funções de validação de path investigadas para os guard rails do QA agent —
sem alterar nenhuma delas. Cobrem casos adversariais que hoje já são
rejeitados/contidos corretamente, mas não tinham um teste direto provando
isso (ver investigação "Parte 2 — Superfície das 4 validações de path").
"""

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# pytest_runner.py::_normalizar_caminho_arquivo
# ---------------------------------------------------------------------------


def test_normalizar_caminho_confirma_basename_ambiguo_levanta_valueerror(
    monkeypatch, tmp_path
):
    """Já coberto por test_pytest_runner_rejeita_basename_ambiguo em
    test_qa_workspace_binding.py — repetido aqui para manter as 4 funções
    de path juntas num único lugar de referência."""
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    for slug in ("rf_001", "rf_002"):
        test_file = workspace / "tests" / "inputs" / slug / "test_repetido.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("def test_ok(): assert True\n", encoding="utf-8")

    from shared.tools.pytest_runner import _normalizar_caminho_arquivo

    with pytest.raises(ValueError, match="Nome de teste ambíguo"):
        _normalizar_caminho_arquivo("test_repetido.py")


def test_normalizar_caminho_fallback_forca_absoluto_externo_para_base_dir(
    monkeypatch, tmp_path
):
    """Um path absoluto totalmente fora do workspace (nem workspace_root,
    nem tests/inputs) é forçado de volta para dentro de base_dir usando só
    o basename — nunca escapa."""
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    from shared.tools.pytest_runner import _normalizar_caminho_arquivo
    from shared.workspace import get_agent_workspace

    resultado = _normalizar_caminho_arquivo("/etc/test_evil.py")

    base_dir = get_agent_workspace("receive_requirements").resolve()
    assert resultado == (base_dir / "test_evil.py").resolve()
    assert resultado.is_relative_to(base_dir)


def test_normalizar_caminho_basename_inexistente_fica_em_base_dir(
    monkeypatch, tmp_path
):
    """Basename test_*.py que não bate com nenhum arquivo real em
    tests/inputs continua contido em base_dir (não vira busca externa)."""
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    from shared.tools.pytest_runner import _normalizar_caminho_arquivo
    from shared.workspace import get_agent_workspace

    resultado = _normalizar_caminho_arquivo("test_nunca_existiu.py")

    base_dir = get_agent_workspace("receive_requirements").resolve()
    assert resultado.is_relative_to(base_dir)
    assert resultado.name == "test_nunca_existiu.py"


# ---------------------------------------------------------------------------
# receive_requirements/io.py::_salvar_arquivos_apoio
# ---------------------------------------------------------------------------


def test_salvar_arquivos_apoio_rejeita_path_absoluto_fora_do_workspace(
    monkeypatch, tmp_path
):
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    from src.agents.qa_agent.subagents.receive_requirements.io import (
        _salvar_arquivos_apoio,
    )

    destino = workspace / "tests" / "inputs" / "rf_001"
    destino.mkdir(parents=True)

    artefato = {"arquivos_apoio": [{"path": "/etc/passwd"}]}
    salvos = _salvar_arquivos_apoio(artefato, destino)

    # /etc/passwd não é relative_to(workspace_root) -> source fica None ->
    # sem conteudo/conteudo_base64, o item é descartado silenciosamente.
    assert salvos == []
    assert not any(destino.iterdir())


def test_salvar_arquivos_apoio_rejeita_path_com_traversal(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    from src.agents.qa_agent.subagents.receive_requirements.io import (
        _salvar_arquivos_apoio,
    )

    destino = workspace / "tests" / "inputs" / "rf_001"
    destino.mkdir(parents=True)

    artefato = {
        "arquivos_apoio": [{"path": "../../../../../../../../etc/passwd"}]
    }
    salvos = _salvar_arquivos_apoio(artefato, destino)

    assert salvos == []
    assert not any(destino.iterdir())


def test_salvar_arquivos_apoio_sanitiza_nome_com_traversal_e_contem_em_destino(
    monkeypatch, tmp_path
):
    """Conteúdo inline (sem `path`) com `nome` tentando escapar via `../` —
    _safe_filename remove os separadores e o arquivo fica dentro de
    `destino`, nunca em outro lugar."""
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    from src.agents.qa_agent.subagents.receive_requirements.io import (
        _salvar_arquivos_apoio,
    )

    destino = workspace / "tests" / "inputs" / "rf_001"
    destino.mkdir(parents=True)

    artefato = {
        "arquivos_apoio": [
            {"nome": "../../evil.py", "conteudo": "print('oi')\n"}
        ]
    }
    salvos = _salvar_arquivos_apoio(artefato, destino)

    assert len(salvos) == 1
    arquivo = salvos[0]
    assert arquivo.is_relative_to(destino.resolve())
    assert arquivo.is_file()
    assert not (workspace / "evil.py").exists()
    assert not (destino.parent / "evil.py").exists()


# ---------------------------------------------------------------------------
# qa_test_files.py::_resolve_qa_test
# ---------------------------------------------------------------------------


def test_resolve_qa_test_rejeita_caminho_para_coder(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    coder_file = workspace / "coder" / "src" / "test_x.py"
    coder_file.parent.mkdir(parents=True)
    coder_file.write_text("def test_x(): assert True\n", encoding="utf-8")

    from shared.tools.qa_test_files import _resolve_qa_test

    with pytest.raises(ValueError, match="tests/inputs"):
        _resolve_qa_test(str(coder_file))


def test_resolve_qa_test_rejeita_nome_sem_prefixo_test(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    arquivo = workspace / "tests" / "inputs" / "rf_001" / "helper.py"
    arquivo.parent.mkdir(parents=True)
    arquivo.write_text("def f(): pass\n", encoding="utf-8")

    from shared.tools.qa_test_files import _resolve_qa_test

    with pytest.raises(ValueError, match="Somente arquivos Python test_"):
        _resolve_qa_test(str(arquivo))
