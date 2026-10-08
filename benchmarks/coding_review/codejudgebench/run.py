"""Orquestrador CLI do benchmark CodeJudgeBench (CodeRepair) sobre o Reviewer Agent.

Uso típico (a partir da raiz do repositório):

    python -m benchmarks.coding_review.codejudgebench.run --model github_copilot/gpt-4 --limit 50

Fluxo:
1. carrega e amostra os pares (download dinâmico na primeira vez);
2. `bootstrap.prepare_environment` fixa `sys.path`, `.env` e o workspace ANTES
   de qualquer import do agente — com a memória mem0 forçada para desligada;
3. pre-flight: uma chamada mínima ao modelo, para falhar antes de começar;
4. para cada par: o reviewer avalia `pos` e `neg` separadamente, e o par é
   classificado pelo `grading` (checkpoint a cada par em progress.jsonl);
5. calcula as métricas e grava report.json + report.md + metadata.json.

Retomada: `--resume-dir` reaproveita os pares já concluídos. Pares que terminaram
em falha operacional (cota, rede) são refeitos, porque não chegaram a ser julgados.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from benchmarks.coding_review.codejudgebench import dataset as ds
from benchmarks.coding_review.humaneval import bootstrap

_DEFAULT_OUTPUT = Path(__file__).resolve().parent / "results"
_DEFAULT_DATASET_DIR = Path(__file__).resolve().parent / "datasets"

# Parâmetros que definem o experimento: precisam ser idênticos numa retomada.
_CONFIG_KEYS = ("model", "split", "seed", "max_per_question", "include_explanation", "max_retries")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="benchmarks.coding_review.codejudgebench.run",
        description="Executa o CodeJudgeBench (CodeRepair) usando o Reviewer Agent do AI4ES.",
    )
    p.add_argument("--model", default=None, help="Modelo LLM do reviewer (obrigatório, ex.: github_copilot/gpt-4).")
    p.add_argument("--limit", type=int, default=None, help="Máximo de pares a avaliar (default: todos os elegíveis).")
    p.add_argument("--split", default=ds.DEFAULT_SPLIT, choices=ds.SPLITS, help=f"Split do CodeRepair (default: {ds.DEFAULT_SPLIT}).")
    p.add_argument("--seed", type=int, default=ds.DEFAULT_SEED, help=f"Semente da amostragem (default: {ds.DEFAULT_SEED}).")
    p.add_argument(
        "--max-per-question",
        type=int,
        default=ds.DEFAULT_MAX_PER_QUESTION,
        help="Máximo de pares por problema; 0 = sem limite (default: 1).",
    )
    p.add_argument("--pair-ids", nargs="*", default=None, help="Avalia só estes pares (ex.: claude_3.7_sonnet/262).")
    p.add_argument("--max-retries", type=int, default=1, help="Retries quando a revisão vem sem status (default: 1).")
    p.add_argument(
        "--no-explanation",
        action="store_true",
        help="Não envia o relato do coder (texto da resposta sem o código) ao reviewer.",
    )
    p.add_argument(
        "--max-consecutive-operational",
        type=int,
        default=3,
        help="Interrompe o run após N pares seguidos com falha operacional (default: 3).",
    )
    p.add_argument("--dataset-dir", type=Path, default=_DEFAULT_DATASET_DIR, help="Diretório do cache do dataset.")
    p.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT, help="Diretório-base dos relatórios.")
    p.add_argument("--resume-dir", type=Path, default=None, help="Retoma um run existente a partir do progress.jsonl.")
    return p.parse_args(argv)


def _config(args: argparse.Namespace) -> dict:
    return {
        "model": args.model,
        "split": args.split,
        "seed": args.seed,
        "max_per_question": args.max_per_question,
        "include_explanation": not args.no_explanation,
        "max_retries": args.max_retries,
    }


def _modelo_litellm(model: str) -> str:
    """Nome do modelo para o LiteLLM usado no pre-flight.

    O ADK resolve `gemini-*` nativamente (Google AI Studio, via GOOGLE_API_KEY),
    mas o LiteLLM trata `gemini-*` sem prefixo como Vertex AI. O prefixo
    `gemini/` faz o pre-flight testar o mesmo caminho que o reviewer vai usar.
    """
    if model.startswith("gemini-"):
        return f"gemini/{model}"
    return model


def _testar_conexao_modelo(model: str) -> None:
    """Pre-flight: chamada mínima ao modelo; aborta com o erro completo se falhar."""
    import traceback

    import litellm

    print(f"\n[PRE-FLIGHT] Testando conexão com o modelo '{model}'...")
    try:
        from shared.llm import copilot_completion_kwargs

        extras = copilot_completion_kwargs(model)
    except Exception:  # noqa: BLE001 — helper opcional
        extras = {}
    try:
        litellm.completion(
            model=_modelo_litellm(model),
            messages=[{"role": "user", "content": "ping"}],
            # Modelos com raciocínio (ex.: gpt-5-mini) recusam max_tokens=1.
            max_tokens=64,
            timeout=30,
            **extras,
        )
        print("[PRE-FLIGHT] Conexão estabelecida com sucesso!\n")
    except Exception:  # noqa: BLE001 — qualquer falha aborta o benchmark
        print("\n" + "=" * 80)
        print(f"[PRE-FLIGHT ERROR] Falha ao conectar ao modelo '{model}'.")
        print("=" * 80)
        traceback.print_exc()
        print("=" * 80)
        print(
            "DICA: verifique credenciais, cota do provedor (ex.: cota mensal do "
            "GitHub Copilot) e conectividade.\n"
        )
        raise SystemExit(1)


def _sanitizar_componente(valor: str) -> str:
    limpo = re.sub(r"[^0-9A-Za-z._-]+", "-", valor.strip())
    limpo = re.sub(r"-{2,}", "-", limpo).strip("-.")
    return limpo or "na"


def _construir_nome_run(args: argparse.Namespace, timestamp: str, n_pares: int) -> str:
    """Formato da issue #421: ``run_<timestamp>_<modelo>_n<N>``."""
    return f"run_{timestamp}_{_sanitizar_componente(args.model)}_n{n_pares}"


