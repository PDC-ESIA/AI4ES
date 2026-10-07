"""Orquestrador CLI do benchmark SlopCodeBench sobre o Coder Agent.

Uso típico (a partir da raiz do repositório):

    python -m benchmarks.coding_review.slopcodebench.run --model <m> --limit 10

Fluxo:
1. `bootstrap.prepare_environment` fixa `sys.path`, `.env` e o workspace do coder
   ANTES de qualquer import do agente;
2. sorteia o subset de problemas (seed fixa);
3. para cada problema, percorre os checkpoints EM ORDEM sobre o mesmo
   workspace: roda o coder (geração), salva o snapshot e avalia com a suíte
   oculta oficial (grading). Segue a pass policy oficial `any`, que nunca
   interrompe por resultado de teste: a trajetória do problema só para se o
   coder falhar (como o runner oficial ao erro do agente);
4. consolida os checkpoints com as funções oficiais (`checkpoint_results.jsonl`)
   e persiste um relatório JSON + resumo Markdown com as três métricas.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Este arquivo pode ser executado como script ou como módulo. O bloco abaixo
# garante que o import do pacote `benchmarks` funcione no modo script.
if __package__ in (None, ""):
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from benchmarks.coding_review.slopcodebench import bootstrap
from benchmarks.coding_review.slopcodebench.dataset import DEFAULT_SEED

_DEFAULT_OUTPUT = Path(__file__).resolve().parent / "results"
# Limite de relógio por checkpoint usado no paper (seção 3, "Setup").
_DEFAULT_CHECKPOINT_TIMEOUT_S = 2 * 60 * 60
_CODER_PROMPT = (
    bootstrap.adk_dir() / "src/agents/workflow_coding_review/coder/prompt.py"
)
# Parâmetros que precisam coincidir para retomar um run (Resume Guard).
_PARAMS_VALIDADOS = ("model", "limit", "seed", "problems", "checkpoint_timeout_s")
# Proveniência que também precisa coincidir na retomada.
_PROVENIENCIA_VALIDADA = (
    "coder_prompt_sha256",
    "slop_code_bench",
    "scb_problems_commit",
    "scb_check_version",
)
# Quando o LLM fica indisponível (cota, timeout, conexão), o checkpoint é
# refeito do zero após uma espera, sem registrar a tentativa que falhou. Dois
# limites contêm o gasto de créditos: tentativas por checkpoint e novas
# tentativas no run inteiro. Esgotado qualquer um, o run é interrompido.
_TENTATIVAS_POR_CHECKPOINT = 3  # a original + 2 novas
_NOVAS_TENTATIVAS_NO_RUN = 5
_ESPERAS_ENTRE_TENTATIVAS_S = (5 * 60, 10 * 60)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="benchmarks.coding_review.slopcodebench.run",
        description="Executa o benchmark SlopCodeBench usando o Coder Agent do AI4ES.",
    )
    p.add_argument(
        "--model",
        default=None,
        help="Modelo LLM a utilizar (obrigatório, ex.: github_copilot/gpt-4).",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Nº de problemas sorteados do catálogo (default: todos os 36).",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Seed do sorteio do subset (default: {DEFAULT_SEED}).",
    )
    p.add_argument(
        "--problems",
        nargs="*",
        default=None,
        help="Roda exatamente estes problemas (ignora --limit/--seed no sorteio).",
    )
    p.add_argument(
        "--problems-path",
        type=Path,
        default=None,
        help=(
            "Checkout local do catálogo scb-problems (default: $SCBENCH_PROBLEMS_PATH; "
            "sem ambos, baixa o commit fixado para datasets/)."
        ),
    )
    p.add_argument(
        "--checkpoint-timeout",
        type=int,
        default=_DEFAULT_CHECKPOINT_TIMEOUT_S,
        help="Limite de relógio (s) do coder por checkpoint (default: 7200, como no paper).",
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
            "checkpoints já concluídos (lidos de progress.jsonl) e completa o resto."
        ),
    )
    return p.parse_args(argv)


def _testar_conexao_modelo(model: str) -> None:
    """Pre-flight: chamada mínima ao modelo para validar credenciais/conexão.

    Mesma lógica do benchmark HumanEval: em caso de falha, exibe o traceback
    completo e aborta com SystemExit(1) antes de iniciar o run.
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


