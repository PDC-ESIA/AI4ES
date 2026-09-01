"""Adaptadores de execução para testes de integração das stacks do Coder."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .integration_profiles import INTEGRATION_TEST_PROFILES

_DEFAULT_TIMEOUT_SECONDS = 180
_NODE_ENTRIES = {
    "vitest": Path("node_modules/vitest/vitest.mjs"),
    "jest": Path("node_modules/jest/bin/jest.js"),
    "mocha": Path("node_modules/mocha/bin/mocha.js"),
}


def _command_path(name: str) -> str | None:
    return shutil.which(name)


def _blocked(profile_id: str, code: str, message: str) -> dict[str, Any]:
    return {
        "status": "bloqueado",
        "tipo_teste": "integracao",
        "perfil": profile_id,
        "framework": None,
        "comando": [],
        "codigo_saida": None,
        "stdout": "",
        "stderr": "",
        "bloqueios": [{"codigo": code, "mensagem": message}],
    }


def _validate_paths(project_root: Path, test_path: Path) -> tuple[Path, Path]:
    root = project_root.resolve()
    test = test_path.resolve()
    if not root.is_dir():
        raise ValueError(f"Projeto não encontrado: {root}")
    if not test.is_file() or not test.is_relative_to(root):
        raise ValueError("O teste de integração deve existir dentro do projeto.")
    return root, test


def _package_dependencies(root: Path) -> set[str]:
    try:
        package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    dependencies: set[str] = set()
    for field in ("dependencies", "devDependencies", "peerDependencies"):
        values = package.get(field, {})
        if isinstance(values, dict):
            dependencies.update(str(name).casefold() for name in values)
    return dependencies


def detect_node_integration_framework(root: Path) -> str:
    """Usa o runner declarado pelo projeto; Node nativo é o fallback."""
    dependencies = _package_dependencies(root)
    for framework in ("vitest", "jest", "mocha"):
        if framework in dependencies or (root / _NODE_ENTRIES[framework]).is_file():
            return framework
    return "node:test"


def _node_command(
    root: Path, test: Path
) -> tuple[list[str] | None, str, str | None]:
    node = _command_path("node")
    framework = detect_node_integration_framework(root)
    if node is None:
        return None, framework, "Node.js não está disponível no ambiente."
    relative_test = test.relative_to(root).as_posix()
    if framework == "node:test":
        return [node, "--test", relative_test], framework, None
    entry = root / _NODE_ENTRIES[framework]
    if not entry.is_file():
        return (
            None,
            framework,
            f"{framework} está declarado, mas não instalado localmente no projeto.",
        )
    if framework == "vitest":
        return (
            [node, str(entry), "run", relative_test, "--reporter=verbose"],
            framework,
            None,
        )
    if framework == "jest":
        return [node, str(entry), relative_test, "--runInBand"], framework, None
    return [node, str(entry), relative_test, "--reporter", "spec"], framework, None


def _qualified_java_test(test: Path) -> str:
    content = test.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^\s*package\s+([\w.]+)\s*;?", content, re.MULTILINE)
    return f"{match.group(1)}.{test.stem}" if match else test.stem


def _java_command(
    root: Path, test: Path
) -> tuple[list[str] | None, str, str | None]:
    test_name = _qualified_java_test(test)
    if (root / "pom.xml").is_file():
        wrapper = root / ("mvnw.cmd" if os.name == "nt" else "mvnw")
        executable: Path | str | None = (
            wrapper if wrapper.is_file() else _command_path("mvn")
        )
        if executable is None:
            return None, "junit-maven", "Maven não está disponível."
        return [str(executable), f"-Dtest={test_name}", "test"], "junit-maven", None
    if (root / "build.gradle").is_file() or (root / "build.gradle.kts").is_file():
        wrapper = root / ("gradlew.bat" if os.name == "nt" else "gradlew")
        executable = wrapper if wrapper.is_file() else _command_path("gradle")
        if executable is None:
            return None, "junit-gradle", "Gradle não está disponível."
        return (
            [str(executable), "test", "--tests", test_name, "--console=plain"],
            "junit-gradle",
            None,
        )
    return None, "junit", "O projeto Java não possui manifesto Maven ou Gradle."


def build_integration_command(
    profile_id: str,
    project_root: Path,
    test_path: Path,
) -> tuple[list[str] | None, str, str | None]:
    """Monta argv fechado sem aceitar comando fornecido pelo usuário."""
    root, test = _validate_paths(project_root, test_path)
    relative_test = test.relative_to(root).as_posix()
    if profile_id == "python-integration":
        return (
            [sys.executable, "-m", "pytest", relative_test, "-q", "--tb=short"],
            "pytest",
            None,
        )
    if profile_id == "node-integration":
        return _node_command(root, test)
    if profile_id == "java-integration":
        return _java_command(root, test)
    if profile_id == "go-integration":
        executable = _command_path("go")
        if executable is None:
            return None, "go-testing", "Go não está disponível no ambiente."
        if not (root / "go.mod").is_file():
            return None, "go-testing", "O projeto Go não possui go.mod."
        relative_parent = test.parent.relative_to(root).as_posix()
        package = "." if relative_parent == "." else f"./{relative_parent}"
        return [executable, "test", "-json", package], "go-testing", None
    return None, "desconhecido", f"Perfil de integração desconhecido: {profile_id}."


def execute_integration_adapter(
    profile_id: str,
    project_root: Path,
    test_path: Path,
    *,
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Executa o adaptador e devolve o resultado bruto ao normalizador."""
    if INTEGRATION_TEST_PROFILES.get(profile_id) is None:
        return _blocked(profile_id, "PERFIL_DESCONHECIDO", "Perfil não registrado.")
    try:
        root, test = _validate_paths(project_root, test_path)
        command, framework, blocker = build_integration_command(
            profile_id, root, test
        )
    except ValueError as exc:
        return _blocked(profile_id, "CAMINHO_TESTE_INVALIDO", str(exc))
    if command is None:
        return _blocked(
            profile_id,
            "RUNTIME_DEPENDENCY_MISSING",
            blocker or "Executor de integração indisponível.",
        )

    environment = os.environ.copy()
    environment["CI"] = "1"
    try:
        process = subprocess.run(
            command,
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            env=environment,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return _blocked(
            profile_id,
            "ERR_TIMEOUT",
            f"A execução ultrapassou {timeout_seconds} segundos.",
        )
    except OSError as exc:
        return _blocked(profile_id, "ERR_EXECUTOR", str(exc))

    return {
        "status": "sucesso" if process.returncode == 0 else "falha",
        "tipo_teste": "integracao",
        "perfil": profile_id,
        "framework": framework,
        "comando": command,
        "codigo_saida": process.returncode,
        "stdout": process.stdout or "",
        "stderr": process.stderr or "",
        "bloqueios": [],
    }


__all__ = [
    "build_integration_command",
    "detect_node_integration_framework",
    "execute_integration_adapter",
]
