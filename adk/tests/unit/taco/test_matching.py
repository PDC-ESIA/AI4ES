"""Testes unitários para matching.py — associação arquivo↔variação."""
from pathlib import Path

import pytest

from src.agents.workflow_taco.matching import (
    MatchResult,
    _is_candidate,
    _label_slug,
    match_files,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _py(tmp_path: Path, name: str) -> Path:
    f = tmp_path / name
    f.write_text("x = 1", encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# _label_slug
# ---------------------------------------------------------------------------

def test_label_slug_hifens_para_underscores():
    assert _label_slug("leitura-direta") == "leitura_direta"


def test_label_slug_maiusculas_normalizadas():
    assert _label_slug("Com-Funcao-E-Tipagem") == "com_funcao_e_tipagem"


def test_label_slug_sem_hifens():
    assert _label_slug("iterativa") == "iterativa"


# ---------------------------------------------------------------------------
# _is_candidate
# ---------------------------------------------------------------------------

def test_is_candidate_py_simples(tmp_path):
    f = _py(tmp_path, "solution.py")
    assert _is_candidate(f, tmp_path) is True


def test_is_candidate_exclui_pasta_tests(tmp_path):
    d = tmp_path / "tests"
    d.mkdir()
    f = d / "test_sol.py"
    f.write_text("x = 1", encoding="utf-8")
    assert _is_candidate(f, tmp_path) is False


def test_is_candidate_exclui_pasta_test(tmp_path):
    d = tmp_path / "test"
    d.mkdir()
    f = d / "helper.py"
    f.write_text("x = 1", encoding="utf-8")
    assert _is_candidate(f, tmp_path) is False


def test_is_candidate_exclui_prefixo_test_(tmp_path):
    f = _py(tmp_path, "test_solution.py")
    assert _is_candidate(f, tmp_path) is False


def test_is_candidate_exclui_sufixo__test(tmp_path):
    f = _py(tmp_path, "solution_test.py")
    assert _is_candidate(f, tmp_path) is False


def test_is_candidate_exclui_nao_py_md(tmp_path):
    f = tmp_path / "PLAN.md"
    f.write_text("# doc", encoding="utf-8")
    assert _is_candidate(f, tmp_path) is False


def test_is_candidate_exclui_nao_py_json(tmp_path):
    f = tmp_path / "run.json"
    f.write_text("{}", encoding="utf-8")
    assert _is_candidate(f, tmp_path) is False


# ---------------------------------------------------------------------------
# match_files — exact match
# ---------------------------------------------------------------------------

def test_exact_match_simples(tmp_path):
    _py(tmp_path, "leitura_direta.py")
    result = match_files(tmp_path, [{"label": "leitura-direta"}])
    mr = result["leitura-direta"]
    assert mr.strategy == "exact"
    assert mr.path is not None
    assert mr.path.name == "leitura_direta.py"


def test_exact_match_multiplas_variacoes(tmp_path):
    _py(tmp_path, "leitura_direta.py")
    _py(tmp_path, "iterativa.py")
    variations = [{"label": "leitura-direta"}, {"label": "iterativa"}]
    result = match_files(tmp_path, variations)
    assert result["leitura-direta"].strategy == "exact"
    assert result["iterativa"].strategy == "exact"
    assert result["leitura-direta"].path != result["iterativa"].path


def test_exact_match_tem_prioridade_sobre_fuzzy(tmp_path):
    _py(tmp_path, "leitura_direta.py")
    _py(tmp_path, "leitura_direta_v2.py")
    result = match_files(tmp_path, [{"label": "leitura-direta"}])
    mr = result["leitura-direta"]
    assert mr.strategy == "exact"
    assert mr.path.name == "leitura_direta.py"


# ---------------------------------------------------------------------------
# match_files — fuzzy match
# ---------------------------------------------------------------------------

def test_fuzzy_match_slug_contido_no_stem(tmp_path):
    _py(tmp_path, "com_funcao_e_tipagem.py")
    result = match_files(tmp_path, [{"label": "com-funcao"}])
    mr = result["com-funcao"]
    assert mr.strategy == "fuzzy"
    assert mr.path is not None


def test_fuzzy_match_stem_contido_no_slug(tmp_path):
    _py(tmp_path, "iterativa.py")
    result = match_files(tmp_path, [{"label": "iterativa-com-listas"}])
    mr = result["iterativa-com-listas"]
    assert mr.strategy == "fuzzy"
    assert mr.path is not None


# ---------------------------------------------------------------------------
# match_files — positional fallback
# ---------------------------------------------------------------------------

def test_positional_quando_sem_correspondencia_semantica(tmp_path):
    _py(tmp_path, "arquivo_xyz.py")
    result = match_files(tmp_path, [{"label": "label-sem-match"}])
    mr = result["label-sem-match"]
    assert mr.strategy == "positional"
    assert mr.path is not None


# ---------------------------------------------------------------------------
# match_files — label sem arquivo (POSSÍVEL_TRUNCAMENTO)
# ---------------------------------------------------------------------------

def test_possivel_truncamento_sem_nenhum_arquivo(tmp_path):
    result = match_files(tmp_path, [{"label": "leitura-direta"}])
    mr = result["leitura-direta"]
    assert mr.path is None
    assert mr.strategy == "not_found"
    assert mr.cause == "POSSÍVEL_TRUNCAMENTO"


def test_possivel_truncamento_com_menos_arquivos_que_variacoes(tmp_path):
    _py(tmp_path, "leitura_direta.py")
    variations = [{"label": "leitura-direta"}, {"label": "com-funcao"}]
    result = match_files(tmp_path, variations)
    assert result["leitura-direta"].path is not None
    mr_sem = result["com-funcao"]
    assert mr_sem.path is None
    assert mr_sem.cause == "POSSÍVEL_TRUNCAMENTO"


# ---------------------------------------------------------------------------
# match_files — artefatos SDLC são ignorados
# ---------------------------------------------------------------------------

def test_ignora_artefatos_sdlc_no_workspace(tmp_path):
    _py(tmp_path, "leitura_direta.py")
    (tmp_path / "PLAN.md").write_text("# plan", encoding="utf-8")
    (tmp_path / "run.json").write_text("{}", encoding="utf-8")
    (tmp_path / "README.md").write_text("# readme", encoding="utf-8")
    result = match_files(tmp_path, [{"label": "leitura-direta"}])
    mr = result["leitura-direta"]
    assert mr.strategy == "exact"
    assert mr.path.suffix == ".py"


def test_arquivo_de_teste_nao_e_candidato(tmp_path):
    _py(tmp_path, "leitura_direta.py")
    _py(tmp_path, "test_leitura_direta.py")
    result = match_files(tmp_path, [{"label": "leitura-direta"}])
    mr = result["leitura-direta"]
    assert mr.path.name == "leitura_direta.py"
