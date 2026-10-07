"""Unit tests for the SlopCodeBench benchmark (CLI, Resume Guard, dataset, metrics)."""

from __future__ import annotations

import argparse
import json

import pytest

from benchmarks.coding_review.slopcodebench import dataset, run


def _catalogo(tmp_path, nomes=("alpha", "beta", "gamma", "delta"), n_cp=3):
    """Cria um catálogo falso no formato do scb-problems."""
    for nome in nomes:
        pasta = tmp_path / nome
        pasta.mkdir()
        checkpoints = "\n".join(
            f"  checkpoint_{i}:\n    version: 1\n    order: {i}"
            for i in range(1, n_cp + 1)
        )
        (pasta / "config.yaml").write_text(
            f"name: {nome}\nentry_file: main\ncheckpoints:\n{checkpoints}\n",
            encoding="utf-8",
        )
    (tmp_path / "scripts").mkdir()  # diretório sem config.yaml é ignorado
    return tmp_path


def test_main_missing_model():
    """Asserts ValueError is raised when --model is not provided."""
    with pytest.raises(ValueError, match="parâmetro '--model' é obrigatório"):
        run.main(["--limit", "5"])


def test_main_nonexistent_resume_dir(tmp_path):
    """Asserts FileNotFoundError is raised when --resume-dir does not exist."""
    with pytest.raises(FileNotFoundError, match="não existe ou não é um diretório"):
        run.main(["--model", "gpt-4", "--resume-dir", str(tmp_path / "nada")])


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("github_copilot/gpt-4", "github_copilot-gpt-4"),
        ("openrouter/vendor/model", "openrouter-vendor-model"),
        ("   ", "na"),
    ],
)
def test_sanitizar_componente(raw, expected):
    assert run._sanitizar_componente(raw) == expected


def test_construir_nome_run():
    args = argparse.Namespace(model="github_copilot/gpt-4")
    nome = run._construir_nome_run(args, "20260928_120000", 10)
    assert nome == "run_20260928_120000_github_copilot-gpt-4_n10"


def _params(**over):
    base = {
        "model": "gpt-4",
        "limit": 10,
        "seed": 42,
        "problems": ["alpha", "beta"],
        "checkpoint_timeout_s": 7200,
    }
    return {**base, **over}


def test_validar_e_persistir_config_new_run(tmp_path):
    run._validar_e_persistir_config(tmp_path, _params(), {"repo_commit": "abc"})
    salvo = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    assert salvo["model"] == "gpt-4"
    assert salvo["problems"] == ["alpha", "beta"]
    assert salvo["pass_policy"] == "any"
    assert salvo["repo_commit"] == "abc"


def test_validar_e_persistir_config_resume_mismatch(tmp_path):
    run._validar_e_persistir_config(tmp_path, _params(), {})
    with pytest.raises(ValueError, match="'seed'"):
        run._validar_e_persistir_config(tmp_path, _params(seed=7), {})


def test_estados_dos_checkpoints(tmp_path):
    """Mesma regra do runner oficial: ran / error / skipped."""
    (problema,) = dataset.load_problems(
        _catalogo(tmp_path, nomes=("alpha",), n_cp=3), names=["alpha"]
    )
    detalhes = [
        {"problem": "alpha", "checkpoint": "checkpoint_1", "coder_error": None},
        {"problem": "alpha", "checkpoint": "checkpoint_2", "grading_error": "infra"},
    ]
    assert run._estados_dos_checkpoints([problema], detalhes) == {
        "alpha": {
            "checkpoint_1": "ran",
            "checkpoint_2": "error",
            "checkpoint_3": "skipped",
        }
    }


def test_interrompe_trajetoria():
    """Só o erro do coder para a trajetória; falha de avaliação não."""
    assert run._interrompe_trajetoria({"passed_policy": True, "coder_error": "boom"})
    assert not run._interrompe_trajetoria({"passed_policy": True, "coder_error": None})
    assert not run._interrompe_trajetoria(
        {"passed_policy": False, "grading_error": "docker fora"}
    )


