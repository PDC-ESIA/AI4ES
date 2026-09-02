"""Leitura e escrita segura de testes gerados pelo pipeline de QA."""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

from shared.testing import (
    executar_teste_unitario,
    inspect_unit_test_project,
    resolve_unit_test_profile,
)
from shared.tools.pytest_runner import executar_pytest_tool
from shared.workspace import get_agent_workspace, get_workspace_root

_NODE_SUFFIXES = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
_IGNORED_DIRS = {
    ".git",
    ".gradle",
    ".venv",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
}


def _altera_sys_path(tree: ast.AST) -> bool:
    """Detecta mutações de sys.path, desnecessárias no workspace isolado do QA."""
    sys_aliases = {"sys"}
    path_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "sys":
                    sys_aliases.add(alias.asname or "sys")
        elif isinstance(node, ast.ImportFrom) and node.module == "sys":
            for alias in node.names:
                if alias.name == "path":
                    path_aliases.add(alias.asname or "path")

    def _is_sys_path(expr: ast.AST) -> bool:
        return (
            isinstance(expr, ast.Attribute)
            and isinstance(expr.value, ast.Name)
            and expr.value.id in sys_aliases
            and expr.attr == "path"
        )

    mutators = {"append", "extend", "insert", "remove", "pop", "clear", "sort", "reverse"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(
                _is_sys_path(t)
                or (isinstance(t, ast.Subscript) and _is_sys_path(t.value))
                for t in targets
            ):
                return True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in mutators
        ):
            obj = node.func.value
            if _is_sys_path(obj) or (isinstance(obj, ast.Name) and obj.id in path_aliases):
                return True
    return False


def _is_node_test_name(name: str) -> bool:
    return bool(
        re.search(
            r"(?:^test[_.-]|(?:\.|_|-)(?:test|spec)(?:\.|_|-))",
            name.casefold(),
        )
    )


def _is_managed_test(path: Path) -> bool:
    tests_inputs = get_agent_workspace("receive_requirements").resolve()
    coder = get_agent_workspace("cr_coder").resolve()
    e2e = get_agent_workspace("e2e_test_generator").resolve()
    resolved = path.resolve()

    if resolved.is_relative_to(tests_inputs):
        return resolved.suffix.casefold() == ".py" and (
            resolved.name.startswith("test_")
            or resolved.name.casefold().endswith("_test.py")
        )
    if resolved.is_relative_to(e2e):
        return (
            resolved.suffix.casefold() in _NODE_SUFFIXES
            and _is_node_test_name(resolved.name)
        )
    if not resolved.is_relative_to(coder):
        return False

    relative = resolved.relative_to(coder)
    parts = tuple(part.casefold() for part in relative.parts)
    suffix = resolved.suffix.casefold()
    in_test_directory = any(
        part in {"__tests__", "spec", "specs", "test", "tests"}
        for part in parts[:-1]
    )
    if suffix == ".py":
        return in_test_directory and (
            resolved.name.startswith("test_")
            or resolved.name.casefold().endswith("_test.py")
        )
    if suffix in _NODE_SUFFIXES:
        return in_test_directory and _is_node_test_name(resolved.name)
    if suffix == ".java":
        return len(parts) >= 3 and parts[:2] == ("src", "test")
    if suffix == ".go":
        name = resolved.name.casefold()
        return name.endswith("_test.go") or name.endswith("_test.generated.go")
    return False


def _search_by_name(name: str) -> list[Path]:
    roots = {
        get_agent_workspace("receive_requirements").resolve(),
        get_agent_workspace("e2e_test_generator").resolve(),
        get_agent_workspace("cr_coder").resolve(),
    }
    matches: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for candidate in root.rglob(name):
            if not candidate.is_file():
                continue
            relative_parts = {
                part.casefold() for part in candidate.relative_to(root).parts[:-1]
            }
            if relative_parts & _IGNORED_DIRS:
                continue
            if _is_managed_test(candidate):
                matches.append(candidate.resolve())
    return sorted(set(matches))


def _resolve_qa_test(caminho_arquivo: str) -> Path:
    if not isinstance(caminho_arquivo, str) or not caminho_arquivo.strip():
        raise ValueError("O caminho do teste deve ser informado.")

    workspace = get_workspace_root().resolve()
    tests_inputs = get_agent_workspace("receive_requirements").resolve()
    coder = get_agent_workspace("cr_coder").resolve()
    e2e = get_agent_workspace("e2e_test_generator").resolve()
    raw_value = caminho_arquivo.strip().replace("\\", "/")
    if raw_value.startswith("workspace_output/"):
        raw_value = raw_value.removeprefix("workspace_output/")
    received = Path(raw_value).expanduser()

    if received.is_absolute():
        candidates = [received.resolve()]
    else:
        candidates = [
            (workspace / received).resolve(),
            (coder / received).resolve(),
            (tests_inputs / received).resolve(),
            (e2e / received).resolve(),
        ]
    existing = [
        candidate
        for candidate in dict.fromkeys(candidates)
        if candidate.is_file() and _is_managed_test(candidate)
    ]
    if len(existing) == 1:
        return existing[0]
    if len(existing) > 1:
        raise ValueError(
            "O caminho do teste é ambíguo: "
            + ", ".join(str(path) for path in existing)
        )

    if len(received.parts) == 1:
        matches = _search_by_name(received.name)
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(
                "O nome do teste é ambíguo: "
                + ", ".join(str(path) for path in matches)
            )

    fallback = candidates[0]
    if received.suffix.casefold() == ".py":
        fallback = (tests_inputs / received).resolve()
    elif received.suffix.casefold() in _NODE_SUFFIXES or (
        received.suffix.casefold() in {".java", ".go"}
    ):
        fallback = (coder / received).resolve()
    if not _is_managed_test(fallback):
        raise ValueError(
            "Somente arquivos de teste gerenciados de Python, Node/TypeScript, "
            "Java ou Go podem ser alterados."
        )
    return fallback


