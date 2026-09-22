"""Avaliação canônica de uma solução do HumanEval no `DirectSandbox`.

Filosofia: a nota do benchmark vem do teste OFICIAL do HumanEval — nunca dos
testes que o coder porventura escreveu. Reutilizamos o `DirectSandbox` do
projeto apenas como camada de isolamento/execução (subprocess efêmero, env
limpo, limites de recurso, timeout de wall-clock).

Fluxo de um grading:
1. copia o código gerado (`coder/src/`) para o sandbox efêmero;
2. injeta um programa de avaliação que importa a função-alvo de `solution` e
   executa `check(entry_point)` (o `check` vem do campo `test` do dataset);
3. o veredito é binário: exit-code 0 + marcador de sucesso ⇒ PASSOU.
"""

from __future__ import annotations

import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

from shared.execution.sandbox import DirectSandbox

from .contract import SOLUTION_FILENAME
from .dataset import HumanEvalProblem

# Nome do programa de avaliação injetado no sandbox (evita colisão com o código).
_GRADE_SCRIPT = "_ai4se_humaneval_grade.py"
# Marcador impresso em caso de sucesso — confirma que `check` passou de fato.
_PASS_MARKER = "AI4SE_HUMANEVAL_PASS"
# Timeout (segundos) por avaliação — teto de wall-clock do sandbox.
DEFAULT_GRADE_TIMEOUT = 30


@dataclass
class GradeResult:
    """Veredito de uma avaliação canônica."""

    passed: bool
    exit_code: int | None
    timed_out: bool
    stdout_tail: str
    stderr_tail: str
    reason: str = ""


def build_grade_program(problem: HumanEvalProblem, module_name: str) -> str:
    """Monta o programa Python que executa o teste canônico do HumanEval.

    Args:
        problem: o problema (fornece `entry_point` e `test`).
        module_name: nome do módulo a importar (sem `.py`) que define a função.
    """
    return (
        "import sys\n"
        'sys.path.insert(0, ".")\n'
        f"from {module_name} import {problem.entry_point} as _candidate\n"
        "\n"
        f"{problem.test}\n"
        "\n"
        f"check(_candidate)\n"
        f'print("{_PASS_MARKER}")\n'
    )


def _module_name_for(solution_file: Path, solution_dir: Path) -> str:
    """Deriva o nome de import a partir do arquivo-solução localizado.

    Para o caso canônico (`solution.py` na raiz) devolve ``"solution"``. Para
    layouts aninhados, usa o *stem* do arquivo e confia que ele esteja em um
    diretório presente no `sys.path` (a raiz é inserida pelo programa de grading;
    o subdiretório é coberto pelo ajuste adicional abaixo).
    """
    return solution_file.stem


def grade_solution(
    problem: HumanEvalProblem,
    solution_dir: Path,
    solution_file: Path,
    *,
    timeout: int = DEFAULT_GRADE_TIMEOUT,
    python_executable: str | None = None,
) -> GradeResult:
    """Executa o teste canônico contra a solução gerada, isolado no sandbox.

    Args:
        problem: problema do HumanEval.
        solution_dir: raiz do código gerado (`coder/src/`).
        solution_file: arquivo que expõe a função-alvo.
        timeout: teto de wall-clock (segundos).
        python_executable: interpretador a usar (default: o atual, `sys.executable`).
    """
    python = python_executable or sys.executable
    module_name = _module_name_for(solution_file, solution_dir)
    programa = build_grade_program(problem, module_name)

    sandbox = DirectSandbox()
    try:
        sandbox.setup(solution_dir)

        # Garante que o diretório do arquivo-solução (se aninhado) seja
        # importável, além da raiz já coberta pelo programa de grading.
        rel_parent = solution_file.parent.relative_to(solution_dir)
        if rel_parent != Path("."):
            programa = programa.replace(
                'sys.path.insert(0, ".")\n',
                'sys.path.insert(0, ".")\n'
                f"sys.path.insert(0, {shlex.quote(str(rel_parent))})\n",
            )

        (sandbox.root / _GRADE_SCRIPT).write_text(programa, encoding="utf-8")

        comando = f"{shlex.quote(python)} {shlex.quote(_GRADE_SCRIPT)}"
        res = sandbox.exec(comando, timeout=timeout)

        stdout_tail = (res.stdout or "")[-3000:]
        stderr_tail = (res.stderr or "")[-3000:]

        if res.timed_out:
            return GradeResult(
                passed=False,
                exit_code=res.exit_code,
                timed_out=True,
                stdout_tail=stdout_tail,
                stderr_tail=stderr_tail,
                reason=f"Timeout de {timeout}s excedido na avaliação.",
            )

        passed = res.exit_code == 0 and _PASS_MARKER in (res.stdout or "")
        reason = "" if passed else _diagnosticar(res.exit_code, stderr_tail)
        return GradeResult(
            passed=passed,
            exit_code=res.exit_code,
            timed_out=False,
            stdout_tail=stdout_tail,
            stderr_tail=stderr_tail,
            reason=reason,
        )
    finally:
        sandbox.cleanup()


def _diagnosticar(exit_code: int | None, stderr_tail: str) -> str:
    """Resumo curto e legível do motivo da reprovação."""
    if "AssertionError" in stderr_tail:
        return "Teste canônico falhou (AssertionError)."
    if "ImportError" in stderr_tail or "ModuleNotFoundError" in stderr_tail:
        return "Falha ao importar a função-alvo de `solution`."
    if "SyntaxError" in stderr_tail:
        return "Código gerado contém erro de sintaxe."
    return f"Avaliação falhou (exit={exit_code})."
