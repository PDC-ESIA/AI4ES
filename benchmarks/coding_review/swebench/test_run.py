"""Testes do orquestrador: CLI, retomada, dry-run, correção e relatório."""

from __future__ import annotations

import argparse
import json

import pytest

from benchmarks.coding_review.swebench import grading, report, run
from benchmarks.coding_review.swebench.dataset import SWEInstance


def _instancias() -> list[SWEInstance]:
    return [
        SWEInstance(
            instance_id=f"django__django-{n}", repo="django/django", base_commit="abc",
            version="4.0", problem_statement=f"issue {n}",
            image=f"swebench/sweb.eval.x86_64.django_1776_django-{n}:latest",
        )
        for n in (11099, 11133)
    ]


@pytest.fixture
def instancias_falsas(monkeypatch, tmp_path):
    parquet = tmp_path / "test.parquet"
    monkeypatch.setattr(run, "_carregar_instancias", lambda args: (_instancias(), parquet))
    return parquet


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_model_e_obrigatorio():
    with pytest.raises(ValueError, match="'--model' é obrigatório"):
        run.main(["--limit", "3"])


def test_grade_only_exige_resume_dir():
    with pytest.raises(ValueError, match="exige '--resume-dir'"):
        run.main(["--model", "m", "--grade-only"])


def test_grade_only_e_skip_grading_sao_excludentes(tmp_path):
    with pytest.raises(ValueError, match="excludentes"):
        run.main(["--model", "m", "--grade-only", "--skip-grading", "--resume-dir", str(tmp_path)])


def test_gold_sanity_nao_se_combina_com_dry_run():
    with pytest.raises(ValueError, match="--gold-sanity"):
        run.main(["--model", "m", "--gold-sanity", "--dry-run"])


def test_resume_dir_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError, match="não existe"):
        run.main(["--model", "m", "--resume-dir", str(tmp_path / "nada")])


def test_nomes_do_run_e_do_modelo_nas_predicoes():
    assert run._construir_nome_run("github_copilot/gpt-5", 30, "20260928_120000") == (
        "run_20260928_120000_github_copilot-gpt-5_n30"
    )
    assert "/" not in run.model_name_for_predictions("github_copilot/gpt-5")


# ---------------------------------------------------------------------------
# Metadata e checkpoint
# ---------------------------------------------------------------------------


def _params(**sobrescritas) -> dict:
    params = {"model": "m", "seed": 42, "limit": 30, "instance_ids_filtro": None,
              "dataset_revision": "rev", "instancias": ["a__a-1", "b__b-2"],
              "instance_timeout": 3600, "grading_timeout": 1800}
    params.update(sobrescritas)
    return params


def test_metadata_novo_e_retomada_compativel(tmp_path):
    run._validar_e_persistir_metadata(tmp_path, _params())
    salvo = json.loads((tmp_path / run.METADATA_FILE).read_text())
    assert salvo["parametros"]["instancias"] == ["a__a-1", "b__b-2"]
    assert run._validar_e_persistir_metadata(tmp_path, _params())["parametros"] == _params()


@pytest.mark.parametrize(
    "chave, valor",
    [("model", "outro"), ("seed", 7), ("limit", 10), ("dataset_revision", "x"),
     ("instancias", ["a__a-1"]), ("instance_timeout", 60), ("grading_timeout", 60)],
)
def test_retomada_recusa_parametros_diferentes(tmp_path, chave, valor):
    run._validar_e_persistir_metadata(tmp_path, _params())
    with pytest.raises(ValueError, match=f"'{chave}'"):
        run._validar_e_persistir_metadata(tmp_path, _params(**{chave: valor}))


def test_checkpoint_ignora_linha_truncada(tmp_path):
    caminho = tmp_path / run.PROGRESS_FILE
    run._append_progresso(caminho, {"instance_id": "a__a-1", "rodadas": 2})
    with caminho.open("a") as fh:
        fh.write('{"instance_id": "b__b-2", "rod')
    assert list(run._carregar_progresso(caminho)) == ["a__a-1"]


def test_registro_apos_linha_truncada_nao_se_perde(tmp_path):
    caminho = tmp_path / run.PROGRESS_FILE
    run._append_progresso(caminho, {"instance_id": "a__a-1"})
    with caminho.open("a") as fh:
        fh.write('{"instance_id": "b__b-2", "rod')  # processo morreu aqui
    run._append_progresso(caminho, {"instance_id": "b__b-2", "rodadas": 3})
    assert run._carregar_progresso(caminho)["b__b-2"]["rodadas"] == 3