def test_validar_e_persistir_config_resume_proveniencia(tmp_path):
    """Retomar com outro prompt do coder (ou harness/catálogo) é recusado."""
    original = {"coder_prompt_sha256": "aaa", "scb_problems_commit": "38d627e"}
    run._validar_e_persistir_config(tmp_path, _params(), original)
    run._validar_e_persistir_config(tmp_path, _params(), original)  # igual: aceita
    with pytest.raises(ValueError, match="'coder_prompt_sha256'"):
        run._validar_e_persistir_config(
            tmp_path, _params(), {**original, "coder_prompt_sha256": "bbb"}
        )


def test_carregar_progresso_ignora_falha_de_avaliacao(tmp_path):
    """Checkpoint com falha de avaliação não é cache: a retomada o refaz."""
    progresso = tmp_path / "progress.jsonl"
    linhas = [
        {"problem": "alpha", "checkpoint": "checkpoint_1", "grading_error": None},
        {"problem": "alpha", "checkpoint": "checkpoint_2", "grading_error": "docker"},
    ]
    progresso.write_text("".join(json.dumps(x) + "\n" for x in linhas))
    assert set(run._carregar_progresso(progresso)) == {("alpha", "checkpoint_1")}


def test_pendencias_marcam_relatorio_incompleto():
    metricas = {"correctness": {"checkpoints_ran": 3}}
    assert run._pendencias([{"problem": "a", "checkpoint": "c1"}], metricas) == []
    pend = run._pendencias(
        [{"problem": "a", "checkpoint": "c1", "grading_error": "docker"}], metricas
    )
    assert pend and "a/c1" in pend[0]
    assert run._pendencias([], {"correctness": {"checkpoints_ran": 0}}) == [
        "nenhum checkpoint foi avaliado"
    ]


def test_dataset_sorteio_deterministico(tmp_path):
    raiz = _catalogo(tmp_path)
    a = [p.name for p in dataset.load_problems(raiz, limit=2, seed=42)]
    b = [p.name for p in dataset.load_problems(raiz, limit=2, seed=42)]
    assert a == b
    assert len(set(a)) == 2


def test_dataset_ordem_dos_checkpoints_e_nomes(tmp_path):
    raiz = _catalogo(tmp_path, nomes=("alpha",), n_cp=3)
    (problema,) = dataset.load_problems(raiz, names=["alpha"])
    assert problema.checkpoints == ("checkpoint_1", "checkpoint_2", "checkpoint_3")
    assert problema.entry_file == "main"
    with pytest.raises(ValueError, match="inexistentes"):
        dataset.load_problems(raiz, names=["zeta"])


def test_dataset_catalogo_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError, match="Catálogo do SlopCodeBench"):
        dataset.resolve_problems_root(tmp_path / "nada")


def test_dataset_download_do_catalogo(tmp_path):
    """Baixa o tarball fixado para datasets/ uma única vez (sem rede: file://)."""
    import io
    import tarfile

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        conteudo = b"name: alpha\nentry_file: main\ncheckpoints: {}\n"
        info = tarfile.TarInfo("scb-problems-abc/alpha/config.yaml")
        info.size = len(conteudo)
        tar.addfile(info, io.BytesIO(conteudo))
    arquivo = tmp_path / "catalogo.tar.gz"
    arquivo.write_bytes(buf.getvalue())

    datasets_dir = tmp_path / "datasets"
    raiz = dataset.ensure_catalog(datasets_dir, url=arquivo.as_uri())
    assert raiz == datasets_dir / f"scb-problems-{dataset.CATALOG_COMMIT}"
    assert (raiz / "alpha" / "config.yaml").is_file()
    assert dataset.source_commit(raiz) == dataset.CATALOG_COMMIT

    # Segunda chamada reaproveita o que já foi baixado (URL inválida não é usada).
    arquivo.unlink()
    assert dataset.ensure_catalog(datasets_dir, url=arquivo.as_uri()) == raiz


def _bins_falsos(pares):
    """Substitui `compute_progress_bins` do harness: progresso = cp / nº de cps."""
    total = {}
    for problema, checkpoint in pares:
        n = int(checkpoint.rsplit("_", 1)[-1])
        total[problema] = max(total.get(problema, 0), n)
    return [int(c.rsplit("_", 1)[-1]) / total[p] for p, c in pares]


