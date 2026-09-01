"""Contrato da preparação e coleta de evidências dos perfis unitários."""

import shutil
from pathlib import Path

import pytest

from shared.testing import UNIT_TEST_PROFILES, inspect_unit_test_project
from shared.testing import unit_evidence
from shared.testing.unit_evidence import (
    UNIT_EVIDENCE_CASES,
    collect_unit_profile_evidence,
    index_dev_ui_screenshots,
    prepare_unit_evidence_workspace,
)


def test_casos_de_evidencia_cobrem_todos_os_perfis_executaveis():
    implemented = {
        profile_id
        for profile_id, profile in UNIT_TEST_PROFILES.items()
        if profile.implemented
    }

    assert set(UNIT_EVIDENCE_CASES) == implemented


def test_matriz_ci_cobre_cada_perfil_executavel_uma_vez():
    workflow = (
        Path(__file__).resolve().parents[3]
        / ".github"
        / "workflows"
        / "unit-profile-matrix.yml"
    ).read_text(encoding="utf-8")
    matrix_profiles = [
        profile_id
        for line in workflow.splitlines()
        if line.strip().startswith("profiles:")
        for profile_id in line.split(":", 1)[1].strip().split()
    ]
    implemented = sorted(
        profile_id
        for profile_id, profile in UNIT_TEST_PROFILES.items()
        if profile.implemented
    )

    assert sorted(matrix_profiles) == implemented
    assert len(matrix_profiles) == len(set(matrix_profiles))


@pytest.mark.parametrize("profile_id", sorted(UNIT_EVIDENCE_CASES))
def test_fixture_de_evidencia_detecta_perfil_correto(tmp_path, profile_id):
    prepared = prepare_unit_evidence_workspace(
        profile_id,
        tmp_path / "workspace_output",
        include_reference_test=True,
    )

    inspection = inspect_unit_test_project(Path(prepared["project_root"]))

    assert inspection["status"] == "suportado"
    assert inspection["perfil"]["profile_id"] == profile_id
    assert prepared["prompt"]
    assert prepared["expected"]["minimum_tests"] == 2


@pytest.mark.parametrize("profile_id", sorted(UNIT_EVIDENCE_CASES))
def test_workspace_dev_ui_nao_inclui_teste_de_referencia(tmp_path, profile_id):
    prepared = prepare_unit_evidence_workspace(
        profile_id,
        tmp_path / profile_id / "workspace_output",
        include_reference_test=False,
    )

    assert prepared["test_path"] is None
    assert "detecte a stack" in prepared["prompt"]
    assert "integração" in prepared["prompt"]


def test_bootstrap_de_fixture_e_opt_in(tmp_path, monkeypatch):
    case = UNIT_EVIDENCE_CASES["node-vitest"]

    disabled = unit_evidence._bootstrap_runtime(case, tmp_path, enabled=False)

    assert disabled == {"status": "ignorado", "commands": []}

    runtime = (
        r"C:\Runtime With Space\npm.cmd"
        if unit_evidence.os.name == "nt"
        else "/runtime/npm"
    )
    monkeypatch.setattr(unit_evidence.shutil, "which", lambda _name: runtime)
    monkeypatch.setattr(
        unit_evidence.subprocess,
        "run",
        lambda command, **_kwargs: unit_evidence.subprocess.CompletedProcess(
            command,
            0,
            "prepared",
            "",
        ),
    )

    enabled = unit_evidence._bootstrap_runtime(case, tmp_path, enabled=True)

    assert enabled["status"] == "sucesso"
    assert enabled["commands"][0]["returncode"] == 0
    if unit_evidence.os.name == "nt":
        assert enabled["commands"][0]["command"] == [
            runtime,
            "install",
            "--ignore-scripts",
            "--no-audit",
            "--no-fund",
        ]


@pytest.mark.parametrize(
    ("profile_id", "runtime"),
    [
        ("python-pytest", "python"),
        ("node-node-test", "node"),
        ("go-testing", "go"),
    ],
)
def test_coleta_smoke_real_evidence_json(tmp_path, profile_id, runtime):
    if runtime != "python" and shutil.which(runtime) is None:
        pytest.skip(f"{runtime} não instalado")

    workspace_base = tmp_path / "short-workspaces"
    evidence = collect_unit_profile_evidence(
        profile_id,
        tmp_path / "run",
        workspace_base=workspace_base,
    )

    assert evidence["status"] == "sucesso"
    assert evidence["inspection"]["perfil"]["profile_id"] == profile_id
    assert evidence["execution"]["status"] == "sucesso"
    assert evidence["normalized_result"]["total"] >= 2
    assert evidence["normalized_result"]["falhas"] == 0
    assert evidence["runtime"]["available"] is True
    assert evidence["source_sha256"]
    assert Path(evidence["workspace"]["workspace_root"]).is_relative_to(workspace_base)


def test_indice_de_prints_exige_minimo_e_registra_hashes(tmp_path):
    screenshot_dir = tmp_path / "dev_ui" / "python-pytest"
    screenshot_dir.mkdir(parents=True)
    for index in range(1, 4):
        (screenshot_dir / f"0{index}_evidence.png").write_bytes(
            b"\x89PNG\r\n\x1a\n" + bytes([index])
        )

    manifest = index_dev_ui_screenshots(
        tmp_path,
        ["python-pytest"],
        minimum_per_profile=3,
    )

    assert manifest["status"] == "completo"
    assert manifest["missing_profiles"] == []
    assert manifest["profiles"]["python-pytest"]["count"] == 3
    assert all(
        item["sha256"] for item in manifest["profiles"]["python-pytest"]["screenshots"]
    )


def test_indice_de_prints_aponta_perfil_incompleto(tmp_path):
    manifest = index_dev_ui_screenshots(
        tmp_path,
        ["go-testing"],
        minimum_per_profile=3,
    )

    assert manifest["status"] == "incompleto"
    assert manifest["missing_profiles"] == ["go-testing"]