def test_falha_na_preparacao_e_refeita_na_retomada():
    assert run._concluida({"instance_id": "a__a-1", "rodadas": 2})
    assert not run._concluida(None)
    falha = run._registro_de_falha_na_preparacao(_instancias()[0], "pull falhou")
    assert not run._concluida(falha)


def test_modelo_vem_do_run_original_na_retomada(tmp_path):
    run._validar_e_persistir_metadata(tmp_path, _params(model="github_copilot/gpt-5"))
    args = argparse.Namespace(model=None, resume_dir=tmp_path)
    run._resolver_modelo_da_retomada(args)
    assert args.model == "github_copilot/gpt-5"
    novo = argparse.Namespace(model=None, resume_dir=None)
    run._resolver_modelo_da_retomada(novo)
    assert novo.model is None


# ---------------------------------------------------------------------------
# Dry-run e relatório
# ---------------------------------------------------------------------------


def test_dry_run_gera_tasks_e_mensagens_sem_llm_nem_docker(tmp_path, instancias_falsas):
    assert run.main(["--model", "github_copilot/gpt-5", "--dry-run",
                     "--output-dir", str(tmp_path / "results")]) == 0

    (run_dir,) = (tmp_path / "results").iterdir()
    assert run_dir.name.endswith("_github_copilot-gpt-5_n2")
    metadata = json.loads((run_dir / run.METADATA_FILE).read_text())
    assert metadata["parametros"]["instancias"] == ["django__django-11099", "django__django-11133"]
    base = run_dir / run.DRY_RUN_DIR
    assert json.loads((base / "django__django-11099" / "TASK-001.json").read_text())["id"] == "TASK-001"
    assert "issue 11099" in (base / "django__django-11099" / "mensagem_coder.md").read_text()
    assert json.loads((base / "amostra.json").read_text())["por_repositorio"] == {"django/django": 2}


def _registro(iid: str, patch_rel: str | None, **extra) -> dict:
    return {
        "instance_id": iid, "repo": "django/django", "rodadas": 2,
        "historico_notas": [0.4, 1.0], "motivo_terminacao": "aprovado",
        "status_desfecho": "aprovado", "veredito_validador": "aprovado",
        "execucao": {"test_commands": ["python tests/runtests.py x"],
                     "status_testes": "sucesso", "testes_identificados": 0},
        "patch": {"arquivo": patch_rel, "vazio": patch_rel is None, "arquivos": ["x.py"]},
        "guarda": {}, "uso": {}, "duracao_s": 1.0, **extra,
    }


def test_consolidacao_sem_correcao_marca_nao_avaliado():
    metadata = {"parametros": _params(), "ambiente": {"max_loop_iterations": 20}}
    relatorio = run._consolidar(metadata, [_registro("a__a-1", None)], None)
    assert relatorio["instancias"][0]["grading"]["status"] == "not_graded"
    assert relatorio["metricas"]["metrica_1_resolucao"]["k"] == 0
    markdown = run.render_markdown(relatorio)
    for secao in ("Métrica 1", "Métrica 2", "Métrica 3", "Por instância"):
        assert secao in markdown