def _testar_docker() -> None:
    """Pre-flight: o avaliador oficial roda a suíte oculta em container Docker."""
    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"[PRE-FLIGHT ERROR] Docker indisponível: {exc}")
        raise SystemExit(1)


def _testar_harness() -> None:
    """Pre-flight: instala o harness oficial se preciso e valida o ambiente oficial."""
    from benchmarks.coding_review.slopcodebench import grading

    try:
        grading.check_harness()
    except Exception as exc:  # noqa: BLE001 — download, uv sync ou import do harness
        print(f"[PRE-FLIGHT ERROR] Harness do SlopCodeBench indisponível:\n{exc}")
        raise SystemExit(1)


def _comando_de_retomada(args: argparse.Namespace, run_dir: Path) -> str:
    """Comando que retoma o run com os mesmos parâmetros validados pelo Resume Guard."""
    partes = [
        "python -m benchmarks.coding_review.slopcodebench.run",
        f"--model {args.model}",
        f"--resume-dir {run_dir}",
    ]
    if args.problems:
        partes.append("--problems " + " ".join(args.problems))
    if args.limit is not None:
        partes.append(f"--limit {args.limit}")
    if args.seed != DEFAULT_SEED:
        partes.append(f"--seed {args.seed}")
    if args.checkpoint_timeout != _DEFAULT_CHECKPOINT_TIMEOUT_S:
        partes.append(f"--checkpoint-timeout {args.checkpoint_timeout}")
    if args.problems_path is not None:
        partes.append(f"--problems-path {args.problems_path}")
    return " ".join(partes)


def _sanitizar_componente(valor: str) -> str:
    """Normaliza um trecho para uso seguro em nome de diretório."""
    limpo = re.sub(r"[^0-9A-Za-z._-]+", "-", valor.strip())
    limpo = re.sub(r"-{2,}", "-", limpo).strip("-.")
    return limpo or "na"


def _construir_nome_run(args: argparse.Namespace, timestamp: str, n: int) -> str:
    """Nome do diretório do run: ``run_<timestamp>_<modelo>_n<N>``."""
    return f"run_{timestamp}_{_sanitizar_componente(args.model)}_n{n}"


def _carregar_progresso(progress_path: Path) -> dict[tuple[str, str], dict]:
    """Lê o checkpoint incremental e devolve {(problema, checkpoint): detalhe}.

    Checkpoints cuja AVALIAÇÃO falhou (`grading_error`) não contam como
    concluídos: a retomada os refaz, como o harness oficial faz com checkpoints
    com erro (`resume.py`, `HAD_ERROR` → inválido → reexecuta).
    """
    concluidos: dict[tuple[str, str], dict] = {}
    if not progress_path.is_file():
        return concluidos
    refazer = 0
    for linha in progress_path.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha:
            continue
        try:
            detalhe = json.loads(linha)
            chave = (detalhe["problem"], detalhe["checkpoint"])
        except json.JSONDecodeError, KeyError:
            print(f"[run] Aviso: linha inválida em {progress_path.name}, ignorada.")
            continue
        if detalhe.get("grading_error"):
            refazer += 1
            continue
        concluidos[chave] = detalhe
    if refazer:
        print(f"[run] {refazer} checkpoint(s) com falha de avaliação serão refeitos.")
    return concluidos


def _append_progresso(progress_path: Path, detalhe: dict) -> None:
    """Anexa (e faz flush de) o detalhe de um checkpoint ao checkpoint incremental."""
    with progress_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(detalhe, ensure_ascii=False) + "\n")
        fh.flush()


def _estados_dos_checkpoints(
    problemas: list, detalhes: list[dict]
) -> dict[str, dict[str, str]]:
    """Estado de cada checkpoint, com a mesma regra de `reporting.save_results`.

    ``error`` se o coder falhou (ou a avaliação não pôde rodar), ``ran`` se o
    checkpoint foi executado e ``skipped`` se não chegou a rodar (early stop).
    """
    por_chave = {(d["problem"], d["checkpoint"]): d for d in detalhes}
    estados: dict[str, dict[str, str]] = {}
    for problema in problemas:
        estados[problema.name] = {}
        for checkpoint in problema.checkpoints:
            detalhe = por_chave.get((problema.name, checkpoint))
            if detalhe is None:
                estado = "skipped"
            elif detalhe.get("coder_error") or detalhe.get("grading_error"):
                estado = "error"
            else:
                estado = "ran"
            estados[problema.name][checkpoint] = estado
    return estados


