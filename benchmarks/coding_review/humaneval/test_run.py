"""Unit tests for HumanEval benchmark CLI and Resume Guard validation in run.py."""

from __future__ import annotations

import argparse
import json
from unittest.mock import AsyncMock, patch

import pytest

from benchmarks.coding_review.humaneval import run


def test_main_missing_model():
    """Asserts ValueError is raised when --model is not provided."""
    with pytest.raises(ValueError, match="parâmetro '--model' é obrigatório"):
        run.main(["--limit", "5"])


def test_main_nonexistent_resume_dir(tmp_path):
    """Asserts FileNotFoundError is raised when --resume-dir does not exist."""
    non_existent = tmp_path / "non_existent_folder"
    with pytest.raises(FileNotFoundError, match="não existe ou não é um diretório"):
        run.main(["--model", "gpt-4", "--resume-dir", str(non_existent)])


def test_validar_e_persistir_config_new_run(tmp_path):
    """Asserts that a new run correctly persists parameters in metadata.json."""
    args = argparse.Namespace(
        model="gpt-4",
        samples=3,
        k=[1, 2],
        timeout=45,
    )
    run._validar_e_persistir_config(tmp_path, args)

    config_path = tmp_path / "metadata.json"
    assert config_path.is_file()

    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["model"] == "gpt-4"
    assert saved["samples"] == 3
    assert saved["k"] == [1, 2]
    assert saved["timeout"] == 45


def test_validar_e_persistir_config_resume_valid(tmp_path):
    """Asserts that resuming with identical parameters succeeds."""
    config_path = tmp_path / "metadata.json"
    original_config = {
        "model": "gpt-4",
        "samples": 3,
        "k": [1, 2],
        "timeout": 45,
    }
    config_path.write_text(json.dumps(original_config), encoding="utf-8")

    args = argparse.Namespace(
        model="gpt-4",
        samples=3,
        k=[1, 2],
        timeout=45,
    )
    # Should not raise any exception
    run._validar_e_persistir_config(tmp_path, args)


@pytest.mark.parametrize(
    "param_name, new_val, expected_msg",
    [
        (
            "model",
            "gpt-3.5",
            "modelo informado \\(gpt-3.5\\) difere do modelo original",
        ),
        ("samples", 5, "número de amostras original \\(3\\)"),
        ("k", [1], "métricas pass@k originais \\(\\[1, 2\\]\\)"),
        ("timeout", 30, "timeout original \\(45\\)"),
    ],
)
def test_validar_e_persistir_config_resume_mismatch(
    tmp_path, param_name, new_val, expected_msg
):
    """Asserts that a mismatch in any key parameter raises ValueError when resuming."""
    config_path = tmp_path / "metadata.json"
    original_config = {
        "model": "gpt-4",
        "samples": 3,
        "k": [1, 2],
        "timeout": 45,
    }
    config_path.write_text(json.dumps(original_config), encoding="utf-8")

    args = argparse.Namespace(
        model="gpt-4",
        samples=3,
        k=[1, 2],
        timeout=45,
    )
    setattr(args, param_name, new_val)

    with pytest.raises(ValueError, match=expected_msg):
        run._validar_e_persistir_config(tmp_path, args)


def test_validar_e_persistir_config_mangled_metadata_json(tmp_path):
    """Asserts that error in reading metadata.json raises ValueError."""
    config_path = tmp_path / "metadata.json"
    config_path.write_text("invalid-json{", encoding="utf-8")

    args = argparse.Namespace(
        model="gpt-4",
        samples=3,
        k=[1],
        timeout=45,
    )
    with pytest.raises(ValueError, match="Erro ao ler metadata.json"):
        run._validar_e_persistir_config(tmp_path, args)


def test_validar_e_persistir_config_retro_migration_progress_mismatch(tmp_path):
    """Asserts that samples mismatch against progress.jsonl raises ValueError."""
    progress_path = tmp_path / "progress.jsonl"
    progress_path.write_text(json.dumps({"n": 5}) + "\n", encoding="utf-8")

    args = argparse.Namespace(
        model="gpt-4",
        samples=3,
        k=[1],
        timeout=45,
    )
    with pytest.raises(
        ValueError,
        match="número de amostras original \\(5\\) encontrado em progress.jsonl",
    ):
        run._validar_e_persistir_config(tmp_path, args)


def test_validar_e_persistir_config_retro_migration_report_model_mismatch(tmp_path):
    """Asserts that model mismatch against report.json raises ValueError."""
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps({"model": "gpt-4", "pass_at_k": {"pass@1": 0.8}}), encoding="utf-8"
    )

    args = argparse.Namespace(
        model="gpt-3.5",
        samples=1,
        k=[1],
        timeout=45,
    )
    with pytest.raises(
        ValueError, match="modelo original \\(gpt-4\\) encontrado em report.json"
    ):
        run._validar_e_persistir_config(tmp_path, args)


