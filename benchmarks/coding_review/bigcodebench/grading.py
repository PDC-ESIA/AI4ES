"""Avaliação oficial de uma solução do BigCodeBench num sandbox Docker isolado.

Filosofia (igual ao HumanEval): a nota vem dos testes OFICIAIS do dataset
(campo ``test``, uma classe ``unittest.TestCase``) — nunca dos testes que o coder
escreveu — e o grading NÃO é reimplementado: o código do coder e o teste oficial
são concatenados num único módulo (como no avaliador do BigCodeBench) e
executados com o `unittest` padrão.

Diferenças em relação ao `humaneval/grading.py`:

- usa `DockerSandbox` (imagem com as bibliotecas das tarefas, rede desligada por
  padrão), pois as tarefas importam bibliotecas de terceiros;
- além do veredito, classifica a CAUSA da falha (ver `FailureCategory`), separando
  falhas de biblioteca (ausente / import / uso incorreto da API) de falhas de
  lógica — a métrica que distingue o BigCodeBench do HumanEval.
"""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .categories import (
    API_MISUSE,
    IMPORT_ERROR,
    LOGIC,
    MISSING_DEPENDENCY,
    PASSED,
    RUNTIME_ERROR,
    SANDBOX_ERROR,
    SYNTAX,
    TIMEOUT,
)
from .dataset import BigCodeBenchProblem
from .sandbox_image import IMAGE_TAG

_GRADE_SCRIPT = "_ai4se_bigcodebench_grade.py"
_PASS_MARKER = "AI4SE_BIGCODEBENCH_PASS"
# Os testes do BigCodeBench podem ser pesados (pandas/tensorflow); 30s não basta.
DEFAULT_GRADE_TIMEOUT = 120
_SANDBOX_MEM = "4g"
_SANDBOX_CPU_QUOTA = 200000  # 2 cores
_SANDBOX_ENV = {"MPLBACKEND": "Agg", "TF_CPP_MIN_LOG_LEVEL": "3"}

_EXC_RE = re.compile(r"^([A-Za-z_][\w.]*(?:Error|Exception))\b", re.MULTILINE)
_API_HINTS = (
    "has no attribute",
    "unexpected keyword argument",
    "positional argument",
    "required positional",
    "is not callable",
    "not supported between",
)


@dataclass
class GradeResult:
    """Veredito de uma avaliação."""

    passed: bool
    category: str
    exit_code: int | None
    timed_out: bool
    stdout_tail: str
    stderr_tail: str
    reason: str = ""


def classify_failure(exit_code: int | None, timed_out: bool, stderr: str) -> str:
    """Classifica a causa de uma reprovação a partir do stderr do `unittest`.

    Precedência (uma falha de biblioteca derruba o módulo inteiro, então prevalece
    sobre as demais): dependência ausente > import > API > asserção > runtime.
    O diagnóstico de "uso incorreto da API" é HEURÍSTICO (ver README).
    """
    if timed_out:
        return TIMEOUT
    excecoes = set(_EXC_RE.findall(stderr)) | {
        e.rsplit(".", 1)[-1] for e in _EXC_RE.findall(stderr)
    }
    if "SyntaxError" in excecoes or "IndentationError" in excecoes:
        return SYNTAX
    if "ModuleNotFoundError" in excecoes:
        return MISSING_DEPENDENCY
    if "ImportError" in excecoes:
        return IMPORT_ERROR
    if {"AttributeError", "TypeError"} & excecoes and (
        "site-packages" in stderr or any(h in stderr for h in _API_HINTS)
    ):
        return API_MISUSE
    if "AssertionError" in excecoes:
        return LOGIC
    return RUNTIME_ERROR


def build_grade_program(problem: BigCodeBenchProblem, solution_source: str) -> str:
    """Monta o módulo avaliado: código do coder + teste oficial + runner `unittest`."""
    return (
        f"{solution_source.rstrip()}\n\n"
        "# ---- teste oficial do BigCodeBench ----\n"
        f"{problem.test.rstrip()}\n\n"
        "# ---- runner ----\n"
        "import sys as _sys\n"
        "import unittest as _unittest\n"
        "_suite = _unittest.defaultTestLoader.loadTestsFromTestCase(TestCases)\n"
        "_res = _unittest.TextTestRunner(stream=_sys.stderr, verbosity=1).run(_suite)\n"
        "if _res.wasSuccessful() and _res.testsRun > 0:\n"
        f'    print("{_PASS_MARKER}")\n'
        "    _sys.exit(0)\n"
        "_sys.exit(1)\n"
    )


