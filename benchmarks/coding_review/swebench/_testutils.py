"""Utilitários dos testes: conferir o benchmark contra o código de produção.

Importar `src.agents.workflow_coding_review.*` num teste dispararia o
`__init__` do workflow, que monta o pipeline inteiro e cria diretórios de
workspace como efeito colateral. Por isso os testes leem constantes da produção
por AST e carregam módulos autocontidos pelo caminho do arquivo.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ADK_DIR = Path(__file__).resolve().parents[3] / "adk"


def module_constant(caminho: Path, nome: str) -> Any:
    """Valor literal de uma atribuição de módulo/classe (`NOME = <literal>`)."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if isinstance(no, ast.Assign) and any(
            isinstance(alvo, ast.Name) and alvo.id == nome for alvo in no.targets
        ):
            return ast.literal_eval(no.value)
        if (
            isinstance(no, ast.AnnAssign)
            and isinstance(no.target, ast.Name)
            and no.target.id == nome
            and no.value is not None
        ):
            return ast.literal_eval(no.value)
    raise LookupError(f"{nome} não encontrado em {caminho}")


def load_isolated_module(caminho: Path, nome: str) -> ModuleType:
    """Carrega um módulo pelo caminho, sem passar pelos `__init__` do pacote."""
    if nome in sys.modules:
        return sys.modules[nome]
    spec = importlib.util.spec_from_file_location(nome, caminho)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo
