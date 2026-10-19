"""Testes do backoff do reviewer_runner (sem LLM)."""

from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest

from benchmarks.coding_review.codejudgebench.dataset import RepairPair

F = "`" * 3


@pytest.fixture
def runner_mod(tmp_path, monkeypatch):
    adk = Path(__file__).resolve().parents[3] / "adk"
    monkeypatch.syspath_prepend(str(adk))
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))
    return importlib.import_module("benchmarks.coding_review.codejudgebench.reviewer_runner")


def _par() -> RepairPair:
    return RepairPair(
        pair_id="claude_3.7_sonnet/1", split="claude_3.7_sonnet", row_idx=1, question_id="q",
        question_title="t", question_content="c", platform="atcoder", difficulty="easy",
        starter_code="", wrong_code="x", pos_response=f"{F}python\nprint(1)\n{F}", neg_response="n",
    )


def _simular(monkeypatch, runner_mod, tentativas):
    """Substitui a chamada real ao LLM por uma sequência de desfechos."""
    fila = list(tentativas)
    esperas: list[float] = []

    async def uma_revisao(*_a, **_k):
        verdict, erro = fila.pop(0)
        tentativa = runner_mod.ReviewAttempt(
            verdict=verdict, lenient_status=None, gate_applied=False, duration_s=0.0, error=erro
        )
        return tentativa, "" if verdict == "absent" else f"## Status: {verdict}", None

    async def dormir(segundos):
        esperas.append(segundos)

    monkeypatch.setattr(runner_mod, "_uma_revisao", uma_revisao)
    monkeypatch.setattr(runner_mod.asyncio, "sleep", dormir)
    return esperas


def test_erro_de_api_espera_com_backoff_exponencial(runner_mod, monkeypatch):
    esperas = _simular(monkeypatch, runner_mod, [("absent", "503"), ("absent", "503"), ("pass", None)])
    veredito = asyncio.run(runner_mod.run_reviewer(_par(), "pos", max_retries=2, backoff_s=5))
    assert esperas == [5, 10]
    assert veredito.verdict == "pass" and len(veredito.attempts) == 3


def test_resposta_sem_status_repete_sem_esperar(runner_mod, monkeypatch):
    esperas = _simular(monkeypatch, runner_mod, [("absent", None), ("pass", None)])
    asyncio.run(runner_mod.run_reviewer(_par(), "pos", max_retries=1, backoff_s=5))
    assert esperas == []


def test_backoff_tem_teto(runner_mod, monkeypatch):
    esperas = _simular(monkeypatch, runner_mod, [("absent", "x")] * 5 + [("pass", None)])
    asyncio.run(runner_mod.run_reviewer(_par(), "pos", max_retries=5, backoff_s=50))
    assert max(esperas) == runner_mod._BACKOFF_MAX_S