def test_metrics_aggregate(tmp_path):
    from benchmarks.coding_review.slopcodebench.metrics import aggregate

    raiz = _catalogo(tmp_path, nomes=("alpha",), n_cp=3)
    problemas = dataset.load_problems(raiz, names=["alpha"])
    rows = [
        {
            "problem": "alpha",
            "checkpoint": "checkpoint_1",
            "state": "ran",
            "strict_pass_rate": 1.0,
            "isolated_pass_rate": 1.0,
            "core_pass_rate": 1.0,
            "verbosity": 0.3,
            "erosion": 0.4,
        },
        {
            "problem": "alpha",
            "checkpoint": "checkpoint_2",
            "state": "ran",
            "strict_pass_rate": 0.5,
            "isolated_pass_rate": 1.0,
            "core_pass_rate": 1.0,
            "regression_passed": 1,
            "regression_total": 2,
            "delta": {"churn_ratio": 0.25},
            "verbosity": 0.5,
            "erosion": 0.6,
        },
    ]
    quebras = {("alpha", "checkpoint_2"): {"passavam": 2, "quebraram": 1}}
    m = aggregate(rows, problemas, _bins_falsos, quebras)
    corr = m["correctness"]
    # checkpoint_3 não rodou: conta como não resolvido no denominador.
    assert corr["checkpoints_expected"] == 3
    assert corr["pct_checkpoints_strict_solved"] == pytest.approx(33.33)
    assert corr["pct_checkpoints_iso_solved"] == pytest.approx(66.67)
    assert corr["regression"]["checkpoints_that_broke_prior_work"] == 1
    assert m["diff"]["delta.churn_ratio"]["mean"] == 0.25
    assert m["slop"]["pct_trajectories_rising"]["erosion"]["pct"] == 100.0
    assert m["by_checkpoint"][2]["state"] == "not_run"
    assert set(m["by_phase"]) == {"33%", "67%", "100%"}
    assert m["by_phase"]["100%"]["ran"] == 0


def test_grading_harness_sem_venv(monkeypatch, tmp_path):
    """SCBENCH_HARNESS_PATH apontando para pasta sem venv falha com mensagem clara."""
    from benchmarks.coding_review.slopcodebench import grading

    monkeypatch.setenv(grading.HARNESS_PATH_ENV, str(tmp_path))
    with pytest.raises(FileNotFoundError, match="Venv do harness não encontrado"):
        grading.check_harness()


def test_grading_ensure_harness(tmp_path):
    """Baixa o harness fixado e instala o venv uma única vez (sem rede nem uv)."""
    import io
    import tarfile

    from benchmarks.coding_review.slopcodebench import grading

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo("slop-code-bench-abc/pyproject.toml")
        tar.addfile(info, io.BytesIO(b""))
    arquivo = tmp_path / "harness.tar.gz"
    arquivo.write_bytes(buf.getvalue())

    instalacoes = []

    def _sync_falso(raiz):
        instalacoes.append(raiz)
        python = raiz / ".venv" / "bin" / "python"
        python.parent.mkdir(parents=True)
        python.touch()

    datasets_dir = tmp_path / "datasets"
    raiz = grading.ensure_harness(datasets_dir, url=arquivo.as_uri(), sync=_sync_falso)
    assert raiz == datasets_dir / f"slop-code-bench-{grading.HARNESS_COMMIT}"
    assert (raiz / "pyproject.toml").is_file()
    assert dataset.source_commit(raiz) == grading.HARNESS_COMMIT

    # Segunda chamada não baixa nem instala de novo.
    arquivo.unlink()
    grading.ensure_harness(datasets_dir, url=arquivo.as_uri(), sync=_sync_falso)
    assert instalacoes == [raiz]


def test_grading_falha_de_avaliacao_vira_dado(monkeypatch, tmp_path):
    """Erro no harness durante o grading não derruba o run: vira GradeResult."""
    from benchmarks.coding_review.slopcodebench import grading

    monkeypatch.setenv(grading.HARNESS_PATH_ENV, str(tmp_path))
    catalogo = tmp_path / "catalogo"
    catalogo.mkdir()
    (problema,) = dataset.load_problems(
        _catalogo(catalogo, nomes=("alpha",)), names=["alpha"]
    )
    grade = grading.grade_checkpoint(problema, "checkpoint_1", tmp_path)
    assert grade.passed_policy is False
    assert "Venv do harness não encontrado" in grade.error


