"""Leitura e escrita segura de testes gerados pelo pipeline de QA."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from shared.tools.pytest_runner import _normalizar_caminho_arquivo
from shared.workspace import get_agent_workspace


def _altera_sys_path(tree: ast.AST) -> bool:
    """Detecta mutações de sys.path, desnecessárias no workspace isolado do QA."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "sys"
                and target.attr == "path"
                for target in targets
            ):
                return True
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        collection = node.func.value
        if (
            node.func.attr in {"append", "extend", "insert", "remove"}
            and isinstance(collection, ast.Attribute)
            and isinstance(collection.value, ast.Name)
            and collection.value.id == "sys"
            and collection.attr == "path"
        ):
            return True
    return False


def _resolve_qa_test(caminho_arquivo: str) -> Path:
    path = _normalizar_caminho_arquivo(caminho_arquivo).resolve()
    tests_root = get_agent_workspace("receive_requirements").resolve()
    if not path.is_relative_to(tests_root):
        raise ValueError("O arquivo deve permanecer dentro de tests/inputs.")
    if path.suffix.casefold() != ".py" or not path.name.startswith("test_"):
        raise ValueError("Somente arquivos Python test_*.py podem ser alterados.")
    return path


def read_qa_test(caminho_arquivo: str) -> dict:
    """Lê um teste gerado dentro de ``workspace_output/tests/inputs``.

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
            "conteudo": path.read_text(encoding="utf-8"),
        }
    except (OSError, ValueError) as exc:
        return {"status": "erro", "erro": str(exc)}


def write_qa_test(caminho_arquivo: str, conteudo: str) -> dict:
    """Sobrescreve fisicamente um teste após validar sua sintaxe Python.

    Esta ferramenta nunca escreve em código de produção. O destino precisa
    ser um ``test_*.py`` dentro de ``workspace_output/tests/inputs``.

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
        tree = ast.parse(conteudo, filename=path.name)
        if _altera_sys_path(tree):
            raise ValueError(
                "O teste não pode alterar sys.path; use o conftest.py "
                "da suíte materializada pelo QA."
            )
        path.write_text(conteudo, encoding="utf-8")
        encoded = conteudo.encode("utf-8")
        return {
            "status": "aplicado",
            "path": str(path),
            "bytes_escritos": len(encoded),
            "sha256": hashlib.sha256(encoded).hexdigest(),
        }
    except (OSError, SyntaxError, ValueError) as exc:
        return {"status": "erro", "erro": str(exc)}
