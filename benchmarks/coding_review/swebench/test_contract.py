"""Testes do contrato entregue ao loop — em especial, que o gabarito não vaza."""

from __future__ import annotations

import json
import re

from benchmarks.coding_review.swebench._testutils import ADK_DIR, load_isolated_module
from benchmarks.coding_review.swebench.contract import (
    TASK_ID,
    build_coder_message,
    build_task_contract,
    suggested_test_command,
)
from benchmarks.coding_review.swebench.dataset import SWEInstance

# Uma sentinela única por campo do gabarito: se qualquer uma aparecer no que o
# coder ou o validador recebem, o benchmark deixou de ser justo.
SENTINELAS = {
    "patch": "SENTINELA_PATCH_OURO_7f3a",
    "test_patch": "SENTINELA_TEST_PATCH_91bc",
    "fail_to_pass": "SENTINELA_F2P_4d2e",
    "pass_to_pass": "SENTINELA_P2P_c05f",
    "hints_text": "SENTINELA_HINTS_aa19",
    "eval_script": "SENTINELA_EVAL_SCRIPT_3e77",
}


def _instancia(repo: str = "django/django") -> SWEInstance:
    return SWEInstance(
        instance_id="django__django-11099",
        repo=repo,
        base_commit="d26b2424437dabeeca94d7900b37d2df4410da0c",
        version="3.0",
        problem_statement="UsernameValidator allows trailing newline in usernames",
        image="swebench/sweb.eval.x86_64.django_1776_django-11099:latest",
        patch=f"diff --git a/x.py b/x.py\n+{SENTINELAS['patch']}\n",
        test_patch=f"diff --git a/tests/t.py b/tests/t.py\n+{SENTINELAS['test_patch']}\n",
        fail_to_pass=(f"tests/t.py::{SENTINELAS['fail_to_pass']}",),
        pass_to_pass=(f"tests/t.py::{SENTINELAS['pass_to_pass']}",),
        hints_text=SENTINELAS["hints_text"],
        eval_script=f": '>>>>> Start Test Output'\npytest {SENTINELAS['eval_script']}\n",
    )


def test_nada_do_gabarito_vaza_para_task_ou_mensagem():
    inst = _instancia()
    exposto = json.dumps(build_task_contract(inst), ensure_ascii=False)
    exposto += build_coder_message(inst)
    for campo, sentinela in SENTINELAS.items():
        assert sentinela not in exposto, f"campo `{campo}` do gabarito vazou"


def test_task_no_formato_que_a_producao_aceita():
    task = build_task_contract(_instancia())
    assert task["id"] == TASK_ID
    assert re.fullmatch(r"TASK-[0-9]+", task["id"])  # `task_iterator._ID_TASK_RE`

    # Os critérios passam pela normalização da produção sem trocar de id.
    criterios_mod = load_isolated_module(
        ADK_DIR / "shared" / "tools" / "coding_tools" / "criterios_aceite.py",
        "_swebench_criterios_aceite",
    )
    normalizados = criterios_mod.normalizar_criterios(task["acceptance_criteria"])
    assert [c.id for c in normalizados] == ["CA-01", "CA-02"]
    assert all(c.automatable for c in normalizados)


def test_mensagem_traz_o_issue_e_as_regras_do_ambiente():
    mensagem = build_coder_message(_instancia())
    assert "UsernameValidator allows trailing newline" in mensagem
    assert '"sandbox": "docker"' in mensagem
    assert "NÃO crie virtualenv" in mensagem
    assert f"coder/tasks/{TASK_ID}.json" in mensagem
    assert "{{" not in mensagem and "}}" not in mensagem


def test_dica_de_comando_de_teste_por_repositorio():
    assert "tests/runtests.py" in suggested_test_command("django/django")
    assert "bin/test" in suggested_test_command("sympy/sympy")
    assert "pytest" in suggested_test_command("astropy/astropy")
    assert "runtests.py" in build_coder_message(_instancia("django/django"))
    assert "pytest" in build_coder_message(_instancia("psf/requests"))