@pytest.fixture
def coder_runner(monkeypatch):
    """Importa o `coder_runner` com o `adk/` no sys.path, como o bootstrap faz."""
    from benchmarks.coding_review.slopcodebench import bootstrap

    monkeypatch.syspath_prepend(str(bootstrap.adk_dir()))
    from benchmarks.coding_review.slopcodebench import coder_runner as modulo

    return modulo


def test_llm_indisponivel_classifica_erros(coder_runner):
    import litellm

    cota = litellm.RateLimitError(
        message="quota_exceeded", llm_provider="github_copilot", model="gpt-4o"
    )
    assert coder_runner.llm_indisponivel(cota)

    # Embrulhado em outra exceção (como o ADK pode fazer), pela mensagem ou causa.
    try:
        raise RuntimeError("falha no agente") from cota
    except RuntimeError as embrulhado:
        assert coder_runner.llm_indisponivel(embrulhado)
    assert coder_runner.llm_indisponivel(ValueError("Error: quota exceeded"))

    # Erro comum do coder continua sendo falha do coder.
    assert not coder_runner.llm_indisponivel(ValueError("arquivo inválido"))


def test_llm_indisponivel_interrompe_sem_registrar_checkpoint(
    monkeypatch, tmp_path, coder_runner
):
    """Cota esgotada no meio do problema: nada vai para o progress.jsonl."""
    import asyncio

    from benchmarks.coding_review.slopcodebench import grading

    catalogo = tmp_path / "catalogo"
    catalogo.mkdir()
    (problema,) = dataset.load_problems(
        _catalogo(catalogo, nomes=("alpha",)), names=["alpha"]
    )

    chamadas = []

    async def _coder_sem_cota(*_args, **_kwargs):
        chamadas.append(1)
        raise coder_runner.LlmIndisponivel("RateLimitError: quota_exceeded")

    save_dir = tmp_path / "cp"
    save_dir.mkdir()
    monkeypatch.setattr(grading, "checkpoint_output_dir", lambda *a: save_dir)
    monkeypatch.setattr(grading, "render_prompt", lambda *a, **k: ("p", "main.py"))
    monkeypatch.setattr(coder_runner, "iniciar_problema", lambda: None)
    monkeypatch.setattr(coder_runner, "run_coder", _coder_sem_cota)
    monkeypatch.setattr(run, "_ESPERAS_ENTRE_TENTATIVAS_S", (0,))

    progress = tmp_path / "progress.jsonl"
    args = argparse.Namespace(model="m", checkpoint_timeout=10)

    # Limite por checkpoint: a tentativa original + 2 novas, depois interrompe.
    with pytest.raises(coder_runner.LlmIndisponivel):
        asyncio.run(run._executar_problema(problema, args, tmp_path, progress, {}))
    assert len(chamadas) == run._TENTATIVAS_POR_CHECKPOINT
    assert not progress.exists()

    # Limite do run inteiro: com 1 nova tentativa restante, só 2 chamadas.
    chamadas.clear()
    orcamento = run._OrcamentoDeTentativas(restantes=1)
    with pytest.raises(coder_runner.LlmIndisponivel):
        asyncio.run(
            run._executar_problema(problema, args, tmp_path, progress, {}, orcamento)
        )
    assert len(chamadas) == 2
    assert orcamento.restantes == 0
    assert not progress.exists()


def test_comando_de_retomada_repete_parametros_validados(tmp_path):
    args = argparse.Namespace(
        model="github_copilot/gpt-4o",
        problems=["dag_execution"],
        limit=None,
        seed=7,
        checkpoint_timeout=600,
        problems_path=None,
    )
    comando = run._comando_de_retomada(args, tmp_path)
    assert f"--resume-dir {tmp_path}" in comando
    assert "--problems dag_execution" in comando
    assert "--seed 7" in comando
    assert "--checkpoint-timeout 600" in comando
    assert "--limit" not in comando


def test_llm_indisponivel_reconhece_timeout_do_provider(coder_runner):
    """Timeout do provider (caso real do run) não pode virar erro do coder."""
    import litellm

    timeout = litellm.Timeout(
        message="Request timed out.", model="gpt-4", llm_provider="github_copilot"
    )
    assert coder_runner.llm_indisponivel(timeout)