def test_fase_de_correcao_com_harness_falso(tmp_path, monkeypatch):
    run_dir = tmp_path / "run_x"
    (run_dir / run.PATCHES_DIR).mkdir(parents=True)
    (run_dir / "patches" / "a__a-1.diff").write_text("diff --git a/x.py b/x.py\n")
    registros = [_registro("a__a-1", "patches/a__a-1.diff"), _registro("b__b-2", None)]
    args = argparse.Namespace(model="github_copilot/gpt-5", swebench_python="/venv/bin/python",
                              grading_workers=2, grading_timeout=1800)
    modelo = run.model_name_for_predictions(args.model)
    chamadas = []

    def _harness_falso(comando, *, grading_dir):
        chamadas.append(comando)
        caminho = grading.instance_report_path(grading_dir, run_dir.name, modelo, "a__a-1")
        caminho.parent.mkdir(parents=True)
        caminho.write_text(json.dumps({"a__a-1": {"resolved": False,
                                                  "patch_successfully_applied": True}}))
        return 0

    monkeypatch.setattr(grading, "run_official_grading", _harness_falso)
    resultados, correcao = run._fase_grading(
        args, run_dir, registros, tmp_path / "t.parquet", "5.0.2"
    )
    assert correcao["returncode"] == 0

    assert resultados["a__a-1"]["status"] == "unresolved"
    assert resultados["b__b-2"]["status"] == "empty_patch"
    predicoes = [json.loads(linha) for linha in (run_dir / run.PREDICTIONS_FILE).read_text().splitlines()]
    assert [p["model_patch"] for p in predicoes] == ["diff --git a/x.py b/x.py\n", ""]
    salvo = json.loads((run_dir / run.GRADING_FILE).read_text())
    assert salvo["swebench_version"] == "5.0.2" and salvo["returncode"] == 0
    assert chamadas[0][-3:] == ["--instance_ids", "a__a-1", "b__b-2"]

    metadata = {"parametros": _params(), "ambiente": {"max_loop_iterations": 20}}
    relatorio = run._consolidar(metadata, registros, resultados)
    assert "Métrica 3" in run.render_markdown(relatorio)
    m3 = relatorio["metricas"]["metrica_3_validador"]
    assert m3["falsos_positivos"] == 2
    assert m3["aprovacoes_qualificadas"] == {"patch_vazio": 1, "testes_nao_identificados": 2}


def test_texto_de_leitura_acompanha_o_numero_de_instancias_do_run():
    """Regressão: o texto dizia '30 instâncias, 3,3 p.p.' mesmo num run parcial (n=26)."""
    def _leitura(n):
        return "\n".join(report._secao_leitura(n))

    assert "com 30 instâncias, cada uma vale 3,3 pontos" in _leitura(30)
    assert "com 26 instâncias, cada uma vale 3,8 pontos" in _leitura(26)
    assert "com 7 instâncias, cada uma vale 14,3 pontos" in _leitura(7)
    assert "—" in _leitura(0)  # sem instâncias não há divisão por zero
    assert "com 1 instância, cada uma vale 100,0 pontos" in _leitura(1)  # singular


def test_relatorio_markdown_usa_o_n_real_no_texto_de_leitura():
    metadata = {"parametros": _params(), "ambiente": {"max_loop_iterations": 20}}
    registros = [_registro("a__a-1", "p/a.diff"), _registro("b__b-2", "p/b.diff")]
    markdown = run.render_markdown(run._consolidar(metadata, registros, None))
    assert "com 2 instâncias, cada uma vale 50,0 pontos" in markdown
    assert "com 30 instâncias" not in markdown


def test_correcao_nao_reaproveita_resultado_de_outro_patch(tmp_path, monkeypatch):
    """Regressão: o harness pula instância com report.json; o patch refeito não pode herdá-lo."""
    run_dir = tmp_path / "run_x"
    (run_dir / run.PATCHES_DIR).mkdir(parents=True)
    (run_dir / "patches" / "a__a-1.diff").write_text("patch NOVO\n")
    args = argparse.Namespace(model="github_copilot/gpt-5", swebench_python="/venv/bin/python",
                              grading_workers=2, grading_timeout=1800)
    modelo = run.model_name_for_predictions(args.model)
    # Resultado que o harness deixou numa avaliação anterior, com o patch ANTIGO.
    antigo = grading.instance_report_path(run_dir / run.GRADING_DIR, run_dir.name, modelo, "a__a-1")
    antigo.parent.mkdir(parents=True)
    antigo.write_text(json.dumps({"a__a-1": {"resolved": False, "patch_successfully_applied": False}}))
    (antigo.parent / "patch.diff").write_text("patch ANTIGO\n")
    existia_na_chamada = []

    def _harness_falso(comando, *, grading_dir):
        existia_na_chamada.append(antigo.exists())  # o harness só vê o que sobrou no disco
        antigo.parent.mkdir(parents=True, exist_ok=True)
        antigo.write_text(json.dumps({"a__a-1": {"resolved": True,
                                                 "patch_successfully_applied": True}}))
        return 0

    monkeypatch.setattr(grading, "run_official_grading", _harness_falso)
    resultados, _ = run._fase_grading(
        args, run_dir, [_registro("a__a-1", "patches/a__a-1.diff")],
        tmp_path / "t.parquet", "5.0.2",
    )
    assert existia_na_chamada == [False]  # o resultado antigo foi descartado antes do harness
    assert resultados["a__a-1"]["status"] == "resolved"


