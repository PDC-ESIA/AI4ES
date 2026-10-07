"""Testes da ingestão e do sorteio do SWE-bench Verified (offline)."""

from __future__ import annotations

import json

import pytest

from benchmarks.coding_review.swebench.dataset import (
    SWEInstance,
    distribution_by_repo,
    image_for,
    instance_from_row,
    load_instances,
    paths_touched_by_diff,
    select_instances,
)


def _linha(instance_id: str, repo: str = "django/django", **extra) -> dict:
    linha = {
        "instance_id": instance_id,
        "repo": repo,
        "base_commit": "abc123",
        "version": "4.0",
        "problem_statement": f"issue de {instance_id}",
        "image": None,
        "difficulty": "<15 min fix",
        "created_at": "2022-01-01T00:00:00Z",
        "patch": "diff --git a/x.py b/x.py\n",
        "test_patch": "diff --git a/tests/t.py b/tests/t.py\n",
        "FAIL_TO_PASS": ["tests/t.py::test_a"],
        "PASS_TO_PASS": ["tests/t.py::test_b"],
        "hints_text": "dica",
    }
    linha.update(extra)
    return linha


def _instancias(n: int) -> list[SWEInstance]:
    return [instance_from_row(_linha(f"repo__repo-{i:04d}")) for i in range(n)]


def test_instance_from_row_aceita_lista_e_string_json():
    lista = instance_from_row(_linha("a__a-1"))
    texto = instance_from_row(
        _linha("a__a-2", FAIL_TO_PASS=json.dumps(["x"]), PASS_TO_PASS="[]")
    )
    assert lista.fail_to_pass == ("tests/t.py::test_a",)
    assert texto.fail_to_pass == ("x",) and texto.pass_to_pass == ()


def test_imagem_da_coluna_tem_precedencia():
    inst = instance_from_row(_linha("a__a-1", image="registry/imagem:tag"))
    assert inst.image == "registry/imagem:tag"


def test_imagem_derivada_segue_o_padrao_oficial():
    # Mesmo valor que a coluna `image` traz para esta instância no dataset.
    assert image_for("astropy__astropy-12907") == (
        "swebench/sweb.eval.x86_64.astropy_1776_astropy-12907:latest"
    )
    assert image_for("Foo__Bar-1") == "swebench/sweb.eval.x86_64.foo_1776_bar-1:latest"


def test_sorteio_e_deterministico_e_ordenado():
    instancias = _instancias(50)
    a = select_instances(instancias, limit=10, seed=42)
    b = select_instances(list(reversed(instancias)), limit=10, seed=42)
    c = select_instances(instancias, limit=10, seed=7)
    ids_a = [i.instance_id for i in a]
    assert ids_a == [i.instance_id for i in b]
    assert ids_a == sorted(ids_a) and len(ids_a) == 10
    assert ids_a != [i.instance_id for i in c]


def test_limit_maior_que_o_total_devolve_todas():
    assert len(select_instances(_instancias(5), limit=30, seed=1)) == 5
    assert len(select_instances(_instancias(5), limit=None, seed=1)) == 5


def test_limit_invalido():
    with pytest.raises(ValueError, match="--limit"):
        select_instances(_instancias(5), limit=0, seed=1)


def test_selecao_por_ids():
    instancias = _instancias(10)
    escolhidas = select_instances(
        instancias, limit=None, seed=1, instance_ids=["repo__repo-0007", "repo__repo-0002"]
    )
    assert [i.instance_id for i in escolhidas] == ["repo__repo-0002", "repo__repo-0007"]
    with pytest.raises(ValueError, match="inexistente"):
        select_instances(instancias, limit=None, seed=1, instance_ids=["nao__existe-1"])


def test_caminhos_do_test_patch():
    diff = (
        "diff --git a/tests/test_a.py b/tests/test_a.py\n--- a/tests/test_a.py\n"
        "diff --git a/tests/novo.py b/tests/novo.py\nnew file mode 100644\n"
    )
    assert paths_touched_by_diff(diff) == ("tests/novo.py", "tests/test_a.py")
    assert paths_touched_by_diff("") == ()


def test_load_instances_do_parquet(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq

    linhas = [_linha("b__b-2", repo="b/b"), _linha("a__a-1", repo="a/a")]
    caminho = tmp_path / "test.parquet"
    pq.write_table(pa.Table.from_pylist(linhas), caminho)

    carregadas = load_instances(caminho)
    assert [i.instance_id for i in carregadas] == ["a__a-1", "b__b-2"]
    assert carregadas[0].pass_to_pass == ("tests/t.py::test_b",)


def test_distribuicao_por_repo():
    instancias = [
        instance_from_row(_linha("d__d-1")),
        instance_from_row(_linha("d__d-2")),
        instance_from_row(_linha("s__s-1", repo="sympy/sympy")),
    ]
    assert distribution_by_repo(instancias) == {"django/django": 2, "sympy/sympy": 1}