def test_validar_e_persistir_config_retro_migration_report_k_mismatch(tmp_path):
    """Asserts that k metric mismatch against report.json raises ValueError."""
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps({"model": "gpt-4", "pass_at_k": {"pass@1": 0.8, "pass@5": 0.9}}),
        encoding="utf-8",
    )

    args = argparse.Namespace(
        model="gpt-4",
        samples=1,
        k=[1],
        timeout=45,
    )
    with pytest.raises(
        ValueError,
        match="métricas pass@k originais \\(\\[1, 5\\]\\) encontradas em report.json",
    ):
        run._validar_e_persistir_config(tmp_path, args)


def test_validar_e_persistir_config_retro_migration_success(tmp_path):
    """Asserts that valid backward migration creates metadata.json and passes."""
    progress_path = tmp_path / "progress.jsonl"
    progress_path.write_text(json.dumps({"n": 3}) + "\n", encoding="utf-8")

    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps({"model": "gpt-4", "pass_at_k": {"pass@1": 0.8, "pass@2": 0.95}}),
        encoding="utf-8",
    )

    args = argparse.Namespace(
        model="gpt-4",
        samples=3,
        k=[1, 2],
        timeout=45,
    )
    run._validar_e_persistir_config(tmp_path, args)

    # Should create metadata.json with the migrated parameters
    config_path = tmp_path / "metadata.json"
    assert config_path.is_file()
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["model"] == "gpt-4"
    assert saved["samples"] == 3
    assert saved["k"] == [1, 2]
    assert saved["timeout"] == 45


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("github_copilot/gpt-4", "github_copilot-gpt-4"),
        ("gpt-3.5-turbo", "gpt-3.5-turbo"),
        ("  spaced  name  ", "spaced-name"),
        ("weird//slashes\\\\here", "weird-slashes-here"),
        ("---", "na"),
        ("", "na"),
    ],
)
def test_sanitizar_componente(raw, expected):
    """Asserts model/component sanitization for safe directory names."""
    assert run._sanitizar_componente(raw) == expected


def test_construir_nome_run_basico():
    """Asserts descriptive run dir name includes model, samples and k."""
    args = argparse.Namespace(
        model="github_copilot/gpt-4",
        samples=3,
        k=[2, 1],
        limit=None,
    )
    nome = run._construir_nome_run(args, "20260822_120000")
    assert nome == "run_20260822_120000_github_copilot-gpt-4_n3_k1-2"


def test_construir_nome_run_com_limit():
    """Asserts run dir name appends the limit segment when provided."""
    args = argparse.Namespace(
        model="gpt-4",
        samples=1,
        k=[1],
        limit=5,
    )
    nome = run._construir_nome_run(args, "20260822_120000")
    assert nome == "run_20260822_120000_gpt-4_n1_k1_lim5"


def test_construir_nome_run_k_vazio():
    """Asserts run dir name falls back to k1 when k is empty."""
    args = argparse.Namespace(
        model="gpt-4",
        samples=2,
        k=[],
        limit=None,
    )
    nome = run._construir_nome_run(args, "20260822_120000")
    assert nome == "run_20260822_120000_gpt-4_n2_k1"


@patch("benchmarks.coding_review.humaneval.bootstrap.prepare_environment")
@patch("benchmarks.coding_review.humaneval.run._persistir_relatorio")
@patch("benchmarks.coding_review.humaneval.run._executar", new_callable=AsyncMock)
def test_main_happy_path(mock_executar, mock_persistir, mock_prepare_env, tmp_path):
    """Asserts main CLI execution works end-to-end under successful parameters."""
    run_dir = tmp_path / "run_folder"
    run_dir.mkdir()

    mock_executar.return_value = {
        "generated_at": "2026-08-22T00:00:00Z",
        "model": "gpt-4",
        "num_problems": 5,
        "samples_per_problem": 2,
        "pass_at_k": {"pass@1": 0.8},
        "problems": [],
    }
    mock_persistir.return_value = (run_dir / "report.json", run_dir / "report.md")

    argv = [
        "--model",
        "gpt-4",
        "--resume-dir",
        str(run_dir),
        "--samples",
        "2",
        "--k",
        "1",
    ]
    status = run.main(argv)

    assert status == 0
    mock_prepare_env.assert_called_once_with(run_dir / "workspace", model="gpt-4")
    mock_executar.assert_called_once()
    mock_persistir.assert_called_once()