def _carregar_progresso(progress_path: Path) -> dict[str, dict]:
    """Lê o checkpoint; a última linha de cada par prevalece (retentativas)."""
    concluidos: dict[str, dict] = {}
    if not progress_path.is_file():
        return concluidos
    for linha in progress_path.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha:
            continue
        try:
            registro = json.loads(linha)
            concluidos[registro["pair_id"]] = registro
        except (json.JSONDecodeError, KeyError):
            print(f"[run] Aviso: linha inválida em {progress_path.name}, ignorada.")
    return concluidos


def _append_progresso(progress_path: Path, registro: dict) -> None:
    with progress_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(registro, ensure_ascii=False) + "\n")
        fh.flush()


def _validar_e_persistir_config(run_dir: Path, args: argparse.Namespace, contexto: dict) -> dict:
    """Garante que uma retomada usa o mesmo experimento; grava metadata.json.

    Returns:
        O conteúdo do metadata.json (config + contexto do ambiente).
    """
    config_path = run_dir / "metadata.json"
    atual = _config(args)
    if config_path.is_file():
        salvo = json.loads(config_path.read_text(encoding="utf-8"))
        for chave in _CONFIG_KEYS:
            if salvo.get("config", {}).get(chave) != atual[chave]:
                raise ValueError(
                    f"Erro: '{chave}' ({atual[chave]!r}) difere do run original "
                    f"({salvo.get('config', {}).get(chave)!r}). Uma retomada precisa "
                    "usar exatamente o mesmo experimento."
                )
        # A config igual não basta: outro --limit ou outros --pair-ids mudam a
        # amostra, e a retomada misturaria checkpoints de amostras diferentes.
        if salvo.get("pair_ids") != contexto.get("pair_ids"):
            raise ValueError(
                "Erro: os pares selecionados diferem do run original "
                f"({len(contexto.get('pair_ids') or [])} agora, "
                f"{len(salvo.get('pair_ids') or [])} no original). Retome com o mesmo "
                "--limit / --pair-ids, ou inicie um run novo."
            )
        revisao_salva = (salvo.get("dataset") or {}).get("revision")
        revisao_atual = (contexto.get("dataset") or {}).get("revision")
        if revisao_salva != revisao_atual:
            raise ValueError(
                f"Erro: a revisão do dataset ({revisao_atual!r}) difere do run "
                f"original ({revisao_salva!r})."
            )
        return salvo

    run_dir.mkdir(parents=True, exist_ok=True)
    metadata = {"config": atual, **contexto}
    config_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def _contexto_do_ambiente(args: argparse.Namespace, pares: list[ds.RepairPair]) -> dict:
    """Protocolo §5/§6: registrar ambiente, versões e parâmetros do experimento."""
    try:
        from importlib.metadata import version

        versao_adk = version("google-adk")
        versao_litellm = version("litellm")
    except Exception:  # noqa: BLE001
        versao_adk = versao_litellm = None
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "limit": args.limit,
        "pair_ids": [p.pair_id for p in pares],
        "dataset": ds.dataset_metadata(args.dataset_dir, args.split),
        "mode": "pointwise",
        "reviewer_static_analysis": os.environ.get("REVIEWER_STATIC_ANALYSIS", "1") != "0",
        "memory_enabled": False,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "google_adk": versao_adk,
            "litellm": versao_litellm,
        },
    }