def test_sanidade_gold_lista_quem_nao_resolve_nem_com_o_gabarito(tmp_path, monkeypatch):
    run_dir = tmp_path / "run_x"
    run_dir.mkdir()
    args = argparse.Namespace(swebench_python="/venv/bin/python", grading_workers=2,
                              grading_timeout=1800)
    comandos = []

    def _harness_falso(comando, *, grading_dir):
        comandos.append(comando)
        run_id = f"{run_dir.name}_gold"
        for iid, resolvido in (("django__django-11099", True), ("django__django-11133", False)):
            caminho = grading.instance_report_path(grading_dir, run_id, "gold", iid)
            caminho.parent.mkdir(parents=True)
            caminho.write_text(json.dumps({iid: {"resolved": resolvido}}))
        return 0

    monkeypatch.setattr(grading, "run_official_grading", _harness_falso)
    falhas = run._sanidade_gold(args, run_dir, _instancias(), tmp_path / "t.parquet", "5.0.2")

    assert falhas == ["django__django-11133"]
    assert comandos[0][comandos[0].index("--predictions_path") + 1] == "gold"
    salvo = json.loads((run_dir / run.GOLD_FILE).read_text())
    assert salvo["nao_resolvidas_com_gold"] == ["django__django-11133"]


def test_retomada_preserva_o_ambiente_original_e_avisa_divergencia(capsys):
    original = {"git_commit": "aaa", "max_loop_iterations": 20, "adk_llm_model": "m",
                "variaveis_ai4es": {}}
    metadata = {"parametros": _params()}
    run._registrar_ambiente(metadata, original)
    assert metadata["ambiente"] == original

    run._registrar_ambiente(metadata, {**original})
    assert "Aviso" not in capsys.readouterr().out

    run._registrar_ambiente(metadata, {**original, "git_commit": "bbb"})
    assert metadata["ambiente"]["git_commit"] == "aaa"
    assert [a["git_commit"] for a in metadata["ambientes_de_retomada"]] == ["aaa", "bbb"]
    assert "git_commit" in capsys.readouterr().out


def test_falha_de_preparacao_nao_vai_ao_harness_nem_a_matriz(tmp_path, monkeypatch):
    run_dir = tmp_path / "run_x"
    run_dir.mkdir()
    registros = [run._registro_de_falha_na_preparacao(_instancias()[0], "pull falhou")]
    args = argparse.Namespace(model="m", swebench_python="/venv/bin/python",
                              grading_workers=2, grading_timeout=1800)
    chamadas = []
    monkeypatch.setattr(grading, "run_official_grading",
                        lambda comando, *, grading_dir: chamadas.append(comando) or 0)

    resultados, correcao = run._fase_grading(args, run_dir, registros, tmp_path / "t.parquet", "5.0.2")

    assert chamadas == []  # nenhuma instância avaliável: o harness nem roda
    assert correcao["returncode"] is None
    assert resultados["django__django-11099"]["status"] == "falha_preparacao"
    assert (run_dir / run.PREDICTIONS_FILE).read_text() == ""
    metadata = {"parametros": _params(), "ambiente": {"max_loop_iterations": 20}}
    m = run._consolidar(metadata, registros, resultados)["metricas"]
    assert m["metrica_1_resolucao"]["k"] == 0 and m["metrica_1_resolucao"]["n"] == 1
    assert m["metrica_3_validador"]["com_gabarito"] == 0


def test_exclusoes_do_gold_e_codigo_de_saida_no_relatorio(tmp_path):
    (tmp_path / run.GOLD_FILE).write_text(json.dumps({"nao_resolvidas_com_gold": ["b__b-2"]}))
    excluidas = run._ler_exclusoes_gold(tmp_path)
    assert excluidas == {"b__b-2"}

    registros = [_registro("a__a-1", "p"), _registro("b__b-2", "p")]
    resultados = {
        "a__a-1": {"status": "resolved", "resolvido": True},
        "b__b-2": {"status": "unresolved", "resolvido": False},
    }
    metadata = {"parametros": _params(), "ambiente": {"max_loop_iterations": 20}}
    relatorio = run._consolidar(metadata, registros, resultados,
                                correcao={"returncode": 1}, excluidas=excluidas)

    m1 = relatorio["metricas"]["metrica_1_resolucao"]
    assert (m1["k"], m1["n"]) == (1, 2)
    assert (m1["sem_exclusoes_gold"]["k"], m1["sem_exclusoes_gold"]["n"]) == (1, 1)
    m3 = relatorio["metricas"]["metrica_3_validador"]
    assert m3["falsos_positivos"] == 0 and m3["excluidas_gold"] == 1
    assert relatorio["instancias"][1]["excluida_pelo_gold"] is True
    markdown = run.render_markdown(relatorio)
    assert "código 1" in markdown and "Excluídas pelo gold:** b__b-2" in markdown


