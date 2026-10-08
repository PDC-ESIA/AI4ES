"""Testes unitários do run.py do CodeJudgeBench (reviewer simulado, sem LLM)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import types

import pytest

from benchmarks.coding_review.codejudgebench import run
from benchmarks.coding_review.codejudgebench.dataset import RepairPair


def _par(i: int) -> RepairPair:
    return RepairPair(
        pair_id=f"claude_3.7_sonnet/{i}",
        split="claude_3.7_sonnet",
        row_idx=i,
        question_id=f"Q{i}",
        question_title="t",
        question_content="c",
        platform="atcoder",
        difficulty="easy",
        starter_code="",
        wrong_code="x",
        pos_response="p",
        neg_response="n",
    )


class _Veredito:
    def __init__(self, which: str, verdict: str, kind: str = "ok", erro: str | None = None):
        self.which, self.verdict, self.kind, self.erro = which, verdict, kind, erro
        self.markdown = f"## Status: {verdict}"

    def to_record(self) -> dict:
        return {
            "which": self.which,
            "verdict": self.verdict,
            "outcome_kind": self.kind,
            "code_found": True,
            "attempts": [{"verdict": self.verdict, "error": self.erro, "lenient_status": None, "gate_applied": False, "duration_s": 1.0}],
            "issues": [],
        }


@pytest.fixture
def reviewer_falso(monkeypatch):
    """Substitui o módulo reviewer_runner (que importaria o agente real)."""
    chamadas: list[tuple[str, str]] = []
    comportamento = {"modo": "acerta"}

    async def run_reviewer(par, which, **_):
        chamadas.append((par.pair_id, which))
        if comportamento["modo"] == "cota":
            return _Veredito(which, "absent", "operational", erro="quota exceeded")
        return _Veredito(which, "pass" if which == "pos" else "fail")

    modulo = types.ModuleType("benchmarks.coding_review.codejudgebench.reviewer_runner")
    modulo.run_reviewer = run_reviewer
    monkeypatch.setitem(sys.modules, modulo.__name__, modulo)
    return chamadas, comportamento


def _args(tmp_path, **extra) -> argparse.Namespace:
    base = run._parse_args(["--model", "m", "--output-dir", str(tmp_path)])
    for chave, valor in extra.items():
        setattr(base, chave, valor)
    return base


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_main_sem_modelo():
    with pytest.raises(ValueError, match="parâmetro '--model' é obrigatório"):
        run.main(["--limit", "5"])


def test_main_resume_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError, match="não existe"):
        run.main(["--model", "m", "--resume-dir", str(tmp_path / "nada")])


@pytest.mark.parametrize(
    ("modelo", "esperado"),
    [
        ("gemini-2.5-flash", "gemini/gemini-2.5-flash"),
        ("gemini/gemini-2.5-flash", "gemini/gemini-2.5-flash"),
        ("github_copilot/gpt-4", "github_copilot/gpt-4"),
    ],
)
def test_preflight_usa_o_mesmo_caminho_do_adk(modelo, esperado):
    assert run._modelo_litellm(modelo) == esperado


def test_saida_redirecionada_em_cp1252_nao_quebra(monkeypatch):
    import io

    buffer = io.BytesIO()
    saida = io.TextIOWrapper(buffer, encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", saida)
    run._saida_utf8()
    print("pos=pass neg=fail → correct · Conexão")
    saida.flush()
    assert "→ correct · Conexão" in buffer.getvalue().decode("utf-8")


def test_nome_do_run_segue_a_issue(tmp_path):
    nome = run._construir_nome_run(_args(tmp_path, model="github_copilot/gpt-4"), "20261001_090000", 50)
    assert nome == "run_20261001_090000_github_copilot-gpt-4_n50"


# ---------------------------------------------------------------------------
# metadata.json / retomada
# ---------------------------------------------------------------------------


def test_config_persistida_e_validada_na_retomada(tmp_path):
    args = _args(tmp_path)
    run._validar_e_persistir_config(tmp_path, args, {"extra": 1})
    salvo = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    assert salvo["config"]["model"] == "m" and salvo["extra"] == 1

    with pytest.raises(ValueError, match="'seed'"):
        run._validar_e_persistir_config(tmp_path, _args(tmp_path, seed=7), {})


def test_retomada_com_mesma_config_devolve_metadata_original(tmp_path):
    run._validar_e_persistir_config(tmp_path, _args(tmp_path), {"created_at": "ontem"})
    assert run._validar_e_persistir_config(tmp_path, _args(tmp_path), {"created_at": "hoje"})["created_at"] == "ontem"


# ---------------------------------------------------------------------------
# _executar
# ---------------------------------------------------------------------------


def test_executa_pos_e_neg_e_grava_checkpoint(tmp_path, reviewer_falso):
    chamadas, _ = reviewer_falso
    registros, completo = asyncio.run(run._executar(_args(tmp_path), tmp_path, [_par(1), _par(2)]))

    assert completo is True
    assert [r["outcome"] for r in registros] == ["correct", "correct"]
    assert chamadas == [(f"claude_3.7_sonnet/{i}", w) for i in (1, 2) for w in ("pos", "neg")]
    assert len((tmp_path / "progress.jsonl").read_text(encoding="utf-8").splitlines()) == 2
    assert (tmp_path / "reviews" / "claude_3_7_sonnet_0001_pos.md").is_file()


def test_retomada_pula_concluidos(tmp_path, reviewer_falso):
    chamadas, _ = reviewer_falso
    asyncio.run(run._executar(_args(tmp_path), tmp_path, [_par(1)]))
    chamadas.clear()

    registros, _ = asyncio.run(run._executar(_args(tmp_path), tmp_path, [_par(1), _par(2)]))

    assert [c[0] for c in chamadas] == ["claude_3.7_sonnet/2", "claude_3.7_sonnet/2"]
    assert len(registros) == 2


def test_falha_operacional_interrompe_e_e_refeita_na_retomada(tmp_path, reviewer_falso):
    chamadas, comportamento = reviewer_falso
    comportamento["modo"] = "cota"
    pares = [_par(i) for i in range(5)]

    registros, completo = asyncio.run(run._executar(_args(tmp_path, max_consecutive_operational=2), tmp_path, pares))
    assert completo is False
    assert len(registros) == 2  # parou no 2º par seguido com falha
    assert all(r["outcome"] == "operational" for r in registros)

    comportamento["modo"] = "acerta"
    chamadas.clear()
    registros, completo = asyncio.run(run._executar(_args(tmp_path), tmp_path, pares))
    assert completo is True
    assert len(chamadas) == 10  # os 2 operacionais foram refeitos + 3 novos
    assert all(r["outcome"] == "correct" for r in registros)


def test_relatorio_markdown_tem_as_tres_metricas(tmp_path, reviewer_falso):
    from benchmarks.coding_review.codejudgebench.metrics import compute_metrics

    registros, completo = asyncio.run(run._executar(_args(tmp_path), tmp_path, [_par(1)]))
    relatorio = {
        "generated_at": "agora",
        "complete": completo,
        "total_duration_s": 1.0,
        "metadata": {"config": run._config(_args(tmp_path)), "dataset": {}},
        "metrics": compute_metrics(registros),
        "pairs": registros,
    }
    _, md = run._persistir_relatorio(relatorio, tmp_path)
    texto = md.read_text(encoding="utf-8")
    for trecho in ("Acurácia do julgamento", "Viés posicional", "Resposta inválida (1ª tentativa)", "100.0%"):
        assert trecho in texto
