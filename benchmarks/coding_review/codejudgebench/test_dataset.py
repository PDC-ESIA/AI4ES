"""Testes unitários do dataset.py do CodeJudgeBench (sem acesso à rede)."""

from __future__ import annotations

import json

import pytest

from benchmarks.coding_review.codejudgebench import dataset


def _par(row_idx: int, question_id: str) -> dataset.RepairPair:
    return dataset.RepairPair(
        pair_id=f"claude_3.7_sonnet/{row_idx}",
        split="claude_3.7_sonnet",
        row_idx=row_idx,
        question_id=question_id,
        question_title="t",
        question_content="c",
        platform="atcoder",
        difficulty="easy",
        starter_code="",
        wrong_code="x = 1",
        pos_response="ok",
        neg_response="ko",
    )


@pytest.fixture
def pares() -> list[dataset.RepairPair]:
    # 30 pares distribuídos em 10 problemas (3 pares por problema).
    return [_par(i, f"Q{i % 10}") for i in range(30)]


# ---------------------------------------------------------------------------
# select_pairs
# ---------------------------------------------------------------------------


def test_mesma_seed_mesma_amostra(pares):
    a = dataset.select_pairs(pares, limit=5, seed=7)
    b = dataset.select_pairs(pares, limit=5, seed=7)
    assert [p.pair_id for p in a] == [p.pair_id for p in b]


def test_seeds_diferentes_mudam_a_amostra(pares):
    a = dataset.select_pairs(pares, limit=5, seed=1, max_per_question=None)
    b = dataset.select_pairs(pares, limit=5, seed=2, max_per_question=None)
    assert [p.pair_id for p in a] != [p.pair_id for p in b]


def test_amostra_menor_e_prefixo_da_maior(pares):
    pequena = dataset.select_pairs(pares, limit=4, seed=42)
    grande = dataset.select_pairs(pares, limit=8, seed=42)
    assert [p.pair_id for p in grande[:4]] == [p.pair_id for p in pequena]


def test_um_par_por_questao_por_padrao(pares):
    amostra = dataset.select_pairs(pares, seed=42)
    questoes = [p.question_id for p in amostra]
    assert len(questoes) == len(set(questoes)) == 10


def test_max_per_question_configuravel(pares):
    amostra = dataset.select_pairs(pares, seed=42, max_per_question=2)
    assert len(amostra) == 20


def test_sem_limite_por_questao_devolve_todos(pares):
    assert len(dataset.select_pairs(pares, seed=42, max_per_question=None)) == 30


def test_limit_maior_que_elegiveis(pares):
    assert len(dataset.select_pairs(pares, limit=100, seed=42)) == 10


def test_pair_ids_ignora_amostragem_e_preserva_ordem(pares):
    alvo = ["claude_3.7_sonnet/20", "claude_3.7_sonnet/3"]
    amostra = dataset.select_pairs(pares, limit=1, pair_ids=alvo)
    assert [p.pair_id for p in amostra] == ["claude_3.7_sonnet/3", "claude_3.7_sonnet/20"]


def test_slug_seguro_para_nome_de_arquivo():
    assert _par(42, "Q").slug == "claude_3_7_sonnet_0042"


# ---------------------------------------------------------------------------
# ensure_dataset / load_all (API do Hugging Face simulada)
# ---------------------------------------------------------------------------


def _linha_api(row_idx: int, truncada: bool = False) -> dict:
    return {
        "row_idx": row_idx,
        "row": {
            "question_id": f"Q{row_idx}",
            "question_title": "t",
            "question_content": "c",
            "platform": "leetcode",
            "difficulty": "hard",
            "starter_code": "class Solution: ...",
            "wrong_code": "x = 1",
            "wrong_meta": {"error_message": "Wrong answer"},
            "pos_response": "ok",
            "neg_response": "ko",
        },
        "truncated_cells": ["pos_response"] if truncada else [],
    }


def _api_falsa(total: int, truncar: int | None = None):
    """Simula a API paginada: devolve até 100 linhas a partir do offset pedido."""

    chamadas: list[str] = []

    def _get_json(url: str) -> dict:
        chamadas.append(url)
        if "datasets-server" not in url:
            return {"sha": "abc123"}
        offset = int(url.split("offset=")[1].split("&")[0])
        fim = min(offset + 100, total)
        return {
            "num_rows_total": total,
            "rows": [_linha_api(i, truncada=(i == truncar)) for i in range(offset, fim)],
        }

    return _get_json, chamadas


def test_download_paginado_grava_cache_e_meta(tmp_path, monkeypatch):
    falsa, chamadas = _api_falsa(total=250)
    monkeypatch.setattr(dataset, "_get_json", falsa)

    pares = dataset.load_all(tmp_path, "claude_3.7_sonnet")

    assert len(pares) == 250
    assert sum("datasets-server" in u for u in chamadas) == 3  # 100 + 100 + 50
    meta = dataset.dataset_metadata(tmp_path, "claude_3.7_sonnet")
    assert meta["revision"] == "abc123"
    assert meta["num_rows"] == 250
    assert pares[0].wrong_meta == {"error_message": "Wrong answer"}
    assert pares[0].starter_code == "class Solution: ..."


def test_cache_existente_nao_baixa_de_novo(tmp_path, monkeypatch):
    falsa, chamadas = _api_falsa(total=5)
    monkeypatch.setattr(dataset, "_get_json", falsa)
    dataset.load_all(tmp_path, "claude_3.7_sonnet")
    antes = len(chamadas)

    dataset.load_all(tmp_path, "claude_3.7_sonnet")

    assert len(chamadas) == antes


def test_celula_truncada_aborta_sem_deixar_cache(tmp_path, monkeypatch):
    falsa, _ = _api_falsa(total=150, truncar=120)
    monkeypatch.setattr(dataset, "_get_json", falsa)

    with pytest.raises(RuntimeError, match="truncadas"):
        dataset.ensure_dataset(tmp_path, "claude_3.7_sonnet")

    assert not dataset.cache_path(tmp_path, "claude_3.7_sonnet").exists()


def test_split_invalido(tmp_path):
    with pytest.raises(ValueError, match="inválido"):
        dataset.ensure_dataset(tmp_path, "gpt_4")


def test_cache_em_utf8(tmp_path, monkeypatch):
    falsa, _ = _api_falsa(total=1)

    def _com_acento(url: str) -> dict:
        resposta = falsa(url)
        for r in resposta.get("rows", []):
            r["row"]["question_content"] = "Ação — ≤ 10⁵"
        return resposta

    monkeypatch.setattr(dataset, "_get_json", _com_acento)
    pares = dataset.load_all(tmp_path, "claude_3.7_sonnet")

    assert pares[0].question_content == "Ação — ≤ 10⁵"
    bruto = dataset.cache_path(tmp_path, "claude_3.7_sonnet").read_text(encoding="utf-8")
    assert json.loads(bruto.splitlines()[0])["question_content"] == "Ação — ≤ 10⁵"