def _run_once(
    programa: str,
    source_dir: Path,
    *,
    timeout: int,
    image: str,
    network_mode: str | None,
) -> GradeResult:
    from shared.execution.sandbox import (
        create_sandbox,  # requer o bootstrap (adk/ no sys.path)
    )

    sandbox = create_sandbox(
        "docker",
        base_image=image,
        mem_limit=_SANDBOX_MEM,
        cpu_quota=_SANDBOX_CPU_QUOTA,
        network_mode=network_mode,
        client_timeout=timeout + 120,  # a API só responde ao fim do exec
    )
    try:
        sandbox.setup(source_dir)
        (sandbox.root / _GRADE_SCRIPT).write_text(programa, encoding="utf-8")
        res = sandbox.exec(f"python {_GRADE_SCRIPT}", timeout=timeout, env=_SANDBOX_ENV)

        stdout_tail = (res.stdout or "")[-3000:]
        stderr_tail = (res.stderr or "")[-3000:]
        # O stderr completo é usado na classificação (a cauda pode cortar a causa).
        passed = (
            not res.timed_out
            and res.exit_code == 0
            and _PASS_MARKER in (res.stdout or "")
        )
        if passed:
            return GradeResult(
                True, PASSED, res.exit_code, False, stdout_tail, stderr_tail
            )

        categoria = classify_failure(res.exit_code, res.timed_out, res.stderr or "")
        reason = (
            f"Timeout de {timeout}s excedido na avaliação."
            if res.timed_out
            else f"Reprovado ({categoria}, exit={res.exit_code})."
        )
        return GradeResult(
            False,
            categoria,
            res.exit_code,
            res.timed_out,
            stdout_tail,
            stderr_tail,
            reason,
        )
    finally:
        sandbox.cleanup()


def _run(
    programa: str,
    source_dir: Path,
    *,
    timeout: int,
    image: str,
    network_mode: str | None,
    attempts: int = 2,
) -> GradeResult:
    """Executa `_run_once` tolerando falhas transitórias de infraestrutura (Docker).

    Uma exceção do Docker NÃO é falha do modelo: após `attempts` tentativas vira
    `sandbox_error` (registrado à parte), em vez de derrubar o benchmark inteiro.
    """
    erro = ""
    for _ in range(attempts):
        try:
            return _run_once(
                programa,
                source_dir,
                timeout=timeout,
                image=image,
                network_mode=network_mode,
            )
        except Exception as exc:  # noqa: BLE001 — qualquer erro de infra vira dado
            erro = f"{type(exc).__name__}: {exc}"
    return GradeResult(
        False, SANDBOX_ERROR, None, False, "", "", f"Falha do sandbox: {erro}"[:500]
    )


def grade_solution(
    problem: BigCodeBenchProblem,
    solution_dir: Path,
    solution_file: Path,
    *,
    timeout: int = DEFAULT_GRADE_TIMEOUT,
    image: str = IMAGE_TAG,
    network_mode: str | None = "none",
) -> GradeResult:
    """Executa o teste oficial contra a solução gerada, isolado em container.

    Args:
        problem: tarefa do BigCodeBench.
        solution_dir: raiz do código gerado (`coder/src/`).
        solution_file: arquivo que contém `task_func`.
        timeout: teto de wall-clock (segundos).
        image: imagem Docker com as bibliotecas das tarefas.
        network_mode: modo de rede do container (`"none"` = sem rede; `None` = padrão).
    """
    fonte = solution_file.read_text(encoding="utf-8", errors="replace")
    programa = build_grade_program(problem, fonte)
    return _run(
        programa, solution_dir, timeout=timeout, image=image, network_mode=network_mode
    )


def grade_canonical(
    problem: BigCodeBenchProblem,
    *,
    timeout: int = DEFAULT_GRADE_TIMEOUT,
    image: str = IMAGE_TAG,
    network_mode: str | None = "none",
) -> GradeResult:
    """Avalia a solução de REFERÊNCIA — valida que o ambiente roda a tarefa.

    Se a canônica falha por dependência, o problema é a imagem, não o modelo.
    """
    fonte = problem.prompt.rstrip("\n") + "\n" + problem.canonical_solution
    programa = build_grade_program(problem, fonte)
    with tempfile.TemporaryDirectory(prefix="ai4se-bcb-canon-") as vazio:
        return _run(
            programa,
            Path(vazio),
            timeout=timeout,
            image=image,
            network_mode=network_mode,
        )
