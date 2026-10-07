"""Orquestrador CLI do benchmark BigCodeBench (split complete) sobre o Coder Agent.

Uso típico (a partir da raiz do repositório):

    python -m benchmarks.coding_review.bigcodebench.run --model <m> --limit 50

Fluxo:
1. `bootstrap.prepare_environment` fixa `sys.path`, `.env` e o workspace do coder
   ANTES de qualquer import do agente;
2. carrega o dataset (download dinâmico) e sorteia `--limit` tarefas com `--seed`;
3. garante a imagem Docker do sandbox (build sob demanda);
4. (opcional) `--verify-canonical`: roda as soluções de referência no sandbox para
   provar que o ambiente executa as tarefas;
5. para cada tarefa: roda o coder (geração) e avalia com o teste oficial no
   container (grading), classificando a causa de cada falha;
6. persiste `report.json`, `report.md` e `metadata.json`, incluindo a comparação
   com o baseline do HumanEval (`--baseline`).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

# Permite executar como script ou como módulo (`python -m ...`).
if __package__ in (None, ""):
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from benchmarks.coding_review.bigcodebench import bootstrap
from benchmarks.coding_review.bigcodebench.categories import (
    GENERATION_ERROR,
    IMPORT_ERROR,
    MISSING_DEPENDENCY,
    NO_SOLUTION,
    PASSED,
)
from benchmarks.coding_review.bigcodebench.dataset import (
    DEFAULT_DATASET_URL,
    DEFAULT_HF_VERSION,
    DEFAULT_SEED,
)

_DEFAULT_OUTPUT = Path(__file__).resolve().parent / "results"
_DEFAULT_DATASET = (
    Path(__file__).resolve().parent
    / "datasets"
    / f"bigcodebench_{DEFAULT_HF_VERSION}.parquet"
)
_DEFAULT_TIMEOUT = 120


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="benchmarks.coding_review.bigcodebench.run",
        description=(
            "Executa o benchmark BigCodeBench (split complete) usando o Coder "
            "Agent do AI4ES, com testes oficiais num sandbox Docker."
        ),
    )
    p.add_argument("--model", default=None, help="Modelo LLM (obrigatório).")
    p.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Nº de tarefas sorteadas (default: 50; o dataset completo tem 1.140).",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Seed do sorteio das tarefas (default: {DEFAULT_SEED}).",
    )
    p.add_argument(
        "--task-ids",
        nargs="*",
        default=None,
        help="Tarefas específicas (ex.: BigCodeBench/0); ignora --limit/--seed.",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=_DEFAULT_TIMEOUT,
        help=f"Timeout (s) por avaliação no sandbox (default: {_DEFAULT_TIMEOUT}).",
    )
    p.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="report.json (ou diretório do run) do HumanEval, mesmo modelo, para comparação.",
    )
    p.add_argument(
        "--verify-canonical",
        action="store_true",
        help="Antes de gerar, roda as soluções de referência no sandbox (valida o ambiente).",
    )
    p.add_argument(
        "--image",
        default=None,
        help="Imagem Docker do sandbox (default: construída a partir de sandbox/Dockerfile).",
    )
    p.add_argument(
        "--rebuild-image",
        action="store_true",
        help="Força a reconstrução da imagem do sandbox.",
    )
    p.add_argument(
        "--allow-network",
        action="store_true",
        help="Liga a rede no container de avaliação (default: sem rede).",
    )
    p.add_argument("--dataset-url", default=DEFAULT_DATASET_URL)
    p.add_argument("--dataset-path", type=Path, default=_DEFAULT_DATASET)
    p.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT)
    p.add_argument(
        "--resume-dir",
        type=Path,
        default=None,
        help="Retoma um run existente (pula tarefas já concluídas em progress.jsonl).",
    )
    return p.parse_args(argv)


def _testar_conexao_modelo(model: str) -> None:
    """Pre-flight: chamada mínima ao modelo para validar credenciais/conexão."""
    import traceback

    import litellm

    print(f"\n[PRE-FLIGHT] Testando conexão com o modelo '{model}'...")
    try:
        litellm.completion(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            timeout=20,
        )
        print("[PRE-FLIGHT] Conexão estabelecida com sucesso!\n")
    except Exception:  # noqa: BLE001 — qualquer falha aborta o benchmark
        print("\n" + "=" * 80)
        print(f"[PRE-FLIGHT ERROR] Falha ao conectar ao modelo '{model}'.")
        print("=" * 80)
        traceback.print_exc()
        print("=" * 80)
        raise SystemExit(1)


def _sanitizar_componente(valor: str) -> str:
    """Normaliza um trecho para uso seguro em nome de diretório."""
    limpo = re.sub(r"[^0-9A-Za-z._-]+", "-", valor.strip())
    limpo = re.sub(r"-{2,}", "-", limpo).strip("-.")
    return limpo or "na"


def _construir_nome_run(model: str, n: int, timestamp: str) -> str:
    """Nome do diretório do run: ``run_<timestamp>_<modelo>_n<N>``."""
    return f"run_{timestamp}_{_sanitizar_componente(model)}_n{n}"


def _carregar_progresso(progress_path: Path) -> dict[str, dict]:
    """Lê o checkpoint incremental (progress.jsonl) → {task_id: detalhe}."""
    concluidos: dict[str, dict] = {}
    if not progress_path.is_file():
        return concluidos
    for linha in progress_path.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha:
            continue
        try:
            detalhe = json.loads(linha)
            concluidos[detalhe["task_id"]] = detalhe
        except (json.JSONDecodeError, KeyError):
            print(f"[run] Aviso: linha inválida em {progress_path.name}, ignorada.")
    return concluidos


def _append_progresso(progress_path: Path, detalhe: dict) -> None:
    """Anexa (com flush) o detalhe de uma tarefa ao checkpoint incremental."""
    with progress_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(detalhe, ensure_ascii=False) + "\n")
        fh.flush()


def _verificar_canonicas(problemas, image: str, timeout: int, network_mode) -> dict:
    """Roda as soluções de referência no sandbox e resume o resultado.

    Aborta (SystemExit) se alguma falhar por dependência/import: o ambiente não
    estaria apto a avaliar o modelo. Falhas de teste isoladas (ex.: testes
    sensíveis a rede) são só registradas.
    """
    from benchmarks.coding_review.bigcodebench import grading

    print(f"[verify] Validando {len(problemas)} solução(ões) canônica(s) no sandbox…")
    falhas: dict[str, str] = {}
    for problema in problemas:
        r = grading.grade_canonical(
            problema, timeout=timeout, image=image, network_mode=network_mode
        )
        status = "OK" if r.passed else f"FALHOU ({r.category})"
        print(f"[verify] {problema.task_id}: {status}")
        if not r.passed:
            falhas[problema.task_id] = r.category

    ambiente = [t for t, c in falhas.items() if c in (MISSING_DEPENDENCY, IMPORT_ERROR)]
    if ambiente:
        raise SystemExit(
            "[verify] Ambiente inapto: a solução canônica falhou por dependência em "
            f"{ambiente}. Reconstrua a imagem (--rebuild-image) ou ajuste o Dockerfile."
        )
    return {"checked": len(problemas), "failed": falhas}


def _resultado_base(problema, t0: float, geracao) -> dict:
    """Campos comuns a qualquer desfecho (identificação + telemetria do LLM)."""
    return {
        "task_id": problema.task_id,
        "entry_point": problema.entry_point,
        "libs": list(problema.libs),
        "files": geracao.files,
        "duration_s": round(time.time() - t0, 2),
        "llm_interactions": geracao.llm_interactions,
        "prompt_tokens": geracao.prompt_tokens,
        "completion_tokens": geracao.completion_tokens,
    }


async def _executar(args: argparse.Namespace, run_dir: Path, model: str) -> dict:
    """Loop principal do benchmark; devolve o relatório consolidado."""
    # Imports tardios: só após o bootstrap ter fixado o ambiente.
    from benchmarks.coding_review.bigcodebench import coder_runner, grading, metrics
    from benchmarks.coding_review.bigcodebench.dataset import load_problems
    from benchmarks.coding_review.bigcodebench.sandbox_image import (
        IMAGE_TAG,
        ensure_image,
    )

    problemas = load_problems(
        args.dataset_path,
        url=args.dataset_url,
        limit=args.limit,
        seed=args.seed,
        task_ids=args.task_ids,
    )
    image = ensure_image(args.image or IMAGE_TAG, rebuild=args.rebuild_image)
    network_mode = None if args.allow_network else "none"

    run_dir.mkdir(parents=True, exist_ok=True)
    canonical_check = None
    if args.verify_canonical:
        canonical_check = _verificar_canonicas(
            problemas, image, args.timeout, network_mode
        )

    progress_path = run_dir / "progress.jsonl"
    concluidos = _carregar_progresso(progress_path)
    if concluidos:
        print(f"[run] Retomando: {len(concluidos)} tarefa(s) já concluída(s).")
    print(f"[run] {len(problemas)} tarefa(s) a executar (seed={args.seed}).")

    resultados: list[dict] = []
    for idx, problema in enumerate(problemas, start=1):
        if problema.task_id in concluidos:
            resultados.append(concluidos[problema.task_id])
            print(f"[run] ({idx}/{len(problemas)}) {problema.task_id}: CACHE")
            continue

        t0 = time.time()
        geracao = await coder_runner.run_coder(problema, model=model)
        resultado = _resultado_base(problema, t0, geracao)

        if geracao.error:
            resultado.update(
                passed=False,
                category=GENERATION_ERROR,
                reason=f"Falha de geração: {geracao.error}",
            )
        elif not geracao.has_solution:
            resultado.update(
                passed=False,
                category=NO_SOLUTION,
                reason=(
                    "Coder não produziu arquivo com a função-alvo "
                    f"(`{problema.entry_point}`)."
                ),
            )
        else:
            grade = grading.grade_solution(
                problema,
                geracao.solution_dir,
                geracao.solution_file,
                timeout=args.timeout,
                image=image,
                network_mode=network_mode,
            )
            resultado.update(
                passed=grade.passed,
                category=grade.category,
                reason=grade.reason,
                solution_file=str(
                    geracao.solution_file.relative_to(geracao.solution_dir)
                ),
                exit_code=grade.exit_code,
                timed_out=grade.timed_out,
                stderr_tail=grade.stderr_tail,
            )
        resultado["duration_s"] = round(time.time() - t0, 2)
        resultados.append(resultado)
        _append_progresso(progress_path, resultado)
        status = "PASS" if resultado["passed"] else f"FAIL[{resultado['category']}]"
        print(
            f"[run] ({idx}/{len(problemas)}) {problema.task_id}: {status} "
            f"({resultado['duration_s']}s)"
        )

    pass1 = metrics.pass_at_1(resultados)
    relatorio = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark": "bigcodebench",
        "split": "complete",
        "dataset_version": DEFAULT_HF_VERSION,
        "model": model,
        "seed": args.seed,
        "num_problems": len(problemas),
        "pass_at_k": {"pass@1": round(pass1, 4)},
        "failures": metrics.aggregate_failures(resultados),
        "usage_metrics": {
            "total_llm_interactions": sum(
                r.get("llm_interactions", 0) for r in resultados
            ),
            "total_prompt_tokens": sum(r.get("prompt_tokens", 0) for r in resultados),
            "total_completion_tokens": sum(
                r.get("completion_tokens", 0) for r in resultados
            ),
        },
        "sandbox": {
            "kind": "docker",
            "image": image,
            "network": "enabled" if args.allow_network else "none",
        },
        "problems": resultados,
    }
    u = relatorio["usage_metrics"]
    u["total_tokens"] = u["total_prompt_tokens"] + u["total_completion_tokens"]
    if canonical_check is not None:
        relatorio["canonical_check"] = canonical_check

    if args.baseline is not None:
        baseline = metrics.load_baseline(args.baseline)
        if baseline is None:
            print(f"[run] Aviso: baseline não encontrado/inválido em {args.baseline}.")
        else:
            relatorio["baseline_comparison"] = metrics.compare_with_baseline(
                pass1, baseline
            )
    return relatorio


def _persistir_relatorio(relatorio: dict, run_dir: Path) -> tuple[Path, Path]:
    """Grava o relatório JSON e o resumo Markdown; devolve os dois caminhos."""
    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / "report.json"
    json_path.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    n = relatorio["num_problems"]
    p1 = relatorio["pass_at_k"]["pass@1"]
    falhas = relatorio["failures"]
    linhas = [
        "# Benchmark BigCodeBench (complete) — Coder Agent",
        "",
        f"- **Gerado em:** {relatorio['generated_at']}",
        f"- **Modelo:** {relatorio['model']}",
        f"- **Dataset:** bigcode/bigcodebench {relatorio['dataset_version']} (split complete)",
        f"- **Tarefas:** {n} (seed {relatorio['seed']})",
        f"- **Sandbox:** Docker `{relatorio['sandbox']['image']}` "
        f"(rede: {relatorio['sandbox']['network']})",
        "",
        "## 1. Pass@1",
        "",
        f"- **pass@1:** {p1:.4f} ({p1 * 100:.1f}%) — "
        f"{round(p1 * n)}/{n} tarefas aprovadas nos testes oficiais",
        "",
        "## 2. Falhas por import/dependência × lógica",
        "",
    ]
    total = falhas["total_failures"]
    if total == 0:
        linhas.append("_Nenhuma reprovação._")
    else:
        g = falhas["by_group"]
        linhas += [
            "| Grupo | Reprovações | % das reprovações |",
            "| ----- | ----------- | ----------------- |",
            f"| Biblioteca (ausente / import / API) | {g['library']} | {g['library'] / total:.0%} |",
            f"| Lógica (asserção / erro de execução) | {g['logic']} | {g['logic'] / total:.0%} |",
            f"| Outras (sintaxe / timeout / sem solução / geração) | {g['other']} | {g['other'] / total:.0%} |",
            "",
            "| Categoria | Reprovações |",
            "| --------- | ----------- |",
        ]
        for cat, qtd in falhas["by_category"].items():
            linhas.append(f"| `{cat}` | {qtd} |")

    linhas += ["", "## 3. Comparação com o HumanEval (mesmo modelo)", ""]
    comp = relatorio.get("baseline_comparison")
    if comp is None:
        linhas.append(
            "_Baseline não informado — rode o HumanEval com o mesmo modelo e passe "
            "`--baseline <report.json>`._"
        )
    else:
        linhas += [
            "| Benchmark | Tarefas | pass@1 |",
            "| --------- | ------- | ------ |",
            f"| HumanEval | {comp['humaneval_num_problems']} | "
            f"{comp['humaneval_pass_at_1'] * 100:.1f}% |",
            f"| BigCodeBench (complete) | {n} | {comp['bigcodebench_pass_at_1'] * 100:.1f}% |",
            "",
            f"- **Variação:** {comp['delta_pp']:+.1f} p.p. "
            f"(queda relativa de {comp['relative_drop_pct']}%)",
        ]
        if comp.get("humaneval_model") != relatorio["model"]:
            linhas.append(
                f"- ⚠️ Modelos diferentes: HumanEval usou `{comp['humaneval_model']}`."
            )

    usage = relatorio["usage_metrics"]
    linhas += [
        "",
        "## Métricas de execução",
        "",
        f"- **Tempo total:** {usage.get('total_duration_s', 0.0):.2f}s",
        f"- **Interações com LLM:** {usage['total_llm_interactions']}",
        f"- **Tokens (entrada/saída/total):** {usage['total_prompt_tokens']}/"
        f"{usage['total_completion_tokens']}/{usage['total_tokens']}",
    ]
    cc = relatorio.get("canonical_check")
    if cc is not None:
        linhas.append(
            f"- **Soluções canônicas validadas no sandbox:** {cc['checked'] - len(cc['failed'])}"
            f"/{cc['checked']}"
        )

    linhas += [
        "",
        "## Por tarefa",
        "",
        "| Task | Bibliotecas | Resultado | Categoria |",
        "| ---- | ----------- | --------- | --------- |",
    ]
    for p in relatorio["problems"]:
        libs = ", ".join(p.get("libs", [])) or "—"
        resultado = "PASS" if p["passed"] else "FAIL"
        cat = "—" if p["category"] == PASSED else f"`{p['category']}`"
        linhas.append(f"| {p['task_id']} | {libs} | {resultado} | {cat} |")

    md_path = run_dir / "report.md"
    md_path.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return json_path, md_path


def _validar_e_persistir_config(run_dir: Path, args: argparse.Namespace) -> None:
    """Persiste `metadata.json` e, em retomada, valida que os parâmetros coincidem."""
    config_path = run_dir / "metadata.json"
    params_atuais = {
        "model": args.model,
        "limit": args.limit,
        "seed": args.seed,
        "task_ids": sorted(args.task_ids) if args.task_ids else None,
        "timeout": args.timeout,
        "dataset_version": DEFAULT_HF_VERSION,
        "allow_network": bool(args.allow_network),
    }

    if config_path.is_file():
        try:
            salvos = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"Erro ao ler metadata.json em {run_dir}: {exc}")
        for chave, atual in params_atuais.items():
            if salvos.get(chave) != atual:
                raise ValueError(
                    f"Erro: o parâmetro '{chave}' ({atual!r}) difere do valor "
                    f"original da execução ({salvos.get(chave)!r})."
                )
        return

    run_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(params_atuais, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not args.model:
        raise ValueError(
            "Erro: O parâmetro '--model' é obrigatório. "
            "A execução do benchmark não pode prosseguir sem a definição explícita do modelo."
        )

    if args.resume_dir is not None:
        run_dir = args.resume_dir
        if not run_dir.is_dir():
            raise FileNotFoundError(
                f"Erro: O diretório de retomada '--resume-dir' ({run_dir}) não existe ou não é um diretório."
            )
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        n = len(args.task_ids) if args.task_ids else args.limit
        run_dir = args.output_dir / _construir_nome_run(args.model, n, timestamp)

    _validar_e_persistir_config(run_dir, args)

    bootstrap.prepare_environment(run_dir / "workspace", model=args.model)
    _testar_conexao_modelo(args.model)

    t_start = time.time()
    relatorio = asyncio.run(_executar(args, run_dir, model=args.model))
    relatorio["usage_metrics"]["total_duration_s"] = round(time.time() - t_start, 2)
    json_path, md_path = _persistir_relatorio(relatorio, run_dir)

    print("\n=== RESULTADO ===")
    print(f"pass@1: {relatorio['pass_at_k']['pass@1'] * 100:.1f}%")
    print(f"Falhas: {relatorio['failures']['by_group']}")
    comp = relatorio.get("baseline_comparison")
    if comp:
        print(f"Δ vs HumanEval: {comp['delta_pp']:+.1f} p.p.")
    print(f"Relatório JSON: {json_path}")
    print(f"Resumo Markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