def _salvar_markdown(run_dir: Path, par: ds.RepairPair, which: str, markdown: str) -> None:
    destino = run_dir / "reviews" / f"{par.slug}_{which}.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(markdown or "", encoding="utf-8")


async def _executar(args: argparse.Namespace, run_dir: Path, pares: list[ds.RepairPair]) -> tuple[list[dict], bool]:
    """Loop principal. Devolve (registros na ordem da amostra, run completo?)."""
    from benchmarks.coding_review.codejudgebench.grading import grade_pair
    from benchmarks.coding_review.codejudgebench.reviewer_runner import run_reviewer

    progress_path = run_dir / "progress.jsonl"
    concluidos = _carregar_progresso(progress_path)
    reaproveitaveis = {k: v for k, v in concluidos.items() if v["outcome"] != "operational"}
    if reaproveitaveis:
        print(f"[run] Retomando: {len(reaproveitaveis)} par(es) já concluído(s), pulando-os.")
    print(f"[run] {len(pares)} par(es) a avaliar, 2 revisões por par (pos e neg).")

    registros: dict[str, dict] = dict(reaproveitaveis)
    operacionais_seguidos = 0
    interrompido = False

    for idx, par in enumerate(pares, start=1):
        if par.pair_id in reaproveitaveis:
            print(f"[run] ({idx}/{len(pares)}) {par.pair_id}: CACHE ({reaproveitaveis[par.pair_id]['outcome']})")
            continue

        t0 = time.time()
        resultados = {}
        for which in ("pos", "neg"):
            veredito = await run_reviewer(
                par,
                which,
                model=args.model,
                max_retries=args.max_retries,
                include_explanation=not args.no_explanation,
            )
            _salvar_markdown(run_dir, par, which, veredito.markdown)
            resultados[which] = veredito.to_record()

        registro = {
            "pair_id": par.pair_id,
            "question_id": par.question_id,
            "difficulty": par.difficulty,
            "platform": par.platform,
            "outcome": grade_pair(resultados["pos"], resultados["neg"]),
            "pos": resultados["pos"],
            "neg": resultados["neg"],
            "duration_s": round(time.time() - t0, 2),
        }
        registros[par.pair_id] = registro
        _append_progresso(progress_path, registro)
        print(
            f"[run] ({idx}/{len(pares)}) {par.pair_id} [{par.difficulty}]: "
            f"pos={resultados['pos']['verdict']} neg={resultados['neg']['verdict']} "
            f"→ {registro['outcome']} ({registro['duration_s']}s)"
        )

        if registro["outcome"] == "operational":
            operacionais_seguidos += 1
            if operacionais_seguidos >= args.max_consecutive_operational:
                print(
                    f"[run] {operacionais_seguidos} pares seguidos com falha operacional "
                    f"(último erro: {resultados['pos']['attempts'][-1].get('error') if resultados['pos']['attempts'] else '?'}). "
                    "Interrompendo — retome com --resume-dir quando o provedor voltar."
                )
                interrompido = True
                break
        else:
            operacionais_seguidos = 0

    ordenados = [registros[p.pair_id] for p in pares if p.pair_id in registros]
    completo = not interrompido and all(r["outcome"] != "operational" for r in ordenados) and len(ordenados) == len(pares)
    return ordenados, completo


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------


def _pct(valor: float | None) -> str:
    return "—" if valor is None else f"{valor * 100:.1f}%"


def _ic(proporcao: dict) -> str:
    ic = proporcao.get("ci95")
    return "—" if not ic else f"{ic[0] * 100:.1f}% – {ic[1] * 100:.1f}%"


