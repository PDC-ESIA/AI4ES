"""Orquestrador CLI do benchmark HumanEval sobre o Coder Agent.

Uso típico (a partir da raiz do repositório):

    python -m benchmarks.coding_review.humaneval.run --limit 5 --samples 1

Ou diretamente:

    python benchmarks/coding_review/humaneval/run.py --limit 5

Fluxo:
1. `bootstrap.prepare_environment` fixa `sys.path`, `.env` e o workspace do coder
   ANTES de qualquer import do agente;
2. baixa/carrega o dataset (download dinâmico por padrão);
3. para cada problema × amostra: roda o coder (geração) e avalia com o teste
   canônico no `DirectSandbox` (grading);
4. calcula pass@k e persiste um relatório JSON + resumo Markdown.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

# Este arquivo pode ser executado como script (python benchmarks/coding_review/humaneval/run.py)
# ou como módulo (python -m benchmarks.coding_review.humaneval.run). O bloco abaixo garante que
# o import do pacote `benchmarks` funcione no modo script.
if __package__ in (None, ""):
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from benchmarks.coding_review.humaneval import bootstrap
from benchmarks.coding_review.humaneval.dataset import DEFAULT_DATASET_URL

_DEFAULT_OUTPUT = Path(__file__).resolve().parent / "results"
_DEFAULT_DATASET = Path(__file__).resolve().parent / "datasets" / "HumanEval.jsonl.gz"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="benchmarks.coding_review.humaneval.run",
        description="Executa o benchmark HumanEval usando o Coder Agent do AI4ES.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Máximo de problemas a executar (default: todos os 164).",
    )
    p.add_argument(
        "--task-ids",
        nargs="*",
        default=None,
        help="Filtra por task_id específicos (ex.: HumanEval/0 HumanEval_1).",
    )
    p.add_argument(
        "--samples",
        type=int,
        default=1,
        help="Amostras geradas por problema (n). Use >1 para pass@k (default: 1).",
    )
    p.add_argument(
        "--k",
        type=int,
        nargs="*",
        default=[1],
        help="Valores de k para pass@k (default: 1).",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout (s) por avaliação no sandbox (default: 30).",
    )
    p.add_argument(
        "--model",
        default=None,
        help="Modelo LLM a utilizar (obrigatório, ex.: github_copilot/gpt-4).",
    )
    p.add_argument(
        "--dataset-url",
        default=DEFAULT_DATASET_URL,
        help="URL de download do dataset HumanEval.",
    )
    p.add_argument(
        "--dataset-path",
        type=Path,
        default=_DEFAULT_DATASET,
        help="Caminho local do dataset (.jsonl.gz).",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help="Diretório-base dos relatórios de saída.",
    )
    p.add_argument(
        "--resume-dir",
        type=Path,
        default=None,
        help=(
            "Retoma um run existente: reutiliza o diretório informado, pula os "
            "problemas já concluídos (lidos de progress.jsonl) e completa o resto."
        ),
    )
    return p.parse_args(argv)


def _testar_conexao_modelo(model: str) -> None:
    """Pre-flight: chamada mínima ao modelo para validar credenciais/conexão.

    Envia um "ping" de 1 token antes de iniciar o benchmark. Em caso de falha,
    exibe o traceback COMPLETO (incl. erro interno da API via LiteLLM/HTTPX) e
    aborta com SystemExit(1) — fail-fast, evitando iniciar o run só para falhar
    na primeira tarefa. Deve ser chamado após `bootstrap.prepare_environment`
    (garante .env carregado e providers registrados no LLMRegistry).
    """
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
        print("Log de erro / traceback completo:")
        print("=" * 80)
        traceback.print_exc()
        print("=" * 80)
        print(
            "DICA: verifique as credenciais no ambiente ou no .env (ex.: "
            "OPENROUTER_API_KEY, credencial do GitHub Copilot) e a conectividade "
            "com a internet.\n"
        )
        raise SystemExit(1)


def _sanitizar_componente(valor: str) -> str:
    """Normaliza um trecho para uso seguro em nome de diretório.

    Substitui separadores de caminho e caracteres não amigáveis (ex.: barras
    do id do modelo `github_copilot/gpt-4`) por hífens, colapsa repetições e
    remove hífens nas bordas.
    """
    limpo = re.sub(r"[^0-9A-Za-z._-]+", "-", valor.strip())
    limpo = re.sub(r"-{2,}", "-", limpo).strip("-.")
    return limpo or "na"


def _construir_nome_run(args: argparse.Namespace, timestamp: str) -> str:
    """Monta um nome de diretório descritivo a partir dos parâmetros do run.

    Formato: ``run_<timestamp>_<modelo>_n<samples>_k<k>[_lim<limit>]``.
    O modelo é sanitizado para remover barras e caracteres inseguros.
    """
    modelo = _sanitizar_componente(args.model)
    ks = "-".join(str(k) for k in sorted(args.k)) if args.k else "1"
    partes = [
        f"run_{timestamp}",
        modelo,
        f"n{args.samples}",
        f"k{ks}",
    ]
    if args.limit is not None:
        partes.append(f"lim{args.limit}")
    return "_".join(partes)


def _carregar_progresso(progress_path: Path) -> dict[str, dict]:
    """Lê o checkpoint incremental (progress.jsonl) e devolve {task_id: detalhe}.

    Cada linha é o dicionário-detalhe de um problema já concluído. Linhas
    corrompidas (ex.: escrita truncada por um kill) são ignoradas com aviso.
    """
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
    """Anexa (e faz flush de) o detalhe de um problema ao checkpoint incremental."""
    with progress_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(detalhe, ensure_ascii=False) + "\n")
        fh.flush()


async def _executar(args: argparse.Namespace, run_dir: Path, model: str) -> dict:
    """Executa o loop principal do benchmark e devolve o relatório consolidado."""
    # Imports tardios: só após o bootstrap ter fixado o ambiente.
    from benchmarks.coding_review.humaneval import coder_runner, grading
    from benchmarks.coding_review.humaneval.dataset import load_problems
    from benchmarks.coding_review.humaneval.metrics import aggregate_pass_at_k

    problemas = load_problems(
        args.dataset_path,
        url=args.dataset_url,
        limit=args.limit,
        task_ids=args.task_ids,
    )

    # Checkpoint incremental: sobrevive a timeouts/kills e permite retomada.
    run_dir.mkdir(parents=True, exist_ok=True)
    progress_path = run_dir / "progress.jsonl"
    concluidos = _carregar_progresso(progress_path)
    if concluidos:
        print(
            f"[run] Retomando: {len(concluidos)} problema(s) já concluído(s), pulando-os."
        )
    print(
        f"[run] {len(problemas)} problema(s) a executar, {args.samples} amostra(s) cada."
    )

    detalhes: list[dict] = []
    per_problem: list[tuple[int, int]] = []

    for idx, problema in enumerate(problemas, start=1):
        # Retomada: reaproveita resultados já persistidos.
        if problema.task_id in concluidos:
            detalhe = concluidos[problema.task_id]
            detalhes.append(detalhe)
            per_problem.append((detalhe["n"], detalhe["correct"]))
            print(
                f"[run] ({idx}/{len(problemas)}) {problema.task_id}: "
                f"CACHE ({detalhe['correct']}/{detalhe['n']})"
            )
            continue

        corretas = 0
        amostras_info: list[dict] = []
        for amostra in range(args.samples):
            t0 = time.time()
            geracao = await coder_runner.run_coder(problema, model=model)

            # Telemetria de uso do LLM, coletada em qualquer desfecho da geração.
            telemetria = {
                "llm_interactions": geracao.llm_interactions,
                "prompt_tokens": geracao.prompt_tokens,
                "completion_tokens": geracao.completion_tokens,
            }

            if geracao.error:
                resultado = {
                    "sample": amostra,
                    "passed": False,
                    "reason": f"Falha de geração: {geracao.error}",
                    "files": geracao.files,
                    "duration_s": round(time.time() - t0, 2),
                    **telemetria,
                }
            elif not geracao.has_solution:
                resultado = {
                    "sample": amostra,
                    "passed": False,
                    "reason": (
                        "Coder não produziu arquivo com a função-alvo "
                        f"(`{problema.entry_point}`)."
                    ),
                    "files": geracao.files,
                    "duration_s": round(time.time() - t0, 2),
                    **telemetria,
                }
            else:
                grade = grading.grade_solution(
                    problema,
                    geracao.solution_dir,
                    geracao.solution_file,
                    timeout=args.timeout,
                )
                if grade.passed:
                    corretas += 1
                resultado = {
                    "sample": amostra,
                    "passed": grade.passed,
                    "reason": grade.reason,
                    "solution_file": str(
                        geracao.solution_file.relative_to(geracao.solution_dir)
                    ),
                    "files": geracao.files,
                    "exit_code": grade.exit_code,
                    "timed_out": grade.timed_out,
                    "stderr_tail": grade.stderr_tail,
                    "duration_s": round(time.time() - t0, 2),
                    **telemetria,
                }
            amostras_info.append(resultado)
            status = "PASS" if resultado["passed"] else "FAIL"
            print(
                f"[run] ({idx}/{len(problemas)}) {problema.task_id} "
                f"amostra {amostra + 1}/{args.samples}: {status} "
                f"({resultado['duration_s']}s)"
            )

        per_problem.append((args.samples, corretas))
        detalhe = {
            "task_id": problema.task_id,
            "entry_point": problema.entry_point,
            "n": args.samples,
            "correct": corretas,
            "samples": amostras_info,
        }
        detalhes.append(detalhe)
        # Checkpoint imediato: persiste o problema recém-concluído.
        _append_progresso(progress_path, detalhe)

    metricas = aggregate_pass_at_k(per_problem, args.k)

    # Agrega telemetria de uso do LLM sobre todas as amostras de todos os
    # problemas (inclui resultados reaproveitados do checkpoint, se presentes).
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_llm_interactions = 0
    for p in detalhes:
        for s in p.get("samples", []):
            total_prompt_tokens += s.get("prompt_tokens", 0) or 0
            total_completion_tokens += s.get("completion_tokens", 0) or 0
            total_llm_interactions += s.get("llm_interactions", 0) or 0

    usage_metrics = {
        "total_llm_interactions": total_llm_interactions,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_tokens": total_prompt_tokens + total_completion_tokens,
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "num_problems": len(problemas),
        "samples_per_problem": args.samples,
        "pass_at_k": {f"pass@{k}": round(v, 4) for k, v in metricas.items()},
        "usage_metrics": usage_metrics,
        "problems": detalhes,
    }


def _persistir_relatorio(relatorio: dict, run_dir: Path) -> tuple[Path, Path]:
    """Grava o relatório JSON e um resumo Markdown; devolve os dois caminhos."""
    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / "report.json"
    json_path.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    linhas = [
        "# Benchmark HumanEval — Coder Agent",
        "",
        f"- **Gerado em:** {relatorio['generated_at']}",
        f"- **Modelo:** {relatorio['model']}",
        f"- **Problemas:** {relatorio['num_problems']}",
        f"- **Amostras/problema:** {relatorio['samples_per_problem']}",
        "",
        "## Métricas",
        "",
    ]
    if relatorio["pass_at_k"]:
        for chave, valor in relatorio["pass_at_k"].items():
            linhas.append(f"- **{chave}:** {valor:.4f} ({valor * 100:.1f}%)")
    else:
        linhas.append("_Nenhuma métrica pass@k definível para a configuração usada._")

    usage = relatorio.get("usage_metrics", {})
    if usage:
        linhas += [
            "",
            "## Métricas de Execução",
            "",
            f"- **Tempo total de execução:** {usage.get('total_duration_s', 0.0):.2f}s",
            f"- **Total de interações com LLM:** {usage.get('total_llm_interactions', 0)}",
            f"- **Total de tokens de entrada (prompt):** {usage.get('total_prompt_tokens', 0)}",
            f"- **Total de tokens de saída (completion):** {usage.get('total_completion_tokens', 0)}",
            f"- **Total de tokens:** {usage.get('total_tokens', 0)}",
        ]

    linhas += [
        "",
        "## Por problema",
        "",
        "| Task | Entry point | Corretas/n |",
        "| ---- | ----------- | ---------- |",
    ]
    for p in relatorio["problems"]:
        linhas.append(
            f"| {p['task_id']} | `{p['entry_point']}` | {p['correct']}/{p['n']} |"
        )

    md_path = run_dir / "report.md"
    md_path.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return json_path, md_path


def _validar_e_persistir_config(run_dir: Path, args: argparse.Namespace) -> None:
    """Valida se os parâmetros atuais coincidem com os originais e persiste-os."""
    config_path = run_dir / "metadata.json"

    # Parâmetros atuais da execução
    params_atuais = {
        "model": args.model,
        "samples": args.samples,
        "k": sorted(args.k) if args.k else [1],
        "timeout": args.timeout,
    }

    if config_path.is_file():
        # Caso exista metadata.json, valida diretamente contra ele
        try:
            params_salvos = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"Erro ao ler metadata.json em {run_dir}: {exc}")

        # Comparação detalhada
        if params_salvos.get("model") != params_atuais["model"]:
            raise ValueError(
                f"Erro: O modelo informado ({params_atuais['model']}) difere do "
                f"modelo original da execução ({params_salvos.get('model')})."
            )
        if params_salvos.get("samples") != params_atuais["samples"]:
            raise ValueError(
                f"Erro: O parâmetro '--samples' ({params_atuais['samples']}) difere do "
                f"número de amostras original ({params_salvos.get('samples')})."
            )
        k_salvo = sorted(params_salvos.get("k", []))
        if k_salvo != params_atuais["k"]:
            raise ValueError(
                f"Erro: O parâmetro '--k' ({params_atuais['k']}) difere das "
                f"métricas pass@k originais ({k_salvo})."
            )
        if params_salvos.get("timeout") != params_atuais["timeout"]:
            raise ValueError(
                f"Erro: O parâmetro '--timeout' ({params_atuais['timeout']}) difere do "
                f"timeout original ({params_salvos.get('timeout')})."
            )
    else:
        # Backward compatibility / Migração retroativa: tenta validar lendo progress.jsonl ou report.json
        progress_path = run_dir / "progress.jsonl"
        report_path = run_dir / "report.json"

        # 1. Validar samples a partir do progress.jsonl
        if progress_path.is_file():
            try:
                linhas_split = progress_path.read_text(encoding="utf-8").splitlines()
                if linhas_split:
                    detalhe = json.loads(linhas_split[0])
                    samples_originais = detalhe.get("n")
                    if (
                        samples_originais is not None
                        and samples_originais != params_atuais["samples"]
                    ):
                        raise ValueError(
                            f"Erro: O parâmetro '--samples' ({params_atuais['samples']}) difere do "
                            f"número de amostras original ({samples_originais}) encontrado em progress.jsonl."
                        )
            except (json.JSONDecodeError, KeyError):
                pass

        # 2. Validar model e k a partir do report.json
        if report_path.is_file():
            try:
                relatorio_salvo = json.loads(report_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                relatorio_salvo = {}

            if relatorio_salvo:
                model_original = relatorio_salvo.get("model")
                if model_original and model_original != params_atuais["model"]:
                    raise ValueError(
                        f"Erro: O modelo informado ({params_atuais['model']}) difere do "
                        f"modelo original ({model_original}) encontrado em report.json."
                    )

                pass_at_k_salvo = relatorio_salvo.get("pass_at_k", {})
                if pass_at_k_salvo:
                    try:
                        k_salvo = sorted(
                            [
                                int(chave.replace("pass@", ""))
                                for chave in pass_at_k_salvo.keys()
                            ]
                        )
                    except (ValueError, TypeError, KeyError):
                        k_salvo = []
                    if k_salvo and k_salvo != params_atuais["k"]:
                        raise ValueError(
                            f"Erro: O parâmetro '--k' ({params_atuais['k']}) difere das "
                            f"métricas pass@k originais ({k_salvo}) encontradas em report.json."
                        )

        # Se passou na validação retroativa ou se é uma pasta nova, persiste o metadata.json
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
        run_dir = args.output_dir / _construir_nome_run(args, timestamp)

    # Valida parâmetros em caso de retomada e persiste metadata.json em qualquer cenário
    _validar_e_persistir_config(run_dir, args)

    workspace_dir = run_dir / "workspace"

    bootstrap.prepare_environment(workspace_dir, model=args.model)

    # Pre-flight: valida conexão/credenciais antes de iniciar o benchmark.
    _testar_conexao_modelo(args.model)

    t_start = time.time()
    relatorio = asyncio.run(_executar(args, run_dir, model=args.model))
    total_duration_s = round(time.time() - t_start, 2)
    relatorio.setdefault("usage_metrics", {})["total_duration_s"] = total_duration_s
    json_path, md_path = _persistir_relatorio(relatorio, run_dir)

    print("\n=== RESULTADO ===")
    if relatorio["pass_at_k"]:
        for chave, valor in relatorio["pass_at_k"].items():
            print(f"{chave}: {valor:.4f} ({valor * 100:.1f}%)")
    else:
        print("Nenhuma métrica pass@k definível para a configuração usada.")
    usage = relatorio.get("usage_metrics", {})
    if usage:
        print(
            f"Tempo total: {usage.get('total_duration_s', 0.0):.2f}s | "
            f"Interações LLM: {usage.get('total_llm_interactions', 0)} | "
            f"Tokens (in/out/total): {usage.get('total_prompt_tokens', 0)}/"
            f"{usage.get('total_completion_tokens', 0)}/{usage.get('total_tokens', 0)}"
        )
    print(f"Relatório JSON: {json_path}")
    print(f"Resumo Markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