def _language(path: Path) -> str:
    suffix = path.suffix.casefold()
    if suffix == ".py":
        return "python"
    if suffix in _NODE_SUFFIXES:
        return "javascript-typescript"
    if suffix == ".java":
        return "java"
    if suffix == ".go":
        return "go"
    return "desconhecida"


def _validate_corrected_content(path: Path, content: str) -> None:
    suffix = path.suffix.casefold()
    if suffix == ".py":
        tree = ast.parse(content, filename=path.name)
        if _altera_sys_path(tree):
            raise ValueError(
                "O teste não pode alterar sys.path; use o conftest.py "
                "da suíte materializada pelo QA."
            )
        return
    if suffix in _NODE_SUFFIXES and not re.search(
        r"\b(?:describe|it|test)\s*\(", content
    ):
        raise ValueError("O conteúdo corrigido não contém testes Node executáveis.")
    if suffix == ".java" and not re.search(
        r"@(?:Test|ParameterizedTest|RepeatedTest|TestFactory)\b", content
    ):
        raise ValueError("O conteúdo corrigido não contém testes JUnit.")
    if suffix == ".go" and not re.search(r"\bfunc\s+Test\w+\s*\(", content):
        raise ValueError("O conteúdo corrigido não contém testes Go.")


def read_qa_test(caminho_arquivo: str) -> dict:
    """Lê um teste existente gerenciado pelo QA em qualquer stack registrada.

    Args:
        caminho_arquivo: Path absoluto, relativo ao workspace ou relativo a
            ``tests/inputs``.

    Returns:
        Objeto com status, path normalizado e conteúdo atual.
    """
    try:
        path = _resolve_qa_test(caminho_arquivo)
        if not path.is_file():
            return {
                "status": "erro",
                "path": str(path),
                "erro": "Arquivo de teste não encontrado.",
            }
        return {
            "status": "ok",
            "path": str(path),
            "linguagem": _language(path),
            "conteudo": path.read_text(encoding="utf-8"),
        }
    except (OSError, ValueError) as exc:
        return {"status": "erro", "erro": str(exc)}


def write_qa_test(caminho_arquivo: str, conteudo: str) -> dict:
    """Sobrescreve um teste existente após validar stack, conteúdo e destino.

    Esta ferramenta nunca escreve em código de produção. O destino precisa ser
    reconhecido como teste gerado de Python, Node/TypeScript, Java ou Go.

    Args:
        caminho_arquivo: Path do teste a corrigir.
        conteudo: Conteúdo Python completo já corrigido.

    Returns:
        Objeto com status, path, bytes escritos e SHA-256 do novo conteúdo.
    """
    try:
        path = _resolve_qa_test(caminho_arquivo)
        if not isinstance(conteudo, str) or not conteudo.strip():
            raise ValueError("O conteúdo corrigido não pode ser vazio.")
        if not path.is_file():
            raise ValueError(
                "O code_fix só pode corrigir um teste existente; "
                "o arquivo informado não foi gerado pelo QA."
            )
        _validate_corrected_content(path, conteudo)
        path.write_text(conteudo, encoding="utf-8")
        encoded = conteudo.encode("utf-8")
        return {
            "status": "aplicado",
            "path": str(path),
            "linguagem": _language(path),
            "bytes_escritos": len(encoded),
            "sha256": hashlib.sha256(encoded).hexdigest(),
        }
    except (OSError, SyntaxError, ValueError) as exc:
        return {"status": "erro", "erro": str(exc)}


def executar_teste_unitario_corrigido(
    caminho_arquivo: str, perfil: str = ""
) -> dict:
    """Reexecuta um teste corrigido com o executor fixo de seu perfil."""
    try:
        path = _resolve_qa_test(caminho_arquivo)
        if not path.is_file():
            raise ValueError("O arquivo de teste corrigido não existe.")
        if path.suffix.casefold() == ".py":
            selected = resolve_unit_test_profile(perfil) if perfil else None
            if selected is not None and selected.profile_id != "python-pytest":
                raise ValueError(
                    f"O perfil '{selected.profile_id}' não corresponde ao teste Python."
                )
            return executar_pytest_tool(str(path))

        project_root = get_agent_workspace("cr_coder").resolve()
        inspection = inspect_unit_test_project(
            project_root,
            declared_stack=perfil,
        )
        if inspection.get("status") != "suportado":
            blockers = inspection.get("bloqueios") or []
            message = (
                blockers[0].get("mensagem")
                if blockers
                else "Perfil unitário não identificado."
            )
            raise ValueError(message)
        profile_id = inspection["perfil"]["profile_id"]
        result = executar_teste_unitario(profile_id, project_root, path)
        result["arquivo"] = str(path)
        return result
    except (OSError, ValueError) as exc:
        return {
            "status": "erro",
            "arquivo": caminho_arquivo,
            "erros": [{"codigo": "REEXECUCAO_INVALIDA", "mensagem": str(exc)}],
        }
