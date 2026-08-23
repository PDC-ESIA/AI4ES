"""Validação determinística das soluções geradas pelo coder para o TACO.

Dois níveis de verificação:
1. Sintaxe — ast.parse detecta arquivos sintaticamente incompletos.
   Erros nos últimos 15% das linhas são classificados como
   POSSÍVEL_TRUNCAMENTO (limite de max_output_tokens), não ERRO_SINTÁTICO.

2. Exemplos — se challenge.examples estiver presente, executa o script
   com cada entrada via subprocess e compara o stdout ao esperado.

Achado registrado: o campo 'prompt' dos JSONs TACO referencia
'challenge.examples' para validação, mas os 60 JSONs de produção não
têm este campo. Isso é reportado ao time TACO, não tratado em silêncio.
"""

from __future__ import annotations

import ast
import logging
import subprocess
from pathlib import Path

from .matching import MatchResult

logger = logging.getLogger(__name__)

_TRUNCAMENTO_THRESHOLD = 0.85
_EXEC_TIMEOUT_S = 10


def _classificar_arquivo(path: Path) -> tuple[bool, str]:
    """Retorna (sintaticamente_completo, classificação)."""
    try:
        texto = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False, "ERRO_LEITURA"
    try:
        ast.parse(texto)
        return True, "OK"
    except SyntaxError as e:
        linhas = texto.splitlines()
        if e.lineno and linhas and e.lineno >= len(linhas) * _TRUNCAMENTO_THRESHOLD:
            return False, "POSSÍVEL_TRUNCAMENTO"
        return False, "ERRO_SINTÁTICO"


def _executar_com_stdin(script_path: Path, stdin_input: str) -> tuple[str, int]:
    """Executa o script com a entrada dada e retorna (stdout, exit_code)."""
    try:
        result = subprocess.run(
            ["python", str(script_path)],
            input=stdin_input,
            capture_output=True,
            text=True,
            timeout=_EXEC_TIMEOUT_S,
        )
        return result.stdout.rstrip("\n"), result.returncode
    except subprocess.TimeoutExpired:
        return "", -1
    except Exception as exc:
        logger.warning("[TACO-VALIDATOR] Erro ao executar %s: %s", script_path.name, exc)
        return "", -2


def validate(
    match: dict[str, MatchResult],
    examples: list[dict] | None,
) -> dict[str, dict]:
    """Valida cada arquivo matched e retorna resultados por label.

    Args:
        match: Saída de match_files — dict[label, MatchResult].
        examples: Lista de dicts {input, expected_output} ou None.
            Ausência é registrada em log como achado para o time TACO.

    Returns:
        Dict[label, resultado] com campos:
        - status: "OK" | "ERRO_SINTÁTICO" | "POSSÍVEL_TRUNCAMENTO" |
                  "ERRO_LEITURA" | causa do MatchResult quando path=None
        - syntax_ok: bool
        - examples_run: lista de resultados de execução (vazia se sem examples)
    """
    if examples is None:
        logger.info(
            "[TACO-VALIDATOR] challenge.examples ausente nos dados de entrada. "
            "Achado a reportar ao time TACO: o campo 'prompt' dos JSONs referencia "
            "'challenge.examples' para validação, mas o schema não inclui o campo."
        )

    results: dict[str, dict] = {}

    for label, mr in match.items():
        if mr.path is None:
            results[label] = {
                "status": mr.cause or "SEM_ARQUIVO",
                "syntax_ok": False,
                "examples_run": [],
            }
            continue

        is_ok, classification = _classificar_arquivo(mr.path)

        if not is_ok:
            results[label] = {
                "status": classification,
                "syntax_ok": False,
                "examples_run": [],
            }
            continue

        examples_run = []
        if examples:
            for i, ex in enumerate(examples):
                stdin_val = ex.get("input", "")
                expected = str(ex.get("expected_output", "")).rstrip("\n")
                actual, exit_code = _executar_com_stdin(mr.path, stdin_val)
                passed = exit_code == 0 and actual == expected
                examples_run.append({
                    "example_index": i,
                    "input": stdin_val,
                    "expected": expected,
                    "actual": actual if exit_code >= 0 else f"[TIMEOUT/ERRO: {exit_code}]",
                    "passed": passed,
                })

        results[label] = {
            "status": "OK",
            "syntax_ok": True,
            "examples_run": examples_run,
        }

    return results
