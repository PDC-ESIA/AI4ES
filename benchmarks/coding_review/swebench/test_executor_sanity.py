"""Testes da sanidade do ambiente do executor (harness e Docker falsos)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from benchmarks.coding_review.swebench import executor_sanity as sanity
from benchmarks.coding_review.swebench.dataset import SWEInstance
from benchmarks.coding_review.swebench.loop_runner import write_task_file
from benchmarks.coding_review.swebench.test_environment import (
    IMAGEM,
    _Client,
    _repo_git,
    _tar_de_diretorio,
)

EVAL_SCRIPT = (
    "#!/bin/bash\ngit apply -v - <<'EOF'\n...\nEOF\n"
    ": '>>>>> Start Test Output'\n"
    "pytest -rA pkg/tests/test_mod.py\n"
    ": '>>>>> End Test Output'\n"
    "git checkout abc pkg/tests/test_mod.py\n"
)


def test_comando_de_teste_oficial_sai_do_eval_script():
    assert sanity.official_test_command(EVAL_SCRIPT) == "pytest -rA pkg/tests/test_mod.py"
    assert sanity.official_test_command("sem marcadores") is None
    vazio = ": '>>>>> Start Test Output'\n: '>>>>> End Test Output'\n"
    assert sanity.official_test_command(vazio) is None


def _report(overall, status_testes="sucesso", resultados=(), implantacao="sucesso"):
    return {
        "overall_status": overall,
        "stages": [
            {"stage": "implantacao_artefato", "status": implantacao,
             "error_code": None if implantacao == "sucesso" else "FALHA_BUILD"},
            {"stage": "testes_automatizados", "status": status_testes,
             "evidence": {"resultados": list(resultados)}},
        ],
    }


def test_classificacao_do_report():
    assert sanity.classify_report(_report("sucesso"))[0] == sanity.RESULTADO_SUCESSO
    timeout = _report("falha", "falha", [{"exit_code": 124, "timed_out": True}])
    assert sanity.classify_report(timeout)[0] == sanity.RESULTADO_TIMEOUT
    oom = _report("falha", "falha", [{"exit_code": 137, "timed_out": False}])
    assert sanity.classify_report(oom)[0] == sanity.RESULTADO_MEMORIA
    falhou = _report("falha", "falha", [
        {"comando": "pytest a.py", "exit_code": 0, "timed_out": False, "saida_tail": "ok"},
        {"comando": "pytest b.py", "exit_code": 2, "timed_out": False,
         "saida_tail": "x" * 5000 + "ERROR collecting b.py"},
    ])
    resultado, detalhe = sanity.classify_report(falhou)
    assert resultado == sanity.RESULTADO_TESTES_FALHARAM
    assert detalhe["exit_codes"] == [0, 2]
    (saida,) = detalhe["saidas_com_falha"]
    assert saida["comando"] == "pytest b.py" and saida["exit_code"] == 2
    assert saida["saida_tail"].endswith("ERROR collecting b.py")
    assert len(saida["saida_tail"]) == 3000
    build = _report("falha", "pulado", implantacao="falha")
    resultado, detalhe = sanity.classify_report(build)
    assert resultado == sanity.RESULTADO_BUILD
    assert detalhe["falhas_de_estagio"] == {"implantacao_artefato": "FALHA_BUILD"}


def _instancia_com_gabarito(repo: Path) -> SWEInstance:
    """Instância cujo patch oficial corrige `pkg/mod.py` e cujo test_patch cria um teste."""
    (repo / "pkg" / "mod.py").write_text("X = 2\n")
    (repo / "pkg" / "test_novo.py").write_text("def test_x():\n    pass\n")
    gerar = subprocess.run(["git", "-C", str(repo), "diff"], capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "add", "-N", "pkg/test_novo.py"], check=True)
    todos = subprocess.run(["git", "-C", str(repo), "diff"], capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "checkout", "--", "pkg/mod.py"], check=True)
    subprocess.run(["git", "-C", str(repo), "rm", "-q", "--cached", "pkg/test_novo.py"], check=True)
    (repo / "pkg" / "test_novo.py").unlink()
    patch_oficial = gerar.stdout
    test_patch = todos.stdout[len(patch_oficial):]
    return SWEInstance(
        instance_id="pkg__pkg-1", repo="pkg/pkg", base_commit="x", version="1",
        problem_statement="p", image=IMAGEM, patch=patch_oficial,
        test_patch=test_patch, eval_script=EVAL_SCRIPT,
    )


def test_aplica_a_solucao_oficial_e_declara_o_comando_oficial(tmp_path: Path):
    repo = _repo_git(tmp_path / "origem")
    inst = _instancia_com_gabarito(repo)
    cliente = _Client(_tar_de_diretorio(repo))
    coder_src = tmp_path / "ws" / "coder" / "src"
    vistos = {}

    def _harness(task_id, iteracao):
        vistos["mod"] = (coder_src / "pkg" / "mod.py").read_text()
        vistos["teste"] = (coder_src / "pkg" / "test_novo.py").is_file()
        vistos["run"] = json.loads((coder_src / "run.json").read_text())
        return _report("sucesso")

    registro = sanity.check_instance(
        inst, coder_src=coder_src, tasks_dir=tmp_path / "ws" / "coder" / "tasks",
        harness=_harness, write_task=write_task_file, client=cliente,
    )

    assert registro["resultado"] == sanity.RESULTADO_SUCESSO
    assert vistos["mod"] == "X = 2\n" and vistos["teste"] is True
    assert vistos["run"]["test"] == ["pytest -rA pkg/tests/test_mod.py"]
    assert vistos["run"]["sandbox"] == "docker"


def test_falhas_viram_registro(tmp_path: Path):
    repo = _repo_git(tmp_path / "origem")
    base = SWEInstance(instance_id="a__a-1", repo="a/a", base_commit="x", version="1",
                       problem_statement="p", image=IMAGEM)
    sem_comando = sanity.check_instance(
        base, coder_src=tmp_path / "c" / "src", tasks_dir=tmp_path / "t",
        harness=lambda *a: {}, write_task=write_task_file, client=_Client(_tar_de_diretorio(repo)),
    )
    assert sem_comando["resultado"] == sanity.RESULTADO_SEM_COMANDO

    patch_invalido = SWEInstance(**{**base.__dict__, "eval_script": EVAL_SCRIPT,
                                    "patch": "diff --git a/x b/x\nlixo\n"})
    registro = sanity.check_instance(
        patch_invalido, coder_src=tmp_path / "c2" / "src", tasks_dir=tmp_path / "t2",
        harness=lambda *a: {}, write_task=write_task_file, client=_Client(_tar_de_diretorio(repo)),
    )
    assert registro["resultado"] == sanity.RESULTADO_PREPARACAO
    assert "SnapshotError" in registro["erro"]
