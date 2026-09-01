"""Preparação e coleta reproduzível de evidências dos perfis unitários ativos."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.tools.pytest_runner import executar_pytest_tool

from .project_inspector import inspect_unit_test_project
from .unit_runner import executar_teste_unitario, unit_profile_execution_environment

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_FIXTURES_ROOT = _REPOSITORY_ROOT / "tests" / "fixtures" / "unit_profiles"
_WORKSPACE_MARKER = ".ai4se_workspace"


@dataclass(frozen=True)
class UnitEvidenceCase:
    """Caso mínimo usado tanto no smoke automatizado quanto na Dev UI."""

    profile_id: str
    title: str
    test_relative_path: str
    reference_test: str
    runtime_command: tuple[str, ...]
    requirement: str
    bootstrap_commands: tuple[tuple[str, ...], ...] = ()
    minimum_tests: int = 2

    @property
    def fixture_root(self) -> Path:
        return _FIXTURES_ROOT / self.profile_id

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["fixture_root"] = str(self.fixture_root)
        return result


UNIT_EVIDENCE_CASES: dict[str, UnitEvidenceCase] = {
    case.profile_id: case
    for case in (
        UnitEvidenceCase(
            profile_id="python-pytest",
            title="Python/FastAPI com pytest",
            test_relative_path="test_calculator.py",
            reference_test="test_calculator.py",
            runtime_command=("python", "--version"),
            requirement=(
                "Gere e execute testes unitários para calculator.py. Valide a soma "
                "de dois números e que divisão por zero lança ValueError."
            ),
        ),
        UnitEvidenceCase(
            profile_id="node-vitest",
            title="Node/TypeScript com Vitest",
            test_relative_path="tests/unit/calculator.test.ts",
            reference_test="calculator.test.ts",
            runtime_command=("node", "--version"),
            requirement=(
                "Gere e execute testes unitários para src/calculator.ts. Valide a "
                "soma de dois números e que divisão por zero lança RangeError."
            ),
            bootstrap_commands=(
                ("npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"),
            ),
        ),
        UnitEvidenceCase(
            profile_id="node-jest",
            title="Node/TypeScript com Jest",
            test_relative_path="tests/unit/calculator.test.js",
            reference_test="calculator.test.js",
            runtime_command=("node", "--version"),
            requirement=(
                "Gere e execute testes unitários para src/calculator.js. Valide a "
                "soma de dois números e que divisão por zero lança RangeError."
            ),
            bootstrap_commands=(
                ("npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"),
            ),
        ),
        UnitEvidenceCase(
            profile_id="node-node-test",
            title="Node/TypeScript com node:test",
            test_relative_path="tests/unit/calculator.test.js",
            reference_test="calculator.test.js",
            runtime_command=("node", "--version"),
            requirement=(
                "Gere e execute testes unitários para src/calculator.js. Valide a "
                "soma de dois números e que divisão por zero lança RangeError."
            ),
        ),
        UnitEvidenceCase(
            profile_id="node-mocha",
            title="Node/TypeScript com Mocha",
            test_relative_path="tests/unit/calculator.test.js",
            reference_test="calculator.test.js",
            runtime_command=("node", "--version"),
            requirement=(
                "Gere e execute testes unitários para src/calculator.js. Valide a "
                "soma de dois números e que divisão por zero lança RangeError."
            ),
            bootstrap_commands=(
                ("npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"),
            ),
        ),
        UnitEvidenceCase(
            profile_id="java-junit",
            title="Java/Spring com JUnit 5",
            test_relative_path="src/test/java/com/example/CalculatorTest.java",
            reference_test="CalculatorTest.java",
            runtime_command=("java", "--version"),
            requirement=(
                "Gere e execute testes unitários para src/main/java/com/example/"
                "Calculator.java. Valide a soma e a divisão por zero."
            ),
            bootstrap_commands=(("mvn", "-q", "-DskipTests", "test"),),
        ),
        UnitEvidenceCase(
            profile_id="go-testing",
            title="Go com testing",
            test_relative_path="calculator_test.go",
            reference_test="calculator_test.go",
            runtime_command=("go", "version"),
            requirement=(
                "Gere e execute testes unitários para calculator.go. Valide a soma "
                "de dois números e que divisão por zero retorna erro."
            ),
        ),
    )
}


def get_unit_evidence_case(profile_id: str) -> UnitEvidenceCase:
    try:
        return UNIT_EVIDENCE_CASES[profile_id]
    except KeyError:
        supported = ", ".join(sorted(UNIT_EVIDENCE_CASES))
        raise ValueError(
            f"Perfil de evidência desconhecido: '{profile_id}'. Opções: {supported}."
        ) from None


def build_dev_ui_prompt(case: UnitEvidenceCase) -> str:
    """Gera o prompt canônico usado nos prints da Dev UI."""
    return (
        "Execute somente o fluxo de testes unitários. O código-fonte já está "
        "persistido no workspace do Coder; detecte a stack sem usar "
        "stack_declarada. Não execute integração nem E2E. " + case.requirement
    )


def _ensure_empty_workspace(workspace_root: Path) -> Path:
    root = workspace_root.expanduser().resolve()
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(
            f"O workspace de evidência deve estar vazio: {root}. Use outro caminho."
        )
    root.mkdir(parents=True, exist_ok=True)
    (root / _WORKSPACE_MARKER).write_text(
        "Workspace exclusivo para evidências de perfis unitários.\n",
        encoding="utf-8",
    )
    return root


def prepare_unit_evidence_workspace(
    profile_id: str,
    workspace_root: Path,
    *,
    include_reference_test: bool,
) -> dict[str, Any]:
    """Materializa um projeto isolado sem instalar dependências."""
    case = get_unit_evidence_case(profile_id)
    root = _ensure_empty_workspace(workspace_root)
    source_project = case.fixture_root / "project"
    reference_test = case.fixture_root / "reference" / case.reference_test
    if not source_project.is_dir() or not reference_test.is_file():
        raise FileNotFoundError(f"Fixture incompleta para o perfil '{profile_id}'.")

    project_root = root / "coder" / "src"
    shutil.copytree(source_project, project_root)
    test_path = project_root / case.test_relative_path
    if include_reference_test:
        test_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(reference_test, test_path)

    session = {
        "profile_id": profile_id,
        "title": case.title,
        "workspace_root": str(root),
        "project_root": str(project_root),
        "prompt": build_dev_ui_prompt(case),
        "expected": {
            "inspection_status": "suportado",
            "profile_id": profile_id,
            "execution_status": "sucesso",
            "minimum_tests": case.minimum_tests,
        },
    }
    session_path = root / "dev_ui_session.json"
    session_path.write_text(
        json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    session["session_file"] = str(session_path)
    session["test_path"] = str(test_path) if include_reference_test else None
    return session


def _runtime_version(command: tuple[str, ...]) -> dict[str, Any]:
    executable = sys.executable if command[0] == "python" else shutil.which(command[0])
    if executable is None:
        return {"available": False, "command": list(command), "output": None}
    resolved = [executable, *command[1:]]
    try:
        process = subprocess.run(
            resolved,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "command": resolved, "output": str(exc)}
    output = "\n".join(
        part.strip() for part in (process.stdout, process.stderr) if part.strip()
    )
    return {
        "available": process.returncode == 0,
        "command": resolved,
        "output": output,
    }


def _bootstrap_command(declared: tuple[str, ...], executable: str) -> list[str]:
    if os.name == "nt" and declared[0] == "npm":
        npm_cli = (
            Path(executable).parent / "node_modules" / "npm" / "bin" / "npm-cli.js"
        )
        node = shutil.which("node")
        if node and npm_cli.is_file():
            return [node, str(npm_cli), *declared[1:]]
    return [executable, *declared[1:]]


def _bootstrap_runtime(
    case: UnitEvidenceCase,
    project_root: Path,
    *,
    enabled: bool,
) -> dict[str, Any]:
    if not case.bootstrap_commands:
        return {"status": "nao_necessario", "commands": []}
    if not enabled:
        return {"status": "ignorado", "commands": []}

    results: list[dict[str, Any]] = []
    for declared in case.bootstrap_commands:
        executable = shutil.which(declared[0])
        if executable is None:
            return {
                "status": "falha",
                "commands": results,
                "error": f"Comando de preparação indisponível: {declared[0]}",
            }
        command = _bootstrap_command(declared, executable)
        try:
            process = subprocess.run(
                command,
                cwd=str(project_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
                env=unit_profile_execution_environment(case.profile_id, executable),
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"status": "falha", "commands": results, "error": str(exc)}
        output = "\n".join(
            part.strip() for part in (process.stdout, process.stderr) if part.strip()
        )
        results.append(
            {"command": command, "returncode": process.returncode, "output": output}
        )
        if process.returncode != 0:
            return {
                "status": "falha",
                "commands": results,
                "error": f"Preparação terminou com código {process.returncode}.",
            }
    return {"status": "sucesso", "commands": results}


def _sha256_files(root: Path) -> dict[str, str]:
    ignored_names = {".coverage", "coverage.json", "report.json"}
    ignored_dirs = {
        ".gradle",
        ".pytest_cache",
        "__pycache__",
        "build",
        "node_modules",
        "target",
    }
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.name not in ignored_names
        and not any(part in ignored_dirs for part in path.relative_to(root).parts)
    }


def _execute_case(case: UnitEvidenceCase, project_root: Path, test_path: Path) -> dict:
    if case.profile_id == "python-pytest":
        return executar_pytest_tool(str(test_path))
    return executar_teste_unitario(case.profile_id, project_root, test_path)


def _normalized_execution_result(execution: dict) -> dict[str, Any]:
    tests = execution.get("testes")
    if isinstance(tests, dict):
        return {
            "total": int(tests.get("total", 0) or 0),
            "sucessos": int(tests.get("sucessos", 0) or 0),
            "falhas": int(tests.get("falhas", 0) or 0),
            "ignorados": int(tests.get("ignorados", 0) or 0),
            "cobertura_percentual": (execution.get("cobertura") or {}).get(
                "percentual"
            ),
        }
    successes = int(execution.get("testes_passaram", 0) or 0)
    failures = int(execution.get("testes_falharam", 0) or 0)
    skipped = int(execution.get("testes_ignorados", 0) or 0)
    return {
        "total": successes + failures + skipped,
        "sucessos": successes,
        "falhas": failures,
        "ignorados": skipped,
        "cobertura_percentual": (execution.get("cobertura") or {}).get("percentual"),
    }


def collect_unit_profile_evidence(
    profile_id: str,
    run_root: Path,
    *,
    bootstrap_runtime: bool = False,
    workspace_base: Path | None = None,
) -> dict[str, Any]:
    """Executa um smoke real e grava um envelope único de evidência."""
    case = get_unit_evidence_case(profile_id)
    output_root = run_root.expanduser().resolve()
    case_root = output_root / "results" / profile_id
    case_root.mkdir(parents=True, exist_ok=False)
    workspace_root = (
        workspace_base.expanduser().resolve() / profile_id / "workspace_output"
        if workspace_base is not None
        else output_root / "workspaces" / profile_id / "workspace_output"
    )
    prepared = prepare_unit_evidence_workspace(
        profile_id, workspace_root, include_reference_test=True
    )
    project_root = Path(prepared["project_root"])
    test_path = Path(prepared["test_path"])

    previous_workspace = os.environ.get("WORKSPACE_OUTPUT_DIR")
    os.environ["WORKSPACE_OUTPUT_DIR"] = str(workspace_root)
    try:
        bootstrap = _bootstrap_runtime(case, project_root, enabled=bootstrap_runtime)
        inspection = inspect_unit_test_project(project_root)
        execution = _execute_case(case, project_root, test_path)
    finally:
        if previous_workspace is None:
            os.environ.pop("WORKSPACE_OUTPUT_DIR", None)
        else:
            os.environ["WORKSPACE_OUTPUT_DIR"] = previous_workspace

    detected_profile = (inspection.get("perfil") or {}).get("profile_id")
    normalized_result = _normalized_execution_result(execution)
    passed = (
        inspection.get("status") == "suportado"
        and detected_profile == profile_id
        and execution.get("status") == "sucesso"
        and normalized_result["total"] >= prepared["expected"]["minimum_tests"]
        and normalized_result["falhas"] == 0
    )
    evidence = {
        "schema_version": "1.0",
        "evidence_type": "unit-profile-smoke",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "status": "sucesso" if passed else "falha",
        "case": case.to_dict(),
        "runtime": _runtime_version(case.runtime_command),
        "bootstrap": bootstrap,
        "workspace": prepared,
        "source_sha256": _sha256_files(project_root),
        "inspection": inspection,
        "execution": execution,
        "normalized_result": normalized_result,
    }
    evidence_path = case_root / "evidence.json"
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    evidence["evidence_file"] = str(evidence_path)
    return evidence


def index_dev_ui_screenshots(
    evidence_root: Path,
    profile_ids: list[str],
    *,
    minimum_per_profile: int = 3,
) -> dict[str, Any]:
    """Indexa prints da Dev UI com hash e valida o conjunto mínimo."""
    root = evidence_root.expanduser().resolve()
    profiles: dict[str, Any] = {}
    missing: list[str] = []
    for profile_id in profile_ids:
        get_unit_evidence_case(profile_id)
        screenshots = [
            {
                "file": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in sorted((root / "dev_ui" / profile_id).glob("*.png"))
        ]
        if len(screenshots) < minimum_per_profile:
            missing.append(profile_id)
        profiles[profile_id] = {
            "count": len(screenshots),
            "screenshots": screenshots,
        }

    manifest = {
        "schema_version": "1.0",
        "evidence_type": "unit-profile-dev-ui-screenshots",
        "indexed_at": datetime.now(timezone.utc).isoformat(),
        "status": "completo" if not missing else "incompleto",
        "minimum_per_profile": minimum_per_profile,
        "missing_profiles": missing,
        "profiles": profiles,
    }
    manifest_path = root / "dev_ui" / "screenshot_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest["manifest_file"] = str(manifest_path)
    return manifest
