"""Adaptadores de execução para testes de integração das stacks do Coder."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import execution_adapters as runtime_adapters
from .integration_profiles import INTEGRATION_TEST_PROFILES
from .profile_orchestration import validate_test_path

_DEFAULT_TIMEOUT_SECONDS = 180


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
        if framework in dependencies or runtime_adapters.has_local_node_framework(
            root, framework
        ):
            return framework
    return "node:test"


def build_integration_command(
    profile_id: str,
    project_root: Path,
    test_path: Path,
) -> tuple[list[str] | None, str, str | None]:
    """Monta argv fechado sem aceitar comando fornecido pelo usuário."""
    root, test = validate_test_path(
        project_root,
        test_path,
        invalid_message="O teste de integração deve existir dentro do projeto.",
    )
    relative_test = test.relative_to(root).as_posix()
    if profile_id == "python-integration":
        return (
            [sys.executable, "-m", "pytest", relative_test, "-q", "--tb=short"],
            "pytest",
            None,
        )
    if profile_id == "node-integration":
        framework = detect_node_integration_framework(root)
        command, blocker = runtime_adapters.build_node_test_command(
            root, test, framework
        )
        return command, framework, blocker
    if profile_id == "java-integration":
        return runtime_adapters.build_java_test_command(root, test)
    if profile_id == "go-integration":
        command, blocker = runtime_adapters.build_go_test_command(root, test)
        return command, "go-testing", blocker
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
        root, test = validate_test_path(
            project_root,
            test_path,
            invalid_message="O teste de integração deve existir dentro do projeto.",
        )
        command, framework, blocker = build_integration_command(profile_id, root, test)
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