def _interrompe_trajetoria(detalhe: dict) -> bool:
    """Early stop como no runner oficial: só o erro do coder para a trajetória.

    `passed_policy` não entra: com a política padrão `any` ele só fica falso
    quando a AVALIAÇÃO falha (ver `PassPolicy.check` no harness), e falha do
    avaliador não é erro do agente — o checkpoint fica como `error`, o problema
    segue, e a retomada o refaz (ver `_carregar_progresso`).
    """
    return bool(detalhe.get("coder_error"))


@dataclass
class _OrcamentoDeTentativas:
    """Novas tentativas ainda permitidas no run inteiro (LLM indisponível)."""

    restantes: int = _NOVAS_TENTATIVAS_NO_RUN


async def _executar_problema(
    problema,
    args: argparse.Namespace,
    scb_dir: Path,
    progress_path: Path,
    concluidos: dict[tuple[str, str], dict],
    orcamento: _OrcamentoDeTentativas | None = None,
) -> list[dict]:
    """Percorre os checkpoints de um problema e devolve o detalhe de cada um."""
    from benchmarks.coding_review.slopcodebench import coder_runner, contract, grading

    if orcamento is None:
        orcamento = _OrcamentoDeTentativas()
    problem_dir = scb_dir / problema.name
    detalhes: list[dict] = []

    for idx, checkpoint in enumerate(problema.checkpoints):
        rotulo = f"{problema.name}/{checkpoint} ({idx + 1}/{problema.num_checkpoints})"
        save_dir = grading.checkpoint_output_dir(problema, problem_dir, checkpoint)
        snapshot_dir = save_dir / grading.SNAPSHOT_DIR_NAME

        # Retomada: reaproveita o checkpoint já concluído.
        if (problema.name, checkpoint) in concluidos:
            detalhe = concluidos[(problema.name, checkpoint)]
            detalhes.append(detalhe)
            print(f"[run] {rotulo}: CACHE")
            if _interrompe_trajetoria(detalhe):
                break
            continue

        if idx > 0:
            anterior = grading.checkpoint_output_dir(
                problema, problem_dir, problema.checkpoints[idx - 1]
            )

        def _preparar_workspace() -> None:
            # O coder parte exatamente do snapshot anterior (ou do zero no 1º
            # checkpoint) — inclusive após uma retomada ou nova tentativa.
            if idx == 0:
                coder_runner.iniciar_problema()
            else:
                coder_runner.restaurar_de_snapshot(anterior / grading.SNAPSHOT_DIR_NAME)

        primeiro = idx == 0
        prompt, entry_file = grading.render_prompt(
            problema, checkpoint, is_first_checkpoint=primeiro
        )
        (save_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        contrato = contract.build_task_contract(
            problema, checkpoint, prompt, entry_file
        )
        mensagem = contract.build_coder_message(checkpoint, prompt, entry_file)

        tentativa = 1
        while True:
            _preparar_workspace()
            inicio = datetime.now()
            t0 = time.time()
            try:
                geracao = await coder_runner.run_coder(
                    mensagem,
                    contrato,
                    primeiro_checkpoint=primeiro,
                    model=args.model,
                    timeout_s=args.checkpoint_timeout,
                )
                break
            except coder_runner.LlmIndisponivel as exc:
                # Nada desta tentativa é registrado. Nova tentativa do zero,
                # dentro dos dois limites; esgotados, o run é interrompido
                # (ver `main`) para ser retomado com --resume-dir.
                if tentativa >= _TENTATIVAS_POR_CHECKPOINT or orcamento.restantes <= 0:
                    raise
                espera = _ESPERAS_ENTRE_TENTATIVAS_S[
                    min(tentativa - 1, len(_ESPERAS_ENTRE_TENTATIVAS_S) - 1)
                ]
                orcamento.restantes -= 1
                tentativa += 1
                print(
                    f"[run] {rotulo}: LLM indisponível ({exc}). Nova tentativa "
                    f"{tentativa}/{_TENTATIVAS_POR_CHECKPOINT} em {espera // 60} min "
                    f"({orcamento.restantes} restante(s) no run)."
                )
                await asyncio.sleep(espera)
        fim = datetime.now()
        duracao_coder = round(time.time() - t0, 2)

        coder_runner.salvar_snapshot(snapshot_dir)
        grading.write_inference_result(
            save_dir,
            started=inicio,
            completed=fim,
            prompt_tokens=geracao.prompt_tokens,
            completion_tokens=geracao.completion_tokens,
            cached_tokens=geracao.cached_tokens,
            reasoning_tokens=geracao.reasoning_tokens,
            steps=geracao.tool_calls,
            had_error=geracao.error is not None,
            error_message=geracao.error,
        )

        if geracao.error:
            grade = grading.GradeResult(passed_policy=False)
        else:
            grade = grading.grade_checkpoint(problema, checkpoint, save_dir)

        detalhe = {
            "problem": problema.name,
            "checkpoint": checkpoint,
            "passed_policy": grade.passed_policy,
            "pass_counts": grade.pass_counts,
            "total_counts": grade.total_counts,
            "grading_error": grade.error,
            "coder_error": geracao.error,
            "coder_timed_out": geracao.timed_out,
            "files": len(geracao.files),
            "coder_duration_s": duracao_coder,
            "llm_interactions": geracao.llm_interactions,
            "tool_calls": geracao.tool_calls,
            "prompt_tokens": geracao.prompt_tokens,
            "completion_tokens": geracao.completion_tokens,
            "cached_tokens": geracao.cached_tokens,
            "reasoning_tokens": geracao.reasoning_tokens,
        }
        detalhes.append(detalhe)
        _append_progresso(progress_path, detalhe)

        passou = sum(grade.pass_counts.values())
        total = sum(grade.total_counts.values())
        if geracao.error:
            status = "ERRO DO CODER"
        elif grade.error:
            status = "FALHA NA AVALIAÇÃO"
        else:
            status = f"{passou}/{total} testes"
        print(f"[run] {rotulo}: {status} (coder {duracao_coder}s)")
        if grade.error:
            print(
                f"[run] {rotulo}: a avaliação falhou ({grade.error}). O checkpoint "
                "fica como `error`, o problema segue, e a retomada (--resume-dir) "
                "o refaz."
            )

        if _interrompe_trajetoria(detalhe):
            print(f"[run] {problema.name}: trajetória interrompida (erro do coder).")
            break

    return detalhes


async def _executar(args: argparse.Namespace, run_dir: Path, problemas: list) -> dict:
    """Executa o loop principal do benchmark e devolve o relatório consolidado."""
    from benchmarks.coding_review.slopcodebench import coder_runner, grading
    from benchmarks.coding_review.slopcodebench.metrics import (
        aggregate,
        regression_breaks,
    )

    scb_dir = run_dir / "workspace" / "scb"
    scb_dir.mkdir(parents=True, exist_ok=True)
    progress_path = run_dir / "progress.jsonl"
    concluidos = _carregar_progresso(progress_path)
    if concluidos:
        print(f"[run] Retomando: {len(concluidos)} checkpoint(s) já concluído(s).")
    print(
        f"[run] {len(problemas)} problema(s), "
        f"{sum(p.num_checkpoints for p in problemas)} checkpoint(s) previstos."
    )

    detalhes: list[dict] = []
    orcamento = _OrcamentoDeTentativas()  # compartilhado entre os problemas
    for idx, problema in enumerate(problemas, start=1):
        print(f"\n[run] ({idx}/{len(problemas)}) problema {problema.name}")
        try:
            detalhes += await _executar_problema(
                problema, args, scb_dir, progress_path, concluidos, orcamento
            )
        except coder_runner.LlmIndisponivel:
            raise  # interrompe o run inteiro; ver `main`
        except Exception as exc:  # noqa: BLE001 — interrompe para retomada segura
            # Seguir adiante publicaria um relatório incompleto como se fosse
            # resultado: os checkpoints já feitos deste problema sumiriam de
            # `detalhes` e virariam `skipped`. O progresso fica no
            # progress.jsonl, e `--resume-dir` continua daqui.
            print(
                f"[run] {problema.name}: falha inesperada ({type(exc).__name__}: {exc})"
            )
            raise

    # Consolidação oficial: uma linha por checkpoint avaliado.
    rows = grading.build_checkpoint_results(
        scb_dir,
        problemas,
        run_dir / grading.CHECKPOINT_RESULTS_FILENAME,
        _estados_dos_checkpoints(problemas, detalhes),
    )

    usage = {
        chave: sum(d.get(chave, 0) or 0 for d in detalhes)
        for chave in (
            "llm_interactions",
            "tool_calls",
            "prompt_tokens",
            "completion_tokens",
            "cached_tokens",
            "reasoning_tokens",
            "coder_duration_s",
        )
    }

    metrics = aggregate(
        rows,
        problemas,
        grading.progress_bins,
        regression_breaks(scb_dir, problemas),
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "seed": args.seed,
        "problems": [
            {"name": p.name, "checkpoints": p.num_checkpoints} for p in problemas
        ],
        "incomplete": _pendencias(detalhes, metrics),
        "metrics": metrics,
        "usage_metrics": usage,
        "checkpoints": detalhes,
    }


def _pendencias(detalhes: list[dict], metrics: dict) -> list[str]:
    """Motivos pelos quais o relatório NÃO é um resultado final (vazio = completo).

    Checkpoints com falha de avaliação ainda serão refeitos na retomada, e um
    run sem nenhum checkpoint rodado não diz nada sobre o modelo: publicar
    qualquer um dos dois como resultado confundiria "avaliador falhou" com
    "modelo ruim".
    """
    motivos = [
        f"{d['problem']}/{d['checkpoint']}: falha na avaliação (refazer com --resume-dir)"
        for d in detalhes
        if d.get("grading_error")
    ]
    if not metrics["correctness"]["checkpoints_ran"]:
        motivos.append("nenhum checkpoint foi avaliado")
    return motivos


def _fmt(valor, sufixo: str = "") -> str:
    if valor is None:
        return "—"
    if isinstance(valor, float):
        return f"{valor:.4f}{sufixo}" if not sufixo else f"{valor:.2f}{sufixo}"
    return f"{valor}{sufixo}"


def _fmt_quebra(checkpoint: dict) -> str:
    """'quebrados/que passavam antes' do checkpoint, ou '—' sem regressão."""
    if checkpoint.get("tests_previously_passing") is None:
        return "—"
    return f"{checkpoint['tests_broken']}/{checkpoint['tests_previously_passing']}"


def _fmt_int(valor) -> str:
    """Contagens (ex.: linhas adicionadas) sem casas decimais."""
    return "—" if valor is None else str(int(valor))


def _persistir_relatorio(relatorio: dict, run_dir: Path) -> tuple[Path, Path]:
    """Grava o relatório JSON e um resumo Markdown; devolve os dois caminhos."""
    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / "report.json"
    json_path.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    m = relatorio["metrics"]
    corr, diff, slop = m["correctness"], m["diff"], m["slop"]
    usage = relatorio["usage_metrics"]

    pendencias = relatorio.get("incomplete") or []
    aviso = (
        [
            "> **⚠️ RELATÓRIO INCOMPLETO — não é um resultado final.**",
            ">",
            *[f"> - {motivo}" for motivo in pendencias],
            "",
        ]
        if pendencias
        else []
    )
    linhas = [
        "# Benchmark SlopCodeBench — Coder Agent",
        "",
        *aviso,
        f"- **Gerado em:** {relatorio['generated_at']}",
        f"- **Modelo:** {relatorio['model']}",
        f"- **Seed:** {relatorio['seed']}",
        "- **Problemas:** "
        + ", ".join(
            f"{p['name']} ({p['checkpoints']} cp)" for p in relatorio["problems"]
        ),
        f"- **Checkpoints rodados / previstos:** {corr['checkpoints_ran']}/"
        f"{corr['checkpoints_expected']}",
        f"- **Tempo do coder (soma de todos os checkpoints):** "
        f"{usage.get('coder_duration_s', 0.0) / 3600:.1f} h",
        f"- **Duração desta execução:** {usage.get('total_duration_s', 0.0):.0f}s "
        f"(o run pode ter sido retomado; ver `execucoes` no metadata.json)",
        f"- **Tokens (in/out):** {usage['prompt_tokens']}/{usage['completion_tokens']}",
        "",
        "## 1. Correção ao longo do horizonte",
        "",
        "Solve rates sobre TODOS os checkpoints previstos (os não rodados contam "
        "como não resolvidos).",
        "",
        f"- **Strict** (`strict_pass_rate == 1`, inclui regressão): "
        f"{_fmt(corr['pct_checkpoints_strict_solved'], '%')}",
        f"- **Isolated** (`isolated_pass_rate == 1`, sem regressão): "
        f"{_fmt(corr['pct_checkpoints_iso_solved'], '%')}",
        f"- **Core** (`core_pass_rate == 1`): "
        f"{_fmt(corr['pct_checkpoints_core_solved'], '%')}",
        f"- **Problemas com solução parcial / completa:** "
        f"{corr['problems_partial']} / {corr['problems_solved']}",
        f"- **Quebrou o que funcionava:** "
        f"{corr['regression']['checkpoints_that_broke_prior_work']} de "
        f"{corr['regression']['checkpoints_with_prior_passing_tests']} checkpoints "
        f"quebraram testes que passavam no checkpoint anterior "
        f"({corr['regression']['tests_broken']} de "
        f"{corr['regression']['tests_previously_passing']} testes; comparação teste "
        f"a teste da avaliação oficial)",
        f"- **Taxa média nos testes de regressão:** "
        f"{_fmt(corr['regression']['mean_regression_pass_rate'])} (inclui testes "
        f"que já falhavam antes)",
        "",
        "## 2. Crescimento do diff",
        "",
        "| Métrica | n | Média | Mediana |",
        "| ------- | - | ----- | ------- |",
    ]
    for campo, st in diff.items():
        linhas.append(
            f"| `{campo}` | {st['count']} | {_fmt(st['mean'])} | {_fmt(st['median'])} |"
        )
    linhas += [
        "",
        "`delta.churn_ratio = (lines_added + lines_removed) / linhas do checkpoint "
        'anterior`, a partir do 2º checkpoint. O SlopCodeBench não mede "quanto do '
        'código final foi escrito e depois reescrito"; o churn aqui é o oficial, '
        "por checkpoint.",
        "",
        "## 3. Slop (definição do SlopCodeBench)",
        "",
        "| Métrica | n | Média | Mediana |",
        "| ------- | - | ----- | ------- |",
    ]
    for campo in (
        "verbosity",
        "erosion",
        "cloned_pct",
        "verbosity_flagged_pct",
        "mass.high_cc_pct",
    ):
        st = slop[campo]
        linhas.append(
            f"| `{campo}` | {st['count']} | {_fmt(st['mean'])} | {_fmt(st['median'])} |"
        )
    subida = slop["pct_trajectories_rising"]
    ref = slop["paper_reference"]
    linhas += [
        "",
        f"- **Trajetórias com erosão subindo:** {_fmt(subida['erosion']['pct'], '%')} "
        f"({subida['erosion']['rising']}/{subida['erosion']['trajectories']}); "
        f"paper: {ref['pct_trajectories_rising']['erosion']}%",
        f"- **Trajetórias com verbosidade subindo:** "
        f"{_fmt(subida['verbosity']['pct'], '%')} "
        f"({subida['verbosity']['rising']}/{subida['verbosity']['trajectories']}); "
        f"paper: {ref['pct_trajectories_rising']['verbosity']}%",
        f"- Compara o 1º e o último checkpoint rodado de cada problema; "
        f"{subida['erosion'].get('excluded', 0)} problema(s) ficaram fora por não "
        f"terem a métrica em um desses dois checkpoints.",
        "",
        "Checkpoints cujo código não é Python válido (erro de sintaxe) ficam sem "
        "métricas estáticas (`—`) ou com valores só dos arquivos legíveis: é o "
        "comportamento da ferramenta oficial.",
        "",
        "Referência do paper (Tabela 2), só para contexto:",
        "",
        "| Referência | Verbosidade | Erosão |",
        "| ---------- | ----------- | ------ |",
        f"| Painel humano (473 repositórios) | {ref['human_panel']['verbosity']} | "
        f"{ref['human_panel']['erosion']} |",
        f"| Checkpoints de agentes (15 modelos) | "
        f"{ref['agent_checkpoints']['verbosity']} | {ref['agent_checkpoints']['erosion']} |",
        "",
        "## Por fase de progresso",
        "",
        "| Fase | Checkpoints (rodados) | Strict % | Iso % | Core % | Churn médio | "
        "Verbosidade média | Erosão média |",
        "| ---- | --------------------- | -------- | ----- | ------ | ----------- | "
        "----------------- | ------------ |",
    ]
    for fase, dados in m["by_phase"].items():
        linhas.append(
            f"| {fase} | {dados['checkpoints']} ({dados['ran']}) | "
            f"{_fmt(dados['pct_strict_solved'], '%')} | {_fmt(dados['pct_iso_solved'], '%')} | "
            f"{_fmt(dados['pct_core_solved'], '%')} | "
            f"{_fmt(dados['delta.churn_ratio']['mean'])} | "
            f"{_fmt(dados['verbosity']['mean'])} | {_fmt(dados['erosion']['mean'])} |"
        )
    linhas += [
        "",
        "## Por checkpoint",
        "",
        "| Problema | Checkpoint | Estado | Strict | Iso | Core | Quebrou | +linhas | "
        "−linhas | Churn | Verbosidade | Erosão |",
        "| -------- | ---------- | ------ | ------ | --- | ---- | ------- | ------- | "
        "------- | ----- | ----------- | ------ |",
    ]
    for c in m["by_checkpoint"]:
        linhas.append(
            f"| {c['problem']} | {c['checkpoint']} | {c['state']} | {_fmt(c['strict_pass_rate'])} | "
            f"{_fmt(c['isolated_pass_rate'])} | {_fmt(c['core_pass_rate'])} | "
            f"{_fmt_quebra(c)} | {_fmt_int(c['lines_added'])} | {_fmt_int(c['lines_removed'])} | "
            f"{_fmt(c['delta.churn_ratio'])} | {_fmt(c['verbosity'])} | {_fmt(c['erosion'])} |"
        )

    md_path = run_dir / "report.md"
    md_path.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return json_path, md_path


def _proveniencia(problems_root: Path) -> dict:
    """Versões que tornam o baseline comparável depois de mudanças no coder."""
    from benchmarks.coding_review.slopcodebench import grading
    from benchmarks.coding_review.slopcodebench.dataset import source_commit

    def _git(*cmd: str, cwd: Path) -> str | None:
        try:
            return subprocess.run(
                ["git", *cmd], cwd=cwd, check=True, capture_output=True, text=True
            ).stdout.strip()
        except OSError, subprocess.SubprocessError:
            return None

    harness = grading.provenance()
    return {
        "repo_commit": _git("rev-parse", "HEAD", cwd=bootstrap.repo_root()),
        "coder_prompt_sha256": hashlib.sha256(_CODER_PROMPT.read_bytes()).hexdigest(),
        "slop_code_bench": {"version": harness["version"], "commit": harness["commit"]},
        "scb_problems_commit": source_commit(problems_root),
        "scb_check_version": harness["scb_check_version"],
    }


def _validar_e_persistir_config(
    run_dir: Path, params: dict, proveniencia: dict
) -> None:
    """Valida se os parâmetros atuais coincidem com os originais e persiste-os."""
    config_path = run_dir / "metadata.json"
    if config_path.is_file():
        try:
            salvos = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"Erro ao ler metadata.json em {run_dir}: {exc}")
        for chave in _PARAMS_VALIDADOS:
            if salvos.get(chave) != params[chave]:
                raise ValueError(
                    f"Erro: o parâmetro '{chave}' ({params[chave]}) difere do "
                    f"valor original da execução ({salvos.get(chave)})."
                )
        # Retomar com outro prompt do coder, outro harness ou outro catálogo
        # misturaria versões no mesmo relatório. O commit do repositório fica de
        # fora de propósito: ele muda a cada commit e vai para `execucoes`.
        for chave in _PROVENIENCIA_VALIDADA:
            if salvos.get(chave) != proveniencia.get(chave):
                raise ValueError(
                    f"Erro: a proveniência '{chave}' ({proveniencia.get(chave)}) "
                    f"difere da execução original ({salvos.get(chave)})."
                )
        return

    run_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        **params,
        "prompt_template": "just-solve",
        "environment": "docker-python3.12-uv",
        "pass_policy": "any",
        **proveniencia,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    config_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _registrar_execucao(run_dir: Path) -> None:
    """Anexa ao metadata.json o que vale para ESTA execução (início ou retomada).

    Um run pode atravessar várias execuções (`--resume-dir`); o timeout do LLM e
    o estado do código podem mudar entre elas, e o baseline precisa registrar
    isso. Chamado depois do bootstrap, para refletir o `AI4ES_LLM_TIMEOUT`
    efetivo (variável de ambiente ou `adk/.env`).
    """

    def _git(*cmd: str) -> str | None:
        try:
            return subprocess.run(
                ["git", *cmd],
                cwd=bootstrap.repo_root(),
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except OSError, subprocess.SubprocessError:
            return None

    pasta_benchmark = str(Path(__file__).resolve().parent)
    alteracoes = _git("status", "--porcelain", "--", pasta_benchmark)
    config_path = run_dir / "metadata.json"
    metadata = json.loads(config_path.read_text(encoding="utf-8"))
    metadata.setdefault("execucoes", []).append(
        {
            "iniciada_em": datetime.now(timezone.utc).isoformat(),
            "llm_timeout_s": float(os.environ.get("AI4ES_LLM_TIMEOUT", "120")),
            "repo_commit": _git("rev-parse", "HEAD"),
            # Só arquivos de código: os resultados do próprio run mudam sempre.
            "codigo_do_benchmark_alterado": any(
                linha.endswith(".py") for linha in (alteracoes or "").splitlines()
            ),
        }
    )
    config_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _registrar_fim(run_dir: Path) -> None:
    config_path = run_dir / "metadata.json"
    metadata = json.loads(config_path.read_text(encoding="utf-8"))
    metadata["finished_at"] = datetime.now(timezone.utc).isoformat()
    config_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
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

    from benchmarks.coding_review.slopcodebench.dataset import (
        load_problems,
        resolve_problems_root,
    )

    problems_root = resolve_problems_root(args.problems_path)
    problemas = load_problems(
        problems_root, limit=args.limit, seed=args.seed, names=args.problems
    )
    _testar_harness()

    if args.resume_dir is not None:
        run_dir = args.resume_dir
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = args.output_dir / _construir_nome_run(args, timestamp, len(problemas))

    params = {
        "model": args.model,
        "limit": args.limit,
        "seed": args.seed,
        "problems": [p.name for p in problemas],
        "checkpoint_timeout_s": args.checkpoint_timeout,
    }
    _validar_e_persistir_config(run_dir, params, _proveniencia(problems_root))

    # O workspace do coder fica DENTRO do run e FORA do catálogo de problemas:
    # as tools de leitura do coder ficam presas a esta pasta, então `tests/` e
    # `solutions/` do catálogo são inalcançáveis.
    bootstrap.prepare_environment(run_dir / "workspace" / "adk", model=args.model)

    _testar_conexao_modelo(args.model)
    _testar_docker()

    _registrar_execucao(run_dir)

    from benchmarks.coding_review.slopcodebench.coder_runner import LlmIndisponivel

    t_start = time.time()
    try:
        relatorio = asyncio.run(_executar(args, run_dir, problemas))
    except LlmIndisponivel as exc:
        print(
            "\n[run] INTERROMPIDO: o LLM do coder ficou indisponível "
            f"(cota esgotada, limite ou conexão):\n  {exc}\n"
            "O checkpoint em andamento NÃO foi registrado. Quando o LLM voltar, "
            "retome com:\n"
            f"  {_comando_de_retomada(args, run_dir)}"
        )
        return 2
    relatorio["usage_metrics"]["total_duration_s"] = round(time.time() - t_start, 2)
    json_path, md_path = _persistir_relatorio(relatorio, run_dir)
    _registrar_fim(run_dir)

    corr = relatorio["metrics"]["correctness"]
    print("\n=== RESULTADO ===")
    print(
        f"Strict/Iso/Core solved: {_fmt(corr['pct_checkpoints_strict_solved'], '%')} / "
        f"{_fmt(corr['pct_checkpoints_iso_solved'], '%')} / "
        f"{_fmt(corr['pct_checkpoints_core_solved'], '%')}"
    )
    print(f"Relatório JSON: {json_path}")
    print(f"Resumo Markdown: {md_path}")
    if relatorio["incomplete"]:
        print("\n[run] ATENÇÃO: relatório INCOMPLETO, não é um resultado final:")
        for motivo in relatorio["incomplete"]:
            print(f"  - {motivo}")
        print(f"Para completar: {_comando_de_retomada(args, run_dir)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
