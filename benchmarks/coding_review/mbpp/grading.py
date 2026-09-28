"""Avaliação de uma solução do MBPP no `DirectSandbox`.

Filosofia (idêntica ao HumanEval): a nota do benchmark vem dos testes
OFICIAIS do dataset (`test_imports` + `test_list`) — nunca dos testes que o
coder porventura escreveu. Reutilizamos o `DirectSandbox` do projeto apenas
como camada de isolamento/execução (subprocess efêmero, env limpo, limites de
recurso, timeout de wall-clock).

Diferença estrutural em relação ao HumanEval: o MBPP não usa uma função
`check(candidate)` indireta — `test_list` é uma lista de `assert`s que chama
a função-alvo PELO NOME (ex.: ``assert similar_elements(...) == (...)``).
Por isso o programa de avaliação expõe a função com o nome original (sem
alias) e executa os `assert`s tal como vêm do dataset, precedidos pelos
`test_imports` declarados.

Fluxo de um grading:
1. copia o código gerado (`coder/src/`) para o sandbox efêmero;
2. injeta um programa de avaliação que carrega o arquivo-solução, expõe a
   função-alvo pelo nome original e executa TODOS os `assert`s de `test_list`
   (incluído o primeiro, já visto pelo coder como exemplo — ver `contract.py`);
3. o veredito é binário: exit-code 0 + marcador de sucesso ⇒ PASSOU.
"""

from __future__ import annotations

import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

from shared.execution.sandbox import DirectSandbox

from .dataset import MbppProblem

# Nome do programa de avaliação injetado no sandbox (evita colisão com o código).
_GRADE_SCRIPT = "_ai4se_mbpp_grade.py"
# Marcador impresso em caso de sucesso — confirma que todos os asserts passaram.
_PASS_MARKER = "AI4SE_MBPP_PASS"
# Timeout (segundos) por avaliação — teto de wall-clock do sandbox.
DEFAULT_GRADE_TIMEOUT = 30


@dataclass
class GradeResult:
    """Veredito de uma avaliação."""

    passed: bool
    exit_code: int | None
    timed_out: bool
    stdout_tail: str
    stderr_tail: str
    reason: str = ""


def build_grade_program(problem: MbppProblem, solution_rel: Path) -> str:
    """Monta o programa Python que executa os `assert`s oficiais do MBPP.

    O módulo-solução é carregado pelo CAMINHO (`importlib`), não por
    `from <stem> import ...`: assim layouts aninhados e nomes de arquivo que
    não são identificadores Python válidos (ex.: `my-sol.py`) continuam
    avaliáveis. O diretório do arquivo entra no `sys.path` para que imports
    entre arquivos irmãos gerados pelo coder funcionem.

    Args:
        problem: o problema (fornece `entry_point`, `test_imports` e `test_list`).
        solution_rel: caminho do arquivo-solução relativo à raiz do sandbox.
    """
    linhas = [
        "import importlib.util as _ilu",
        "import sys",
        'sys.path.insert(0, ".")',
        f"sys.path.insert(0, {str(solution_rel.parent)!r})",
        f'_spec = _ilu.spec_from_file_location("solution", {str(solution_rel)!r})',
        "_mod = _ilu.module_from_spec(_spec)",
        'sys.modules["solution"] = _mod',
        "_spec.loader.exec_module(_mod)",
        f"{problem.entry_point} = _mod.{problem.entry_point}",
        *problem.test_imports,
        "",
        *problem.test_list,
        f'print("{_PASS_MARKER}")',
    ]
    return "\n".join(linhas) + "\n"


def grade_solution(
    problem: MbppProblem,
    solution_dir: Path,
    solution_file: Path,
    *,
    timeout: int = DEFAULT_GRADE_TIMEOUT,
    python_executable: str | None = None,
) -> GradeResult:
    """Executa os `assert`s oficiais contra a solução gerada, isolado no sandbox.

    Args:
        problem: problema do MBPP.
        solution_dir: raiz do código gerado (`coder/src/`).
        solution_file: arquivo que expõe a função-alvo.
        timeout: teto de wall-clock (segundos).
        python_executable: interpretador a usar (default: o atual, `sys.executable`).
    """
    python = python_executable or sys.executable
    programa = build_grade_program(problem, solution_file.relative_to(solution_dir))

    sandbox = DirectSandbox()
    try:
        sandbox.setup(solution_dir)
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
        return "Assert oficial do MBPP falhou (AssertionError)."
    if "ImportError" in stderr_tail or "ModuleNotFoundError" in stderr_tail:
        return "Falha ao importar a função-alvo de `solution`."
    if "SyntaxError" in stderr_tail:
        return "Código gerado contém erro de sintaxe."
    ultima = next(
        (ln.strip() for ln in reversed(stderr_tail.splitlines()) if ln.strip()), ""
    )
    if ultima:
        return f"Avaliação falhou (exit={exit_code}): {ultima[:200]}"
    return f"Avaliação falhou (exit={exit_code})."