def _linha_proporcao(nome: str, proporcao: dict) -> str:
    return f"| {nome} | {_pct(proporcao['value'])} | {_ic(proporcao)} | {proporcao['k']}/{proporcao['n']} |"


def _render_markdown(relatorio: dict) -> str:
    m = relatorio["metrics"]
    meta = relatorio["metadata"]
    cfg = meta["config"]
    dataset_meta = meta.get("dataset") or {}
    j, d, f = m["judgment"], m["decision"], m["format"]
    linhas = [
        "# Benchmark CodeJudgeBench (CodeRepair) — Reviewer Agent",
        "",
        f"- **Gerado em:** {relatorio['generated_at']}",
        f"- **Status do run:** {'completo' if relatorio['complete'] else 'INTERROMPIDO (resultados parciais)'}",
        f"- **Modelo do reviewer:** `{cfg['model']}`",
        f"- **Dataset:** `{dataset_meta.get('dataset', ds.DATASET_ID)}` · config `{ds.CONFIG}` · "
        f"split `{cfg['split']}` · revisão `{(dataset_meta.get('revision') or '?')[:12]}`",
        f"- **Amostra:** {m['pairs']['total']} pares · seed {cfg['seed']} · "
        f"máx. {cfg['max_per_question'] or 'ilimitado'} par(es) por problema",
        f"- **Modo:** pontual (cada resposta revisada separadamente) · relato do coder: "
        f"{'sim' if cfg['include_explanation'] else 'não'} · retries: {cfg['max_retries']} · "
        f"análise estática: {'ligada' if meta.get('reviewer_static_analysis') else 'desligada'}",
        "",
        "## Métricas da issue #421",
        "",
        "| Métrica | Valor | IC 95% | k/n |",
        "| --- | --- | --- | --- |",
        _linha_proporcao("Acurácia do julgamento (empate = erro)", j["accuracy"]),
        "| Viés posicional | n/a | — | — |",
        _linha_proporcao("Resposta inválida — status não reconhecido pelo manifesto (1ª tentativa)", f["invalid_first_attempt_rate"]),
        _linha_proporcao("Resposta inválida — status não reconhecido pelo manifesto (após retries)", f["invalid_final_rate"]),
        "",
        f"> Viés posicional: {j['positional_bias_note']}",
        ">",
        "> Resposta inválida mede se o pipeline consegue ler o veredito (a linha `Status:` que o "
        "manifesto procura). O reviewer produz markdown, não JSON: não há aderência ao `ReviewOutput` "
        "a medir — o harness converte o markdown nesse schema depois.",
        "",
        "## Decisão por resposta",
        "",
        "| Métrica | Valor | IC 95% | k/n |",
        "| --- | --- | --- | --- |",
        _linha_proporcao("Aprovou código que falha nos testes (neg aprovada)", d["false_approve_rate"]),
        _linha_proporcao("Bloqueou código que passa nos testes (pos bloqueada)", d["false_block_rate"]),
        "",
        "Camadas das issues críticas nos bloqueios indevidos: "
        + (", ".join(f"{k}={v}" for k, v in d["critical_issue_layers_on_false_blocks"].items()) or "nenhuma"),
        "",
        "## Julgamento detalhado",
        "",
        "| Métrica | Valor | IC 95% | k/n |",
        "| --- | --- | --- | --- |",
        _linha_proporcao("Decisividade (vereditos diferentes)", j["decisiveness"]),
        _linha_proporcao("Acurácia entre pares decididos", j["accuracy_when_decided"]),
        f"| Acurácia com empate = ½ acerto | {_pct(j['accuracy_ties_half'])} | — | — |",
        "",
        "| Desfecho | Pares |",
        "| --- | --- |",
        *[f"| `{k}` | {v} |" for k, v in m["pairs"]["outcomes"].items()],
        "",
        "## Por dificuldade",
        "",
        "| Dificuldade | Acurácia | IC 95% | k/n |",
        "| --- | --- | --- | --- |",
        *[_linha_proporcao(k, v) for k, v in m["by_difficulty"].items()],
        "",
        "## Aderência e execução",
        "",
        f"- Respostas com retry: {f['responses_with_retry']}",
        f"- Falhas só de formato (status existe, mas fora do padrão do manifesto): {f['format_only_failures']}",
        f"- Gate de cobertura aplicado: {f['gate_applied']} (esperado 0 — senão o summary sintético está errado)",
        f"- Respostas com falha operacional: {m['operational']['responses_with_operational_error']}",
        f"- Respostas sem bloco de código no dataset: {m['operational']['responses_without_code']}",
        f"- Revisões executadas: {m['usage']['reviews']} · interações LLM: {m['usage']['llm_interactions']} · "
        f"tokens (in/out): {m['usage']['prompt_tokens']}/{m['usage']['completion_tokens']}",
        f"- Tempo total de revisão: {m['usage']['review_duration_s']:.1f}s · tempo total do run: "
        f"{relatorio.get('total_duration_s', 0.0):.1f}s",
        "",
        "## Por par",
        "",
        "| Par | Dificuldade | pos | neg | Desfecho |",
        "| --- | --- | --- | --- | --- |",
        *[
            f"| {r['pair_id']} | {r['difficulty']} | {r['pos']['verdict']} | {r['neg']['verdict']} | `{r['outcome']}` |"
            for r in relatorio["pairs"]
        ],
    ]
    return "\n".join(linhas) + "\n"