def test_sem_arquivo_de_gold_nenhuma_exclusao(tmp_path):
    assert run._ler_exclusoes_gold(tmp_path) == frozenset()


def test_executor_sanity_nao_se_combina_com_outros_modos():
    with pytest.raises(ValueError, match="--executor-sanity"):
        run.main(["--model", "m", "--executor-sanity", "--gold-sanity"])


def test_sanidade_do_executor_entra_no_relatorio(tmp_path):
    (tmp_path / run.EXECUTOR_SANITY_FILE).write_text(json.dumps({
        "n": 2, "sucesso": 1,
        "por_resultado": {"sucesso": 1, "timeout_do_comando_de_teste": 1},
        "sem_sucesso": {"b__b-2": "timeout_do_comando_de_teste"}, "instancias": [],
    }))
    sanidade = run._ler_sanidade_executor(tmp_path)
    assert sanidade["sucesso"] == 1 and "instancias" not in sanidade
    assert run._ler_sanidade_executor(tmp_path / "nada") is None

    metadata = {"parametros": _params(), "ambiente": {"max_loop_iterations": 20}}
    relatorio = run._consolidar(metadata, [_registro("a__a-1", "p")], None,
                                sanidade_executor=sanidade)
    markdown = run.render_markdown(relatorio)
    assert "**1/2**" in markdown and "timeout_do_comando_de_teste" in markdown


@pytest.mark.parametrize(
    "erro, esperado",
    [
        ("RateLimitError: litellm.RateLimitError: 429 quota exceeded", True),
        ("AuthenticationError: token do Copilot expirou", True),
        ("APIConnectionError: connection reset", True),
        ("BadRequestError: Error code: 429 - you have exceeded your quota", True),
        ("ContextWindowExceededError: prompt longo demais", False),
        ("Instância excedeu o teto de 3600s.", False),
        ("ValueError: algo no loop", False),
        (None, False),
    ],
)
def test_erro_do_provedor_e_distinguido_de_falha_do_loop(erro, esperado):
    assert run._falha_do_provedor(erro) is esperado


def test_falha_do_provedor_e_refeita_e_fica_fora_da_correcao(tmp_path, monkeypatch):
    assert not run._concluida({"instance_id": "a__a-1", "falha_provedor": True})
    run_dir = tmp_path / "run_x"
    run_dir.mkdir()
    registros = [_registro("a__a-1", None, falha_provedor=True)]
    args = argparse.Namespace(model="m", swebench_python="/venv/bin/python",
                              grading_workers=2, grading_timeout=1800)
    chamadas = []
    monkeypatch.setattr(grading, "run_official_grading",
                        lambda comando, *, grading_dir: chamadas.append(comando) or 0)
    resultados, _ = run._fase_grading(args, run_dir, registros, tmp_path / "t.parquet", "5.0.2")
    assert chamadas == []
    assert resultados["a__a-1"]["status"] == "falha_provedor_llm"


# ---------------------------------------------------------------------------
# Laço do loop com rate limit (adk real para o workspace; loop, preparação e
# patch falsos — sem LLM e sem Docker)
# ---------------------------------------------------------------------------


