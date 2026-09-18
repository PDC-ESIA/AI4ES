"""Executores determinísticos das stacks não Python publicadas pelo Coder."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

from shared.workspace import get_agent_workspace

from . import execution_adapters as runtime_adapters
from .profile_orchestration import validate_test_path
from .result_normalization import parse_test_counts, test_counts
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


def unit_profile_execution_environment(
    profile_id: str, executable: str
) -> dict[str, str]:
    """Monta o ambiente comum sem instalar ou alterar runtimes."""
    del profile_id, executable
    environment = os.environ.copy()
    environment["CI"] = "1"
    return environment


def _go_command(
    root: Path, test: Path
) -> tuple[list[str] | None, str | None, Path | None]:
    coverage_dir = get_agent_workspace("unit_test_generator") / "coverage"
    coverage_dir.mkdir(parents=True, exist_ok=True)
    coverage_path = coverage_dir / f"{test.stem}.out"
    command, blocker = runtime_adapters.build_go_test_command(
        root, test, coverage_path=coverage_path
    )
    return command, blocker, coverage_path


def _strip_ansi(output: str) -> str:
    """Remove sequências de estilo emitidas pelos runners em terminais CI."""
    return _ANSI_ESCAPE_RE.sub("", output)


def _parse_counts(profile_id: str, output: str, returncode: int) -> dict[str, int]:
    output = _strip_ansi(output)
    if re.search(
        r"no tests? (?:were found|is available|matches)", output, re.IGNORECASE
    ):
        return test_counts(0)
    framework = {
        "go-testing": "go-testing",
        "java-junit": "junit",
        "node-vitest": "vitest",
        "node-jest": "jest",
        "node-node-test": "node:test",
        "node-mocha": "mocha",
    }.get(profile_id, profile_id)
    counts = parse_test_counts(framework, output)
    return (
        counts
        if counts["total"]
        else test_counts(0 if returncode else 1, 1 if returncode else 0)
    )


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
        framework = profile_id.removeprefix("node-").replace("node-test", "node:test")
        command, blocker = runtime_adapters.build_node_test_command(
            root, test, framework, coverage=profile_id == "node-jest"
        )
    elif profile_id == "java-junit":
        command, _framework, blocker = runtime_adapters.build_java_test_command(
            root, test
        )
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
        root, test = validate_test_path(project_root, test_path)
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