def _persistir_relatorio(relatorio: dict, run_dir: Path) -> tuple[Path, Path]:
    json_path = run_dir / "report.json"
    json_path.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = run_dir / "report.md"
    md_path.write_text(_render_markdown(relatorio), encoding="utf-8")
    return json_path, md_path


def _saida_utf8() -> None:
    """No Windows, saída redirecionada (arquivo, pipe, CI) usa cp1252 e quebra
    no primeiro `→` ou acento impresso — derrubando o run no meio. Também
    liga o line buffering: redirecionada, a saída só apareceria no fim do run."""
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _saida_utf8()
    args = _parse_args(argv)
    if not args.model:
        raise ValueError(
            "Erro: O parâmetro '--model' é obrigatório. "
            "A execução do benchmark não pode prosseguir sem a definição explícita do modelo."
        )
    if args.resume_dir is not None and not args.resume_dir.is_dir():
        raise FileNotFoundError(
            f"Erro: O diretório de retomada '--resume-dir' ({args.resume_dir}) não existe ou não é um diretório."
        )

    # O benchmark nunca escreve lições na memória de produção (mem0). O .env é
    # carregado com override=False, então este valor prevalece sobre ele.
    os.environ["AI4ES_MEMORY_ENABLED"] = "false"

    pares = ds.load_pairs(
        args.dataset_dir,
        split=args.split,
        limit=args.limit,
        seed=args.seed,
        max_per_question=args.max_per_question or None,
        pair_ids=args.pair_ids,
    )
    if not pares:
        raise ValueError("Nenhum par selecionado — confira --limit, --pair-ids e --split.")

    if args.resume_dir is not None:
        run_dir = args.resume_dir
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = args.output_dir / _construir_nome_run(args, timestamp, len(pares))

    # Pre-flight ANTES de persistir qualquer coisa: um run novo que falha na
    # conexão não deixa pasta vazia em results/ (que é versionado).
    run_novo = not run_dir.exists()
    bootstrap.prepare_environment(run_dir / "workspace", model=args.model)
    try:
        _testar_conexao_modelo(args.model)
    except SystemExit:
        if run_novo:
            shutil.rmtree(run_dir, ignore_errors=True)
        raise

    metadata = _validar_e_persistir_config(run_dir, args, _contexto_do_ambiente(args, pares))

    from benchmarks.coding_review.codejudgebench.metrics import compute_metrics

    t_inicio = time.time()
    registros, completo = asyncio.run(_executar(args, run_dir, pares))
    relatorio = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "complete": completo,
        "total_duration_s": round(time.time() - t_inicio, 2),
        "metadata": metadata,
        "metrics": compute_metrics(registros),
        "pairs": registros,
    }
    json_path, md_path = _persistir_relatorio(relatorio, run_dir)

    j = relatorio["metrics"]["judgment"]
    f = relatorio["metrics"]["format"]
    print("\n=== RESULTADO ===")
    print(f"Status: {'completo' if completo else 'INTERROMPIDO'}")
    print(f"Acurácia do julgamento: {_pct(j['accuracy']['value'])} ({j['accuracy']['k']}/{j['accuracy']['n']})")
    print(f"Resposta inválida (1ª tentativa): {_pct(f['invalid_first_attempt_rate']['value'])}")
    print(f"Relatório JSON: {json_path}")
    print(f"Resumo Markdown: {md_path}")
    return 0 if completo else 1


if __name__ == "__main__":
    raise SystemExit(main())