def _preparar_laco(tmp_path, monkeypatch, erros):
    import asyncio

    from benchmarks.coding_review.swebench import bootstrap, environment, loop_runner
    from benchmarks.coding_review.swebench import patch as patch_mod

    bootstrap.ensure_adk_on_path()
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    preparacoes, esperas = [], []
    monkeypatch.setattr(environment, "seed_workspace",
                        lambda ws, image, client=None: preparacoes.append(image)
                        or environment.SeedResult(baseline_tree="t"))
    monkeypatch.setattr(loop_runner, "write_task_file", lambda pasta, inst: None)
    respostas = iter(erros)

    async def _run_loop(inst, *, plugin, timeout_s):
        erro = next(respostas)
        return loop_runner.LoopRun(
            instance_id=inst.instance_id, duration_s=1.0, error=erro,
            desfecho={"motivo_terminacao": "erro_operacional" if erro else "aprovado",
                      "status": "reprovado" if erro else "aprovado"},
            veredito_validador=None if erro else "aprovado",
            guarda={"rodadas_executor": 1},
        )

    async def _sleep(segundos):
        esperas.append(segundos)

    monkeypatch.setattr(loop_runner, "run_loop", _run_loop)
    monkeypatch.setattr(patch_mod, "extract_patch",
                        lambda *a, **k: patch_mod.PatchResult(patch="diff\n", files=["x.py"]))
    monkeypatch.setattr(asyncio, "sleep", _sleep)
    run_dir = tmp_path / "run_x"
    run_dir.mkdir()
    args = argparse.Namespace(instance_timeout=10, provider_retries=2, provider_wait=60,
                              max_tokens_per_minute=0)
    return run_dir, args, preparacoes, esperas


def test_rate_limit_espera_e_refaz_a_instancia(tmp_path, monkeypatch):
    import asyncio

    run_dir, args, preparacoes, esperas = _preparar_laco(
        tmp_path, monkeypatch, ["RateLimitError: 429 utility models", None]
    )
    inst = _instancias()[0]
    asyncio.run(run._executar_loop(args, run_dir, [inst]))

    assert esperas == [60]
    assert len(preparacoes) == 2  # a instância é refeita do zero
    registro = run._carregar_progresso(run_dir / run.PROGRESS_FILE)[inst.instance_id]
    assert registro["veredito_validador"] == "aprovado"
    assert not registro.get("falha_provedor")


def test_rate_limit_persistente_para_o_run_sem_contar_como_falha_do_loop(tmp_path, monkeypatch):
    import asyncio

    run_dir, args, preparacoes, esperas = _preparar_laco(
        tmp_path, monkeypatch, ["RateLimitError: 429"] * 3
    )
    inst = _instancias()[0]
    with pytest.raises(SystemExit, match="continuou falhando"):
        asyncio.run(run._executar_loop(args, run_dir, [inst]))

    assert esperas == [60, 120]  # backoff dobrando
    registro = run._carregar_progresso(run_dir / run.PROGRESS_FILE)[inst.instance_id]
    assert registro["falha_provedor"] is True
    assert not run._concluida(registro)


def test_estouro_de_contexto_nunca_e_falha_do_provedor():
    # "142900" contém "429": não pode virar rate limit.
    assert not run._falha_do_provedor(
        "BadRequestError: Github_copilotException - prompt token count of 142900 "
        "exceeds the limit of 128000"
    )
    assert run._falha_do_provedor("APIError: HTTP 429 Too Many Requests")
    assert not run._falha_do_provedor("ValueError: id 14290 inválido")


def test_registro_antigo_de_estouro_e_reclassificado_no_relatorio():
    erro = "BadRequestError: prompt token count of 169117 exceeds the limit of 128000"
    registros = [_registro("a__a-1", None, motivo_terminacao="erro_operacional", erro=erro,
                           veredito_validador=None, rodadas=0, historico_notas=[])]
    metadata = {"parametros": _params(), "ambiente": {"max_loop_iterations": 20}}
    relatorio = run._consolidar(metadata, registros, None)
    assert relatorio["instancias"][0]["motivo_terminacao"] == "estouro_de_contexto"
    m = relatorio["metricas"]
    assert m["metrica_2_loop"]["motivo_parada_detalhe"]["outro"] == {"estouro_de_contexto": 1}
    assert m["operacional"]["estouros_de_contexto"] == ["a__a-1"]
    assert m["operacional"]["erros_operacionais"] == []
    assert "Estouros de contexto do modelo:** 1" in run.render_markdown(relatorio)


def test_only_ids_adia_as_outras_pendentes_sem_apagar_nada(tmp_path, monkeypatch):
    import asyncio

    run_dir, args, preparacoes, _ = _preparar_laco(tmp_path, monkeypatch, [None])
    a, b = _instancias()[:2]
    args.only_ids = [b.instance_id]
    asyncio.run(run._executar_loop(args, run_dir, [a, b]))

    assert len(preparacoes) == 1  # só a `b` foi preparada e rodada
    feitos = run._carregar_progresso(run_dir / run.PROGRESS_FILE)
    assert set(feitos) == {b.instance_id}  # a `a` segue pendente, sem registro