def test_ctrl_c_na_avaliacao_interrompe_sem_registrar(monkeypatch, tmp_path):
    """Subprocesso do harness morto por Ctrl+C vira interrupção, não falha."""
    import subprocess

    from benchmarks.coding_review.slopcodebench import grading

    python = tmp_path / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.touch()
    monkeypatch.setenv(grading.HARNESS_PATH_ENV, str(tmp_path))
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, returncode=-2),
    )
    with pytest.raises(KeyboardInterrupt):
        grading.check_harness()


def test_registrar_execucao_guarda_timeout_de_cada_execucao(monkeypatch, tmp_path):
    """Cada início/retomada ganha uma entrada com o timeout do LLM em vigor."""
    (tmp_path / "metadata.json").write_text(
        json.dumps({"model": "m"}), encoding="utf-8"
    )

    monkeypatch.setenv("AI4ES_LLM_TIMEOUT", "120")
    run._registrar_execucao(tmp_path)
    monkeypatch.setenv("AI4ES_LLM_TIMEOUT", "600")
    run._registrar_execucao(tmp_path)

    salvo = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    assert salvo["model"] == "m"
    assert [e["llm_timeout_s"] for e in salvo["execucoes"]] == [120.0, 600.0]
    assert {"iniciada_em", "repo_commit", "codigo_do_benchmark_alterado"} <= set(
        salvo["execucoes"][0]
    )


def test_regression_breaks_compara_teste_a_teste(tmp_path):
    """Só conta como quebra o teste que PASSAVA antes e falhou na regressão."""
    from benchmarks.coding_review.slopcodebench.metrics import regression_breaks

    catalogo = tmp_path / "catalogo"
    catalogo.mkdir()
    (problema,) = dataset.load_problems(
        _catalogo(catalogo, nomes=("alpha",), n_cp=2), names=["alpha"]
    )
    avaliacoes = {
        "checkpoint_1": {
            "checkpoint_1-Core": {"passed": ["t_ok", "t_quebra"], "failed": ["t_nunca"]}
        },
        "checkpoint_2": {
            "checkpoint_1-Regression": {
                "passed": ["t_ok"],
                "failed": ["t_quebra", "t_nunca"],
            },
            "checkpoint_2-Core": {"passed": [], "failed": ["t_novo"]},
        },
    }
    for checkpoint, grupos in avaliacoes.items():
        pasta = tmp_path / "scb" / "alpha" / checkpoint
        pasta.mkdir(parents=True)
        (pasta / "evaluation.json").write_text(json.dumps({"tests": grupos}))

    quebras = regression_breaks(tmp_path / "scb", [problema])
    # t_nunca já falhava no checkpoint 1: não é quebra.
    assert quebras == {("alpha", "checkpoint_2"): {"passavam": 2, "quebraram": 1}}


def _simular_problema(monkeypatch, tmp_path, coder_runner, avaliacao_falha_em=()):
    """Liga `_executar_problema` a um coder e um avaliador falsos (sem LLM/Docker).

    Devolve (problema, checkpoints em que o coder rodou).
    """
    from benchmarks.coding_review.slopcodebench import grading

    catalogo = tmp_path / "catalogo"
    catalogo.mkdir(parents=True)
    (problema,) = dataset.load_problems(
        _catalogo(catalogo, nomes=("alpha",), n_cp=3), names=["alpha"]
    )
    rodou = []

    async def _coder(mensagem, contrato, **_kwargs):
        rodou.append(contrato["contract"]["checkpoint"])
        return coder_runner.CoderGeneration(task_id=contrato["id"], files=[])

    def _pasta(_problema, pasta_problema, checkpoint):
        pasta = pasta_problema / checkpoint
        pasta.mkdir(parents=True, exist_ok=True)
        return pasta

    def _avaliar(_problema, checkpoint, _save_dir):
        if checkpoint in avaliacao_falha_em:
            return grading.GradeResult(passed_policy=False, error="docker fora")
        return grading.GradeResult(
            passed_policy=True, pass_counts={"core": 1}, total_counts={"core": 1}
        )

    monkeypatch.setattr(grading, "checkpoint_output_dir", _pasta)
    monkeypatch.setattr(grading, "render_prompt", lambda *a, **k: ("p", "main.py"))
    monkeypatch.setattr(grading, "write_inference_result", lambda *a, **k: None)
    monkeypatch.setattr(grading, "grade_checkpoint", _avaliar)
    monkeypatch.setattr(coder_runner, "iniciar_problema", lambda: None)
    monkeypatch.setattr(coder_runner, "restaurar_de_snapshot", lambda *a: None)
    monkeypatch.setattr(coder_runner, "salvar_snapshot", lambda *a: None)
    monkeypatch.setattr(coder_runner, "run_coder", _coder)
    return problema, rodou


