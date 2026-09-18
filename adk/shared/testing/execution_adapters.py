"""Construção segura de comandos reutilizada pelos níveis de teste."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

_NODE_ENTRIES = {
    "vitest": Path("node_modules/vitest/vitest.mjs"),
    "jest": Path("node_modules/jest/bin/jest.js"),
    "mocha": Path("node_modules/mocha/bin/mocha.js"),
}


def has_local_node_framework(root: Path, framework: str) -> bool:
    """Informa se o runner Node conhecido já está instalado no projeto."""
    entry = _NODE_ENTRIES.get(framework)
    return bool(entry and (root / entry).is_file())


def build_node_test_command(
    root: Path,
    test: Path,
    framework: str,
    *,
    coverage: bool = False,
) -> tuple[list[str] | None, str | None]:
    """Usa Node e runners locais, sem shell ou instalação implícita."""
    node = shutil.which("node")
    if node is None:
        return None, "Node.js não está disponível no ambiente."
    relative_test = test.relative_to(root).as_posix()
    if framework == "node:test":
        strip_types = (
            ["--experimental-strip-types"]
            if test.suffix.casefold() in {".ts", ".mts", ".cts"}
            else []
        )
        return [node, *strip_types, "--test", relative_test], None

    entry = root / _NODE_ENTRIES[framework]
    if not entry.is_file():
        return None, f"{framework} não está instalado localmente no projeto."
    if framework == "vitest":
        return [node, str(entry), "run", relative_test, "--reporter=verbose"], None
    if framework == "jest":
        command = [node, str(entry), relative_test, "--runInBand"]
        return [*command, "--coverage"] if coverage else command, None
    return [node, str(entry), relative_test, "--reporter", "spec"], None


def _qualified_java_test(test: Path) -> str:
    content = test.read_text(encoding="utf-8", errors="replace")
    package = re.search(r"^\s*package\s+([\w.]+)\s*;?", content, re.MULTILINE)
    declared_class = re.search(r"\b(?:public\s+)?(?:final\s+)?class\s+(\w+)", content)
    class_name = declared_class.group(1) if declared_class else test.stem
    return f"{package.group(1)}.{class_name}" if package else class_name


def build_java_test_command(
    root: Path, test: Path
) -> tuple[list[str] | None, str, str | None]:
    """Seleciona Maven ou Gradle, priorizando o wrapper do projeto."""
    test_name = _qualified_java_test(test)
    if (root / "pom.xml").is_file():
        wrapper = root / ("mvnw.cmd" if os.name == "nt" else "mvnw")
        executable = wrapper if wrapper.is_file() else shutil.which("mvn")
        if executable is None:
            return None, "junit-maven", "Maven não está disponível."
        return [str(executable), f"-Dtest={test_name}", "test"], "junit-maven", None
    if (root / "build.gradle").is_file() or (root / "build.gradle.kts").is_file():
        wrapper = root / ("gradlew.bat" if os.name == "nt" else "gradlew")
        executable = wrapper if wrapper.is_file() else shutil.which("gradle")
        if executable is None:
            return None, "junit-gradle", "Gradle não está disponível."
        return (
            [str(executable), "test", "--tests", test_name, "--console=plain"],
            "junit-gradle",
            None,
        )
    return None, "junit", "O projeto Java não possui manifesto Maven ou Gradle."


def build_go_test_command(
    root: Path, test: Path, *, coverage_path: Path | None = None
) -> tuple[list[str] | None, str | None]:
    """Executa somente o pacote que contém o teste Go."""
    executable = shutil.which("go")
    if executable is None:
        return None, "Go não está disponível no ambiente."
    if not (root / "go.mod").is_file():
        return None, "O projeto Go não possui go.mod."
    relative_parent = test.parent.relative_to(root).as_posix()
    package = "." if relative_parent == "." else f"./{relative_parent}"
    coverage = [f"-coverprofile={coverage_path}"] if coverage_path else []
    return [executable, "test", "-json", *coverage, package], None


__all__ = [
    "build_go_test_command",
    "build_java_test_command",
    "build_node_test_command",
    "has_local_node_framework",
]
