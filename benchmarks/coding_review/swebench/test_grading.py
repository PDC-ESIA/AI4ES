"""Testes da ponte com o harness oficial (sem executar o `swebench`)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.coding_review.swebench import grading
from benchmarks.coding_review.swebench.metrics import (
    GRADE_EMPTY_PATCH,
    GRADE_ERROR,
    GRADE_RESOLVED,
    GRADE_UNRESOLVED,
)

MODELO = "ai4se-coding-review__github_copilot-gpt-5"


def _report(grading_dir: Path, run_id: str, iid: str, conteudo: str) -> None:
    caminho = grading.instance_report_path(grading_dir, run_id, MODELO, iid)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(conteudo)


def test_predicoes_no_formato_do_swebench(tmp_path: Path):
    caminho = tmp_path / "predictions.jsonl"
    grading.write_predictions(caminho, [("a__a-1", "diff\n"), ("b__b-2", "")],
                              model_name_or_path=MODELO)
    linhas = [json.loads(linha) for linha in caminho.read_text().splitlines()]
    assert linhas == [
        {"instance_id": "a__a-1", "model_name_or_path": MODELO, "model_patch": "diff\n"},
        {"instance_id": "b__b-2", "model_name_or_path": MODELO, "model_patch": ""},
    ]


def test_comando_do_run_evaluation():
    comando = grading.build_command(
        "/venv/bin/python", dataset_path=Path("/d/test.parquet"),
        predictions_path=Path("/r/predictions.jsonl"), run_id="run_x",
        instance_ids=["a__a-1", "b__b-2"], max_workers=2, timeout=1800,
    )
    assert comando[:3] == ["/venv/bin/python", "-m", "swebench.harness.run_evaluation"]
    assert comando[comando.index("--dataset_name") + 1] == "/d/test.parquet"
    assert comando[comando.index("--run_id") + 1] == "run_x"
    assert comando[-3:] == ["--instance_ids", "a__a-1", "b__b-2"]


def test_caminho_do_report_troca_barras_do_modelo(tmp_path: Path):
    caminho = grading.instance_report_path(tmp_path, "r", "org/modelo", "a__a-1")
    assert caminho == tmp_path / "logs/run_evaluation/r/org__modelo/a__a-1/report.json"


def test_leitura_dos_resultados(tmp_path: Path):
    run_id = "run_x"
    _report(tmp_path, run_id, "ok__ok-1", json.dumps(
        {"ok__ok-1": {"resolved": True, "patch_successfully_applied": True}}))
    _report(tmp_path, run_id, "nao__nao-1", json.dumps(
        {"nao__nao-1": {"resolved": False, "patch_successfully_applied": False}}))
    _report(tmp_path, run_id, "ruim__ruim-1", "{quebrado")

    resultados = grading.parse_results(
        tmp_path, run_id=run_id, model_name_or_path=MODELO,
        instance_ids=["ok__ok-1", "nao__nao-1", "ruim__ruim-1", "sem__sem-1", "vazio__v-1"],
        empty_patch_ids={"vazio__v-1"},
    )

    assert resultados["ok__ok-1"].status == GRADE_RESOLVED
    assert resultados["ok__ok-1"].resolved is True
    assert resultados["nao__nao-1"].status == GRADE_UNRESOLVED
    assert resultados["nao__nao-1"].patch_applied is False
    assert resultados["ruim__ruim-1"].status == GRADE_ERROR
    assert resultados["sem__sem-1"].status == GRADE_ERROR
    assert resultados["vazio__v-1"].status == GRADE_EMPTY_PATCH
    assert resultados["vazio__v-1"].as_dict()["resolvido"] is False


def test_swebench_ausente_gera_erro_claro(tmp_path: Path):
    with pytest.raises(grading.GradingError, match="swebench"):
        grading.installed_version(str(tmp_path / "nao-existe" / "python"))


def _log(grading_dir: Path, run_id: str, iid: str, conteudo: str) -> None:
    caminho = grading.instance_report_path(grading_dir, run_id, MODELO, iid).with_name(
        "run_instance.log"
    )
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(conteudo)


def test_sem_report_o_log_diz_se_o_patch_falhou_ou_se_foi_erro(tmp_path: Path):
    run_id = "run_x"
    _log(tmp_path, run_id, "apply__a-1", "...\n>>>>> Patch Apply Failed:\nerror: patch failed\n")
    _log(tmp_path, run_id, "lento__l-1", "EvaluationError: Test timed out after 1800 seconds.\n")
    _log(tmp_path, run_id, "infra__i-1", "docker.errors.APIError: 500 Server Error\n")

    resultados = grading.parse_results(
        tmp_path, run_id=run_id, model_name_or_path=MODELO,
        instance_ids=["apply__a-1", "lento__l-1", "infra__i-1"], empty_patch_ids=set(),
    )

    assert resultados["apply__a-1"].status == GRADE_UNRESOLVED
    assert resultados["apply__a-1"].cause == "patch_nao_aplicou"
    assert resultados["apply__a-1"].patch_applied is False
    assert resultados["lento__l-1"].status == GRADE_UNRESOLVED
    assert resultados["lento__l-1"].cause == "timeout_dos_testes"
    assert resultados["infra__i-1"].status == GRADE_ERROR
    assert resultados["infra__i-1"].as_dict()["causa"] == "erro_de_avaliacao"


# --- cache do harness: não reaproveitar resultado de outro patch ----------------


def _avaliada(tmp_path: Path, instance_id: str, patch: str | None, run_id="r1", modelo="m/x"):
    """Simula a pasta que o harness deixa para uma instância já avaliada."""
    pasta = tmp_path / "logs" / "run_evaluation" / run_id / modelo.replace("/", "__") / instance_id
    pasta.mkdir(parents=True)
    (pasta / "report.json").write_text("{}", encoding="utf-8")
    if patch is not None:
        (pasta / "patch.diff").write_text(patch, encoding="utf-8")
    return pasta


def test_resultado_com_o_mesmo_patch_e_mantido(tmp_path: Path):
    pasta = _avaliada(tmp_path, "a__a-1", "diff igual\n")
    invalidadas = grading.invalidate_stale_reports(
        tmp_path, run_id="r1", model_name_or_path="m/x", patches=[("a__a-1", "diff igual\n")]
    )
    assert invalidadas == []
    assert (pasta / "report.json").is_file()


def test_resultado_de_outro_patch_e_descartado(tmp_path: Path):
    pasta = _avaliada(tmp_path, "a__a-1", "patch antigo\n")
    invalidadas = grading.invalidate_stale_reports(
        tmp_path, run_id="r1", model_name_or_path="m/x", patches=[("a__a-1", "patch novo\n")]
    )
    assert invalidadas == ["a__a-1"]
    assert not pasta.exists()


def test_pasta_sem_patch_diff_nao_pode_ser_conferida_e_e_descartada(tmp_path: Path):
    pasta = _avaliada(tmp_path, "a__a-1", None)
    invalidadas = grading.invalidate_stale_reports(
        tmp_path, run_id="r1", model_name_or_path="m/x", patches=[("a__a-1", "qualquer\n")]
    )
    assert invalidadas == ["a__a-1"]
    assert not pasta.exists()


def test_so_a_instancia_alterada_e_invalidada(tmp_path: Path):
    igual = _avaliada(tmp_path, "a__a-1", "p1\n")
    mudou = _avaliada(tmp_path, "a__a-2", "p2 velho\n")
    invalidadas = grading.invalidate_stale_reports(
        tmp_path, run_id="r1", model_name_or_path="m/x",
        patches=[("a__a-1", "p1\n"), ("a__a-2", "p2 novo\n"), ("a__a-3", "p3\n")],
    )
    assert invalidadas == ["a__a-2"]  # a-3 nunca foi avaliada: nada a apagar
    assert igual.exists() and not mudou.exists()


def test_diretorio_de_grading_inexistente_nao_quebra(tmp_path: Path):
    assert grading.invalidate_stale_reports(
        tmp_path / "nao_existe", run_id="r1", model_name_or_path="m/x",
        patches=[("a__a-1", "x\n")],
    ) == []


def test_patch_com_crlf_igual_e_mantido(tmp_path: Path):
    """Regressão: a leitura em texto trocava \\r\\n por \\n e descartava sempre."""
    patch = "diff --git a/x b/x\r\n+linha\r\n"
    pasta = _avaliada(tmp_path, "a__a-1", None)
    (pasta / "patch.diff").write_bytes(patch.encode("utf-8"))
    assert grading.invalidate_stale_reports(
        tmp_path, run_id="r1", model_name_or_path="m/x", patches=[("a__a-1", patch)]
    ) == []
    assert pasta.exists()


def test_patch_diff_fora_de_utf8_e_descartado_sem_excecao(tmp_path: Path):
    pasta = _avaliada(tmp_path, "a__a-1", None)
    (pasta / "patch.diff").write_bytes(b"diff \xff\xfe nao utf8\n")
    assert grading.invalidate_stale_reports(
        tmp_path, run_id="r1", model_name_or_path="m/x", patches=[("a__a-1", "diff novo\n")]
    ) == ["a__a-1"]
    assert not pasta.exists()


def test_patch_vazio_com_resultado_antigo_de_patch_nao_vazio_e_descartado(tmp_path: Path):
    pasta = _avaliada(tmp_path, "a__a-1", "patch antigo\n")
    assert grading.invalidate_stale_reports(
        tmp_path, run_id="r1", model_name_or_path="m/x", patches=[("a__a-1", "")]
    ) == ["a__a-1"]
    assert not pasta.exists()
