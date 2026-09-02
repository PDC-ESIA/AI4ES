"""Executores determinísticos das stacks não Python publicadas pelo Coder."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from shared.workspace import get_agent_workspace

from .unit_profiles import get_unit_test_profile

_DEFAULT_TIMEOUT_SECONDS = 120
_ANSI_ESCAPE_RE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|[@-_])")


def _blocked(profile_id: str, code: str, message: str) -> dict[str, Any]:
    return {
        "status": "bloqueado",
        "tipo_teste": "unitario",
        "perfil": profile_id,
        "comando": [],
        "testes": {"total": 0, "sucessos": 0, "falhas": 0, "ignorados": 0},
        "cobertura": {"percentual": None, "formato": None, "arquivo": None},
        "saida": "",
        "erros": [{"codigo": code, "mensagem": message}],
    }


def _validate_paths(project_root: Path, test_path: Path) -> tuple[Path, Path]:
    root = project_root.resolve()
    test = test_path.resolve()
    if not root.is_dir():
        raise ValueError(f"Projeto não encontrado: {root}")
    if not test.is_file() or not test.is_relative_to(root):
        raise ValueError("O teste deve existir dentro do projeto gerenciado.")
    return root, test


def _command_path(name: str) -> str | None:
    return shutil.which(name)


def unit_profile_execution_environment(
    profile_id: str, executable: str
) -> dict[str, str]:
    """Monta o ambiente comum sem instalar ou alterar runtimes."""
    del profile_id, executable
    environment = os.environ.copy()
    environment["CI"] = "1"
    return environment


def _batch_command(executable: Path | str, arguments: list[str]) -> list[str]:
    return [str(executable), *arguments]


def _node_command(
    profile_id: str, root: Path, test: Path
) -> tuple[list[str] | None, str | None]:
    node = _command_path("node")
    if not node:
        return None, "Node.js não está disponível no ambiente."
    relative_test = test.relative_to(root).as_posix()
    entries = {
        "node-vitest": root / "node_modules" / "vitest" / "vitest.mjs",
        "node-jest": root / "node_modules" / "jest" / "bin" / "jest.js",
        "node-mocha": root / "node_modules" / "mocha" / "bin" / "mocha.js",
    }
    if profile_id == "node-node-test":
        return [node, "--test", relative_test], None
    entry = entries[profile_id]
    if not entry.is_file():
        framework = profile_id.removeprefix("node-")
        return None, (
            f"{framework} não está instalado localmente no projeto. "
            "Instale as dependências declaradas antes da execução."
        )
    if profile_id == "node-vitest":
        return [node, str(entry), "run", relative_test, "--reporter=verbose"], None
    if profile_id == "node-jest":
        return [node, str(entry), relative_test, "--runInBand", "--coverage"], None
    return [node, str(entry), relative_test, "--reporter", "spec"], None


def _jvm_test_name(test: Path) -> str:
    text = test.read_text(encoding="utf-8", errors="replace")
    package_match = re.search(r"^\s*package\s+([\w.]+)\s*;?", text, re.MULTILINE)
    class_match = re.search(
        r"\b(?:public\s+)?(?:final\s+)?class\s+(\w+)",
        text,
    )
    class_name = class_match.group(1) if class_match else test.stem
    return f"{package_match.group(1)}.{class_name}" if package_match else class_name


def _jvm_command(root: Path, test: Path) -> tuple[list[str] | None, str | None]:
    test_name = _jvm_test_name(test)
    if (root / "pom.xml").is_file():
        wrapper = root / ("mvnw.cmd" if os.name == "nt" else "mvnw")
        executable: Path | str | None = (
            wrapper if wrapper.is_file() else _command_path("mvn")
        )
        if executable is None:
            return None, "Maven não está disponível e o projeto não possui wrapper."
        return _batch_command(executable, [f"-Dtest={test_name}", "test"]), None
    if (root / "build.gradle").is_file() or (root / "build.gradle.kts").is_file():
        wrapper = root / ("gradlew.bat" if os.name == "nt" else "gradlew")
        executable = wrapper if wrapper.is_file() else _command_path("gradle")
        if executable is None:
            return None, "Gradle não está disponível e o projeto não possui wrapper."
        return _batch_command(
            executable,
            ["test", "--tests", test_name, "--console=plain"],
        ), None
    return None, "O projeto Java não possui pom.xml, build.gradle ou build.gradle.kts."


def _go_command(
    root: Path, test: Path
) -> tuple[list[str] | None, str | None, Path | None]:
    executable = _command_path("go")
    if not executable:
        return None, "Go não está disponível no ambiente.", None
    if not (root / "go.mod").is_file():
        return None, "O projeto Go não possui go.mod.", None
    coverage_dir = get_agent_workspace("unit_test_generator") / "coverage"
    coverage_dir.mkdir(parents=True, exist_ok=True)
    coverage_path = coverage_dir / f"{test.stem}.out"
    relative_parent = test.parent.relative_to(root).as_posix()
    package = "." if relative_parent == "." else f"./{relative_parent}"
    return (
        [executable, "test", "-json", f"-coverprofile={coverage_path}", package],
        None,
        coverage_path,
    )


def _parse_go_json(output: str) -> dict[str, int]:
    tests: dict[str, str] = {}
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        test_name = event.get("Test")
        action = event.get("Action")
        if isinstance(test_name, str) and action in {"pass", "fail", "skip"}:
            tests[test_name] = action
    return {
        "total": len(tests),
        "sucessos": sum(value == "pass" for value in tests.values()),
        "falhas": sum(value == "fail" for value in tests.values()),
        "ignorados": sum(value == "skip" for value in tests.values()),
    }


def _counts(total: int, failed: int = 0, skipped: int = 0) -> dict[str, int]:
    return {
        "total": total,
        "sucessos": max(0, total - failed - skipped),
        "falhas": failed,
        "ignorados": skipped,
    }


def _strip_ansi(output: str) -> str:
    """Remove sequências de estilo emitidas pelos runners em terminais CI."""
    return _ANSI_ESCAPE_RE.sub("", output)


def _parse_counts(profile_id: str, output: str, returncode: int) -> dict[str, int]:
    output = _strip_ansi(output)
    if profile_id == "go-testing":
        return _parse_go_json(output)
    if re.search(
        r"no tests? (?:were found|is available|matches)", output, re.IGNORECASE
    ):
        return _counts(0)

    if profile_id == "java-junit":
        matches = re.findall(
            r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)",
            output,
        )
        if matches:
            total, failures, errors, skipped = map(int, matches[-1])
            return _counts(total, failures + errors, skipped)
        gradle = re.search(
            r"(\d+) tests completed(?:, (\d+) failed)?(?:, (\d+) skipped)?", output
        )
        if gradle:
            return _counts(*(int(value or 0) for value in gradle.groups()))
        statuses = re.findall(
            r"^.+\s>\s.+\s(PASSED|FAILED|SKIPPED)\s*$",
            output,
            re.MULTILINE,
        )
        if statuses:
            return _counts(
                len(statuses), statuses.count("FAILED"), statuses.count("SKIPPED")
            )

    if profile_id == "node-vitest":
        match = re.search(
            r"Tests\s+(?:(\d+)\s+passed)?(?:\s*\|\s*)?(?:(\d+)\s+failed)?(?:\s*\|\s*)?(?:(\d+)\s+skipped)?",
            output,
            re.IGNORECASE,
        )
        if match:
            passed, failed, skipped = (int(value or 0) for value in match.groups())
            return _counts(passed + failed + skipped, failed, skipped)
    if profile_id == "node-jest":
        match = re.search(
            r"Tests:\s*(?:(\d+) failed,\s*)?(?:(\d+) skipped,\s*)?(?:(\d+) passed,\s*)?(\d+) total",
            output,
            re.IGNORECASE,
        )
        if match:
            failed, skipped, _passed, total = (
                int(value or 0) for value in match.groups()
            )
            return _counts(total, failed, skipped)
    if profile_id == "node-node-test":
        values = {
            key: (
                int(match.group(1))
                if (
                    match := re.search(
                        rf"^.*?\b{key}\s+(\d+)\s*$",
                        output,
                        re.MULTILINE | re.IGNORECASE,
                    )
                )
                else 0
            )
            for key in ("tests", "pass", "fail", "skipped")
        }
        if values["tests"]:
            return _counts(values["tests"], values["fail"], values["skipped"])
    if profile_id == "node-mocha":
        passed = int((re.search(r"(\d+) passing", output) or [0, 0])[1])
        failed = int((re.search(r"(\d+) failing", output) or [0, 0])[1])
        skipped = int((re.search(r"(\d+) pending", output) or [0, 0])[1])
        if passed + failed + skipped:
            return _counts(passed + failed + skipped, failed, skipped)

    return _counts(0 if returncode else 1, 1 if returncode else 0)


def _coverage_percent(profile_id: str, output: str) -> float | None:
    output = _strip_ansi(output)
    patterns = {
        "go-testing": r"coverage:\s*([\d.]+)%",
        "node-vitest": r"All files[^\n]*?([\d.]+)\s*%",
        "node-jest": r"All files[^\n]*?([\d.]+)\s*%",
        "node-node-test": r"all files[^\n]*?([\d.]+)\s*%",
        "java-junit": r"Total[^%\n]*?([\d.]+)%",
    }
    pattern = patterns.get(profile_id)
    match = re.search(pattern, output, re.IGNORECASE) if pattern else None
    return float(match.group(1)) if match else None


def _build_command(
    profile_id: str,
    root: Path,
    test: Path,
) -> tuple[list[str] | None, str | None, Path | None]:
    coverage_path: Path | None = None
    if profile_id.startswith("node-"):
        command, blocker = _node_command(profile_id, root, test)
    elif profile_id == "java-junit":
        command, blocker = _jvm_command(root, test)
    elif profile_id == "go-testing":
        return _go_command(root, test)
    else:
        command, blocker = (
            None,
            f"O perfil '{profile_id}' não pertence ao catálogo atual do Coder.",
        )
    return command, blocker, coverage_path


def executar_teste_unitario(
    profile_id: str,
    project_root: Path,
    test_path: Path,
    *,
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Executa um teste usando somente o comando fixo do perfil selecionado."""
    try:
        root, test = _validate_paths(project_root, test_path)
        profile = get_unit_test_profile(profile_id)
    except ValueError as exc:
        return _blocked(profile_id, "CAMINHO_TESTE_INVALIDO", str(exc))

    command, blocker, coverage_path = _build_command(profile_id, root, test)
    if command is None:
        return _blocked(
            profile_id,
            "RUNTIME_DEPENDENCY_MISSING",
            blocker or "Executor indisponível.",
        )

    env = unit_profile_execution_environment(profile_id, command[0])
    try:
        process = subprocess.run(
            command,
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            env=env,
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

    output = "\n".join(
        part for part in (process.stdout, process.stderr) if part
    ).strip()
    counts = _parse_counts(profile_id, output, process.returncode)
    no_tests = process.returncode == 0 and counts["total"] == 0
    status = "sucesso" if process.returncode == 0 and not no_tests else "falha"
    errors = []
    if no_tests:
        errors.append(
            {
                "codigo": "NENHUM_TESTE_EXECUTADO",
                "mensagem": "O executor terminou sem descobrir testes.",
            }
        )
    elif process.returncode != 0:
        errors.append(
            {
                "codigo": "TESTES_FALHARAM",
                "mensagem": f"O executor terminou com código {process.returncode}.",
            }
        )
    return {
        "status": status,
        "tipo_teste": "unitario",
        "perfil": profile_id,
        "comando": command,
        "testes": counts,
        "cobertura": {
            "percentual": _coverage_percent(profile_id, output),
            "formato": profile.coverage_format,
            "arquivo": (
                str(coverage_path)
                if coverage_path and coverage_path.is_file()
                else None
            ),
        },
        "saida": output,
        "erros": errors,
    }
