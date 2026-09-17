"""Testes unitários para validator.py — validação sintática e de exemplos."""
from pathlib import Path

import pytest

from src.agents.workflow_taco.matching import MatchResult
from src.agents.workflow_taco.validator import _classificar_arquivo, validate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _match(path: Path | None, cause: str | None = None) -> dict[str, MatchResult]:
    return {
        "leitura-direta": MatchResult(
            path=path,
            strategy="exact" if path else "not_found",
            cause=cause,
        )
    }


def _script(tmp_path: Path, code: str) -> Path:
    f = tmp_path / "leitura_direta.py"
    f.write_text(code, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# _classificar_arquivo
# ---------------------------------------------------------------------------

def test_classificar_ok(tmp_path):
    f = _script(tmp_path, "a, b = map(int, input().split())\nprint(a + b)\n")
    ok, status = _classificar_arquivo(f)
    assert ok is True
    assert status == "OK"


def test_classificar_possivel_truncamento(tmp_path):
    linhas = ["x = 1\n"] * 20 + ["def incompleto(\n"]
    f = _script(tmp_path, "".join(linhas))
    ok, status = _classificar_arquivo(f)
    assert ok is False
    assert status == "POSSÍVEL_TRUNCAMENTO"


def test_classificar_erro_sintatico_no_inicio(tmp_path):
    f = _script(tmp_path, "def foo(\n" + "x = 1\n" * 20)
    ok, status = _classificar_arquivo(f)
    assert ok is False
    assert status == "ERRO_SINTÁTICO"


# ---------------------------------------------------------------------------
# validate — path=None
# ---------------------------------------------------------------------------

def test_validate_path_none_propaga_cause():
    result = validate(_match(None, cause="POSSÍVEL_TRUNCAMENTO"), examples=None)
    r = result["leitura-direta"]
    assert r["status"] == "POSSÍVEL_TRUNCAMENTO"
    assert r["syntax_ok"] is False
    assert r["examples_run"] == []


def test_validate_path_none_sem_cause():
    result = validate(_match(None, cause=None), examples=None)
    r = result["leitura-direta"]
    assert r["status"] == "SEM_ARQUIVO"
    assert r["syntax_ok"] is False


# ---------------------------------------------------------------------------
# validate — sem exemplos
# ---------------------------------------------------------------------------

def test_validate_sem_examples_retorna_ok(tmp_path):
    f = _script(tmp_path, "a, b = map(int, input().split())\nprint(a + b)\n")
    result = validate(_match(f), examples=None)
    r = result["leitura-direta"]
    assert r["status"] == "OK"
    assert r["syntax_ok"] is True
    assert r["examples_run"] == []


def test_validate_erro_sintatico_nao_executa_examples(tmp_path):
    f = _script(tmp_path, "def incompleto(\n")
    result = validate(_match(f), examples=[{"input": "1 2", "expected_output": "3"}])
    r = result["leitura-direta"]
    assert r["syntax_ok"] is False
    assert r["examples_run"] == []


# ---------------------------------------------------------------------------
# validate — com exemplos
# ---------------------------------------------------------------------------

def test_validate_exemplo_passa(tmp_path):
    f = _script(tmp_path, "a, b = map(int, input().split())\nprint(a + b)\n")
    result = validate(_match(f), examples=[{"input": "3 5", "expected_output": "8"}])
    ex = result["leitura-direta"]["examples_run"][0]
    assert ex["passed"] is True
    assert ex["actual"] == "8"
    assert ex["expected"] == "8"


def test_validate_exemplo_falha_bug_stdin(tmp_path):
    # Bug: lê em duas linhas em vez de uma — falha com input "3 5" em linha única
    f = _script(tmp_path, "a = int(input())\nb = int(input())\nprint(a + b)\n")
    result = validate(_match(f), examples=[{"input": "3 5", "expected_output": "8"}])
    ex = result["leitura-direta"]["examples_run"][0]
    assert ex["passed"] is False


def test_validate_input_como_inteiro_nao_quebra(tmp_path):
    """Garante o str() cast: campo 'input' como número não causa TypeError."""
    f = _script(tmp_path, "n = int(input())\nprint(n * 2)\n")
    result = validate(_match(f), examples=[{"input": 3, "expected_output": "6"}])
    ex = result["leitura-direta"]["examples_run"][0]
    assert ex["passed"] is True


def test_validate_multiplos_exemplos_todos_passam(tmp_path):
    f = _script(tmp_path, "a, b = map(int, input().split())\nprint(a + b)\n")
    examples = [
        {"input": "1 2", "expected_output": "3"},
        {"input": "0 0", "expected_output": "0"},
        {"input": "-1 1", "expected_output": "0"},
    ]
    result = validate(_match(f), examples=examples)
    exs = result["leitura-direta"]["examples_run"]
    assert len(exs) == 3
    assert all(ex["passed"] for ex in exs)


def test_validate_example_index_incrementa(tmp_path):
    f = _script(tmp_path, "a, b = map(int, input().split())\nprint(a + b)\n")
    examples = [
        {"input": "1 2", "expected_output": "3"},
        {"input": "4 5", "expected_output": "9"},
    ]
    result = validate(_match(f), examples=examples)
    exs = result["leitura-direta"]["examples_run"]
    assert exs[0]["example_index"] == 0
    assert exs[1]["example_index"] == 1


def test_validate_expected_output_normaliza_newline(tmp_path):
    """expected_output com \n no final não causa falha de comparação."""
    f = _script(tmp_path, "print('ok')\n")
    result = validate(_match(f), examples=[{"input": "", "expected_output": "ok\n"}])
    ex = result["leitura-direta"]["examples_run"][0]
    assert ex["passed"] is True