def test_falha_de_avaliacao_nao_interrompe_e_e_refeita(
    monkeypatch, tmp_path, coder_runner
):
    """Cenário da revisão: avaliação falha no checkpoint 1 de um problema de 3.

    No run, o problema segue até o checkpoint 3. Na retomada, o checkpoint 1 é
    refeito (não vira CACHE) e os seguintes não ficam presos atrás dele.
    """
    import asyncio

    problema, rodou = _simular_problema(
        monkeypatch, tmp_path, coder_runner, avaliacao_falha_em=("checkpoint_1",)
    )
    progresso = tmp_path / "progress.jsonl"
    args = argparse.Namespace(model="m", checkpoint_timeout=10)

    detalhes = asyncio.run(
        run._executar_problema(problema, args, tmp_path / "scb", progresso, {})
    )
    assert rodou == ["checkpoint_1", "checkpoint_2", "checkpoint_3"]
    assert detalhes[0]["grading_error"] == "docker fora"
    assert run._estados_dos_checkpoints([problema], detalhes)["alpha"] == {
        "checkpoint_1": "error",
        "checkpoint_2": "ran",
        "checkpoint_3": "ran",
    }

    # Retomada com o progress.jsonl que ficou: só o checkpoint 1 roda de novo.
    problema, rodou = _simular_problema(monkeypatch, tmp_path / "r", coder_runner)
    concluidos = run._carregar_progresso(progresso)
    asyncio.run(
        run._executar_problema(problema, args, tmp_path / "scb", progresso, concluidos)
    )
    assert rodou == ["checkpoint_1"]


def test_retomada_de_progresso_antigo_parado_na_falha_de_avaliacao(
    monkeypatch, tmp_path, coder_runner
):
    """progress.jsonl antigo, parado no checkpoint 1 por falha de avaliação."""
    import asyncio

    progresso = tmp_path / "progress.jsonl"
    progresso.write_text(
        json.dumps(
            {
                "problem": "alpha",
                "checkpoint": "checkpoint_1",
                "passed_policy": False,
                "grading_error": "docker fora",
            }
        )
        + "\n"
    )
    problema, rodou = _simular_problema(monkeypatch, tmp_path, coder_runner)
    args = argparse.Namespace(model="m", checkpoint_timeout=10)
    asyncio.run(
        run._executar_problema(
            problema,
            args,
            tmp_path / "scb",
            progresso,
            run._carregar_progresso(progresso),
        )
    )
    # Antes: só CACHE do checkpoint 1 e parada. Agora: segue até o fim.
    assert rodou == ["checkpoint_1", "checkpoint_2", "checkpoint_3"]


def test_trajetorias_exigem_metrica_no_primeiro_e_no_ultimo(tmp_path):
    """Sem métrica no 1º checkpoint, a trajetória fica fora da conta."""
    from benchmarks.coding_review.slopcodebench.metrics import aggregate

    (problema,) = dataset.load_problems(
        _catalogo(tmp_path, nomes=("alpha",), n_cp=3), names=["alpha"]
    )
    rows = [
        {"problem": "alpha", "checkpoint": f"checkpoint_{i}", "state": "ran", **v}
        for i, v in ((1, {}), (2, {"erosion": 0.3}), (3, {"erosion": 0.5}))
    ]
    subida = aggregate(rows, [problema], _bins_falsos)["slop"][
        "pct_trajectories_rising"
    ]
    assert subida["erosion"] == {
        "trajectories": 0,
        "rising": 0,
        "excluded": 1,
        "pct": None,
    }
