"""Adapter da stack Node.js — testes via `npm test` DENTRO do container implantado.

PoC de que o desenho de adapter da C1 (`StackAdapter`/`FileMarker`/`registry`)
generaliza para uma segunda stack. Diferença central em relação ao
`PythonAdapter`: aqui NÃO se assume o test runner. O adapter delega ao script
`"test"` do `package.json` (Jest/Mocha/Vitest/... — o próprio projeto resolve,
inclusive TypeScript via ts-jest) e classifica o resultado pelo EXIT CODE do
`npm test` — convenção universal do ecossistema Node, independente do runner.
Não há parsing de contagem passou/falhou (exigiria assumir um runner); a saída
bruta vai como evidência.

Não instala nada em runtime: `npm` ausente no container é falha honesta e
reportada, não uma tentativa de instalação (ao contrário do `PythonAdapter`, que
tenta `pip install pytest`). A instalação de dependências (`npm install`) é
responsabilidade do build da imagem (Dockerfile do app), não deste adapter.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .base import ExecNoContainer, FileMarker, ResultadoTestes, StackAdapter

# Teto para `npm test` no container (segundos). Constante PRÓPRIA do módulo — não
# compartilha com o _TESTS_TIMEOUT do python_adapter; suítes Node (Jest/ts-jest)
# costumam ter um cold start mais lento.
_TESTS_TIMEOUT = 120

# Placeholder que `npm init` grava quando não há teste configurado
# (`"test": "echo \"Error: no test specified\" && exit 1"`). Sai com código 1,
# igual a uma suíte que falhou — por isso é tratado à parte, para não confundir
# "nenhum teste escrito" com "os testes falharam".
_PLACEHOLDER_SEM_TESTE = "no test specified"

def _ler_package_json(coder_dir: Path) -> Optional[dict]:
    try:
        dado = json.loads((coder_dir / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return dado if isinstance(dado, dict) else None

def _usa_express(pkg: dict) -> bool:
    """Express declarado em dependencies/devDependencies (checagem de chave only).

    Puramente informativo — não instala nem executa nada para descobrir isso, e
    NUNCA influencia o status/error_code do resultado (ver spec Fatia D §3.4).
    """
    for secao in ("dependencies", "devDependencies"):
        deps = pkg.get(secao)
        if isinstance(deps, dict) and "express" in deps:
            return True
    return False


class NodeAdapter(StackAdapter):
    """Stack Node.js: testes via `npm test` no container implantado."""

    nome = "node"
    tech_stack_keywords = ("node", "node.js", "nodejs", "javascript", "typescript")
    file_markers = (FileMarker("package.json"),)

    def executar_testes(
        self, exec_no_container: ExecNoContainer, container: Any, coder_dir: Path
    ) -> ResultadoTestes:
        pkg = _ler_package_json(coder_dir)
        if pkg is None:
            return ResultadoTestes(
                status="pulado",
                summary="package.json ausente ou ilegível no workspace do coder.",
                error_code=None,
                evidence={"package_json": None},
            )

        # Evidência informativa (não gateia nada) — coletada cedo p/ ir em todos
        # os caminhos abaixo.
        express = _usa_express(pkg)
        scripts = pkg.get("scripts")
        script_test = scripts.get("test") if isinstance(scripts, dict) else None

        if not script_test:
            return ResultadoTestes(
                status="pulado",
                summary="Nenhum script `test` configurado no package.json.",
                error_code=None,
                evidence={"scripts_test": None, "usa_express": express},
            )

        if _PLACEHOLDER_SEM_TESTE in script_test:
            return ResultadoTestes(
                status="pulado",
                summary="Nenhum teste configurado (placeholder padrão do `npm init`).",
                error_code=None,
                evidence={"scripts_test": script_test, "usa_express": express},
            )

        try:
            code_npm, _, _ = exec_no_container(container, "npm --version")
            if code_npm != 0:
                return ResultadoTestes(
                    status="pulado",
                    summary="npm indisponível no container. Testes não executados.",
                    error_code="NPM_INDISPONIVEL",
                    evidence={"scripts_test": script_test, "usa_express": express},
                )

            exit_code, stdout, stderr = exec_no_container(
                container, f"timeout {_TESTS_TIMEOUT} npm test"
            )
        except Exception as e:
            return ResultadoTestes(
                status="erro",
                summary=f"Falha ao executar `npm test` no container: {e}",
                error_code="EXEC_FALHOU",
                evidence={"scripts_test": script_test, "usa_express": express},
            )

        # Classificação SÓ pelo exit code (sem parsing de contagem — ver docstring):
        #   0 = passou | 124 = timeout (coreutils) | qualquer outro != 0 = falhou.
        if exit_code == 0:
            status, error_code = "sucesso", None
        elif exit_code == 124:
            status, error_code = "falha", "TESTES_TIMEOUT"
        else:
            status, error_code = "falha", "TESTES_FALHARAM"

        tail = (stdout or "")[-3000:]
        if stderr:
            tail += f"\n--- stderr ---\n{stderr[-1000:]}"

        return ResultadoTestes(
            status=status,
            summary=(
                f"`npm test` executado no container (exit={exit_code}); "
                f"classificação pelo exit code (runner não parseado)."
            ),
            error_code=error_code,
            evidence={
                "scripts_test": script_test,
                "exit_code": exit_code,
                "usa_express": express,
                "saida_tail": tail,
            },
        )
