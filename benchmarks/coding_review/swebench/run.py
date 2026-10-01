"""Orquestrador CLI do benchmark SWE-bench Verified (issue #417).

Uso típico (a partir da raiz do repositório):

    python -m benchmarks.coding_review.swebench.run --model <modelo> --limit 30

Fases:
1. **Seleção** — baixa (ou reutiliza) o parquet fixado do SWE-bench Verified e
   sorteia as instâncias com seed fixa. Parâmetros e ids sorteados vão para o
   `metadata.json`, que protege a retomada (`--resume-dir`).
2. **Loop** (por instância, com checkpoint em `progress.jsonl`) — prepara o
   workspace a partir da imagem oficial, roda o `code_execute_loop` até ele
   parar sozinho, registra rodadas/desfecho/veredito e extrai o patch.
3. **Correção** — grava o `predictions.jsonl` e chama o harness OFICIAL do
   SWE-bench (venv separado). Pode ser refeita sozinha com `--grade-only`.
4. **Relatório** — `report.json` + `report.md` com as três métricas.

`--dry-run` executa só a fase 1 e grava, por instância, a task e a mensagem que
o coder receberia — sem LLM e sem Docker.

`--gold-sanity` corrige os patches OFICIAIS das instâncias sorteadas (sem LLM):
valida o ambiente do harness oficial antes de gastar horas com o loop.

`--executor-sanity` aplica a solução OFICIAL no workspace e roda o harness do
executor (sem LLM): mostra quantas aprovações corretas o ambiente do executor
consegue dar, separando ruído de infraestrutura do comportamento do LLM.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Execução como script (python benchmarks/coding_review/swebench/run.py).
if __package__ in (None, ""):
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from benchmarks.coding_review.swebench import bootstrap, contract, dataset, grading
from benchmarks.coding_review.swebench.dataset import (
    DATASET_REPO_ID,
    DEFAULT_LIMIT,
    DEFAULT_REVISION,
    DEFAULT_SEED,
    SWEInstance,
)
from benchmarks.coding_review.swebench.metrics import (
    GRADE_NOT_GRADED,
    GRADE_PREP_FAILED,
    GRADE_PROVIDER_FAILED,
    aggregate,
)
from benchmarks.coding_review.swebench.report import render_markdown

_PKG_DIR = Path(__file__).resolve().parent
_DEFAULT_OUTPUT = _PKG_DIR / "results"
_DEFAULT_DATASET_DIR = _PKG_DIR / "datasets"
_DEFAULT_SWEBENCH_PYTHON = _PKG_DIR / ".venv-swebench" / "bin" / "python"
_MODEL_PREFIX = "ai4se-coding-review"

PROGRESS_FILE = "progress.jsonl"
PREDICTIONS_FILE = "predictions.jsonl"
METADATA_FILE = "metadata.json"
GRADING_FILE = "grading.json"
PATCHES_DIR = "patches"
GRADING_DIR = "grading"
GOLD_GRADING_DIR = "grading_gold"
GOLD_FILE = "sanidade_gold.json"
_GOLD_MODEL = "gold"
EXECUTOR_SANITY_FILE = "sanidade_executor.json"
EXECUTOR_SANITY_PROGRESS = "sanidade_executor.jsonl"
WORKSPACE_DIR = "workspace"
DRY_RUN_DIR = "dry_run"

# Parâmetros que definem o experimento: a retomada exige que coincidam.
_PARAMETROS_GUARDADOS = (
    "model", "seed", "limit", "dataset_revision", "instancias",
    "instance_timeout", "grading_timeout",
)
_TERMOS_SENSIVEIS = ("KEY", "TOKEN", "SECRET", "PASSWORD")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="benchmarks.coding_review.swebench.run",
        description=(
            "Benchmark SWE-bench Verified do loop coder → executor do "
            "workflow_coding_review (issue #417)."
        ),
    )
    p.add_argument("--model", default=None,
                   help=("Modelo LLM do loop (ex.: github_copilot/gpt-5-mini). Obrigatório, "
                         "exceto ao retomar um run: aí vale o modelo gravado nele."))
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                   help=f"Instâncias sorteadas (default: {DEFAULT_LIMIT}).")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED,
                   help=f"Seed do sorteio (default: {DEFAULT_SEED}).")
    p.add_argument("--instance-ids", nargs="*", default=None,
                   help="Usa estas instâncias em vez do sorteio.")
    p.add_argument("--dataset-revision", default=DEFAULT_REVISION,
                   help="Revisão (commit) do dataset no Hugging Face.")
    p.add_argument("--dataset-dir", type=Path, default=_DEFAULT_DATASET_DIR,
                   help="Cache local do parquet.")
    p.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT,
                   help="Diretório-base dos runs.")
    p.add_argument("--resume-dir", type=Path, default=None,
                   help="Retoma um run existente (pula instâncias já concluídas).")
    p.add_argument("--instance-timeout", type=int, default=3600,
                   help=("Teto (s) de wall-clock do loop por instância (default: 3600). "
                         "Aproximado: só é checado quando o harness devolve o controle."))
    p.add_argument("--max-tokens-per-minute", type=int, default=50_000,
                   help=("Teto de tokens (entrada+saída) por minuto enviados ao LLM; o "
                         "loop espera antes de cada chamada para respeitá-lo. Evita o "
                         "rate limit do provedor. 0 desliga (default: 50000)."))
    p.add_argument("--provider-retries", type=int, default=4,
                   help=("Novas tentativas de uma instância quando o provedor de LLM "
                         "falha (rate limit, cota, rede) antes de parar o run (default: 4)."))
    p.add_argument("--provider-wait", type=int, default=600,
                   help=("Espera (s) antes da 1ª nova tentativa; dobra a cada uma "
                         "(default: 600 → 10, 20, 40, 80 min)."))
    p.add_argument("--swebench-python", default=os.environ.get(
                       "SWEBENCH_PYTHON", str(_DEFAULT_SWEBENCH_PYTHON)),
                   help="Python do venv com o harness oficial (`swebench`).")
    p.add_argument("--grading-workers", type=int, default=2,
                   help="Workers do harness oficial (default: 2).")
    p.add_argument("--grading-timeout", type=int, default=1800,
                   help="Timeout (s) por instância no harness oficial (default: 1800).")
    p.add_argument("--skip-grading", action="store_true",
                   help="Roda só o loop; corrija depois com --grade-only.")
    p.add_argument("--grade-only", action="store_true",
                   help="Só a correção + relatório de um run existente (exige --resume-dir).")
    p.add_argument("--dry-run", action="store_true",
                   help="Só sorteia e gera tasks/mensagens (sem LLM e sem Docker).")
    p.add_argument("--gold-sanity", action="store_true",
                   help=("Corrige os patches OFICIAIS das instâncias sorteadas no harness "
                         "oficial (sem LLM). Instâncias que não resolvem nem com o gold "
                         "são problema de ambiente e devem virar exclusões documentadas."))
    p.add_argument("--executor-sanity", action="store_true",
                   help=("Aplica a solução OFICIAL no workspace e roda o harness do "
                         "EXECUTOR (sem LLM): mostra quantas aprovações corretas o "
                         "ambiente do executor consegue dar."))
    return p.parse_args(argv)


def _validar_args(args: argparse.Namespace) -> None:
    if not args.model:
        raise ValueError(
            "Erro: o parâmetro '--model' é obrigatório. A execução do benchmark "
            "não pode prosseguir sem a definição explícita do modelo."
        )
    if args.grade_only and args.resume_dir is None:
        raise ValueError("Erro: '--grade-only' exige '--resume-dir' de um run existente.")
    if args.grade_only and args.skip_grading:
        raise ValueError("Erro: '--grade-only' e '--skip-grading' são excludentes.")
    if args.gold_sanity and (args.dry_run or args.skip_grading or args.grade_only):
        raise ValueError(
            "Erro: '--gold-sanity' não se combina com '--dry-run', '--skip-grading' "
            "ou '--grade-only'."
        )
    if args.executor_sanity and (
        args.dry_run or args.skip_grading or args.grade_only or args.gold_sanity
    ):
        raise ValueError(
            "Erro: '--executor-sanity' não se combina com '--dry-run', "
            "'--skip-grading', '--grade-only' ou '--gold-sanity'."
        )
    if args.resume_dir is not None and not args.resume_dir.is_dir():
        raise FileNotFoundError(
            f"Erro: o diretório de retomada '--resume-dir' ({args.resume_dir}) não "
            "existe ou não é um diretório."
        )


# ---------------------------------------------------------------------------
# Nomes, metadata e checkpoint
# ---------------------------------------------------------------------------


def _sanitizar_componente(valor: str) -> str:
    """Normaliza um trecho para nome de diretório (barras viram hífen)."""
    limpo = re.sub(r"[^0-9A-Za-z._-]+", "-", valor.strip())
    limpo = re.sub(r"-{2,}", "-", limpo).strip("-.")
    return limpo or "na"


def _construir_nome_run(model: str, n: int, timestamp: str) -> str:
    """`run_<timestamp>_<modelo>_n<N>` (formato pedido pela issue #417)."""
    return f"run_{timestamp}_{_sanitizar_componente(model)}_n{n}"


def model_name_for_predictions(model: str) -> str:
    """Identificador do "modelo" nas predições do SWE-bench (sem barras)."""
    return f"{_MODEL_PREFIX}__{_sanitizar_componente(model)}"


def _parametros(args: argparse.Namespace, instancias: list[SWEInstance]) -> dict[str, Any]:
    return {
        "model": args.model,
        "seed": args.seed,
        "limit": args.limit,
        "instance_ids_filtro": args.instance_ids or None,
        "dataset_revision": args.dataset_revision,
        "instancias": [i.instance_id for i in instancias],
        "instance_timeout": args.instance_timeout,
        "grading_timeout": args.grading_timeout,
    }


def _resolver_modelo_da_retomada(args: argparse.Namespace) -> None:
    """Na retomada sem `--model`, usa o modelo gravado no run original."""
    if args.model or args.resume_dir is None or not args.resume_dir.is_dir():
        return
    salvo = (_ler_metadata(args.resume_dir).get("parametros") or {}).get("model")
    if salvo:
        args.model = salvo


def _ler_metadata(run_dir: Path) -> dict[str, Any]:
    caminho = run_dir / METADATA_FILE
    if not caminho.is_file():
        return {}
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Erro ao ler {METADATA_FILE} em {run_dir}: {exc}") from exc


def _gravar_metadata(run_dir: Path, metadata: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / METADATA_FILE).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _validar_e_persistir_metadata(run_dir: Path, params: dict[str, Any]) -> dict[str, Any]:
    """Na retomada, exige os mesmos parâmetros do run original; senão, grava-os."""
    metadata = _ler_metadata(run_dir)
    salvos = metadata.get("parametros")
    if salvos:
        for chave in _PARAMETROS_GUARDADOS:
            if salvos.get(chave) != params.get(chave):
                raise ValueError(
                    f"Erro: o parâmetro '{chave}' ({params.get(chave)!r}) difere do "
                    f"run original ({salvos.get(chave)!r}). Retomar misturaria "
                    "configurações diferentes."
                )
        return metadata
    metadata = {"parametros": params}
    _gravar_metadata(run_dir, metadata)
    return metadata


def _carregar_progresso(caminho: Path) -> dict[str, dict[str, Any]]:
    """Checkpoint incremental: `{instance_id: registro}` (ignora linhas truncadas)."""
    concluidos: dict[str, dict[str, Any]] = {}
    if not caminho.is_file():
        return concluidos
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        try:
            registro = json.loads(linha)
            concluidos[registro["instance_id"]] = registro
        except (json.JSONDecodeError, KeyError):
            print(f"[run] Aviso: linha inválida em {caminho.name}, ignorada.")
    return concluidos


def _append_progresso(caminho: Path, registro: dict[str, Any]) -> None:
    """Anexa um registro; se a última escrita foi truncada, fecha a linha antes.

    Sem isso, o registro novo seria colado na linha truncada e as duas seriam
    descartadas juntas na leitura.
    """
    prefixo = ""
    if caminho.is_file() and caminho.stat().st_size > 0:
        with caminho.open("rb") as fh:
            fh.seek(-1, os.SEEK_END)
            if fh.read(1) != b"\n":
                prefixo = "\n"
    with caminho.open("a", encoding="utf-8") as fh:
        fh.write(prefixo + json.dumps(registro, ensure_ascii=False) + "\n")
        fh.flush()


def _concluida(registro: dict[str, Any] | None) -> bool:
    """Instância que a retomada pode pular.

    Falha na preparação e falha do provedor de LLM são refeitas: nenhuma das
    duas diz nada sobre o loop.
    """
    return (
        registro is not None
        and not registro.get("falha_preparacao")
        and not registro.get("falha_provedor")
    )


# Exceções do LiteLLM que indicam o PROVEDOR indisponível (cota, rate limit,
# credencial, rede), e não o comportamento do loop. `ContextWindowExceededError`
# fica de fora de propósito: estourar o contexto é resultado do loop.
_ERROS_DE_PROVEDOR = frozenset({
    "RateLimitError", "AuthenticationError", "PermissionDeniedError",
    "APIConnectionError", "ServiceUnavailableError", "InternalServerError",
    "Timeout", "APIError",
})
_SINAIS_DE_COTA = ("rate limit", "ratelimit", "quota", "insufficient_quota")
# 429 como código isolado: "prompt token count of 142900" contém "429".
_HTTP_429 = re.compile(r"(?<!\d)429(?!\d)")


def _falha_do_provedor(erro: str | None) -> bool:
    """Se o erro da instância veio do provedor de LLM (e não do loop).

    Estouro de contexto nunca conta: é resultado do loop, mesmo quando o
    provedor o devolve como um erro HTTP genérico.
    """
    from benchmarks.coding_review.swebench.loop_runner import is_context_overflow

    if not erro or is_context_overflow(erro):
        return False
    tipo = erro.split(":", 1)[0].strip().rsplit(".", 1)[-1]
    texto = erro.lower()
    return (
        tipo in _ERROS_DE_PROVEDOR
        or any(sinal in texto for sinal in _SINAIS_DE_COTA)
        or bool(_HTTP_429.search(texto))
    )


def _git_saida(raiz: Path, *args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(raiz), *args], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _coletar_ambiente(max_iter: int | None, swebench_version: str | None) -> dict[str, Any]:
    """Tudo que muda o resultado sem estar nos parâmetros da CLI."""
    raiz = bootstrap.repo_root()
    return {
        "git_commit": _git_saida(raiz, "rev-parse", "HEAD"),
        "git_dirty": bool(_git_saida(raiz, "status", "--porcelain", "--untracked-files=no")),
        "python": platform.python_version(),
        "plataforma": platform.platform(),
        "max_loop_iterations": max_iter,
        "swebench_version": swebench_version,
        "adk_llm_model": os.environ.get("ADK_LLM_MODEL"),
        "variaveis_ai4es": {
            chave: valor
            for chave, valor in sorted(os.environ.items())
            if chave.startswith("AI4ES_")
            and not any(t in chave.upper() for t in _TERMOS_SENSIVEIS)
        },
    }


# Campos do ambiente que, se mudarem entre o run original e uma retomada,
# misturam condições diferentes no mesmo relatório.
_AMBIENTE_CRITICO = ("git_commit", "max_loop_iterations", "adk_llm_model", "variaveis_ai4es")


def _registrar_ambiente(metadata: dict[str, Any], atual: dict[str, Any]) -> None:
    """Grava o ambiente do run; numa retomada, preserva o original e anexa o novo."""
    original = metadata.get("ambiente")
    if not original:
        metadata["ambiente"] = atual
        return
    metadata.setdefault("ambientes_de_retomada", []).append(atual)
    divergentes = [c for c in _AMBIENTE_CRITICO if original.get(c) != atual.get(c)]
    if divergentes:
        print(
            "[run] Aviso: a retomada roda em ambiente diferente do original em "
            f"{', '.join(divergentes)} — o relatório vai misturar as duas condições "
            "(ver `ambientes_de_retomada` no metadata.json)."
        )


# ---------------------------------------------------------------------------
# Fase 1 — seleção (e dry-run)
# ---------------------------------------------------------------------------


def _carregar_instancias(args: argparse.Namespace) -> tuple[list[SWEInstance], Path]:
    parquet = dataset.ensure_dataset(args.dataset_dir, revision=args.dataset_revision)
    todas = dataset.load_instances(parquet)
    selecionadas = dataset.select_instances(
        todas, limit=args.limit, seed=args.seed, instance_ids=args.instance_ids
    )
    return selecionadas, parquet


def _executar_dry_run(run_dir: Path, instancias: list[SWEInstance]) -> None:
    base = run_dir / DRY_RUN_DIR
    for inst in instancias:
        destino = base / inst.instance_id
        destino.mkdir(parents=True, exist_ok=True)
        (destino / f"{contract.TASK_ID}.json").write_text(
            json.dumps(contract.build_task_contract(inst), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (destino / "mensagem_coder.md").write_text(
            contract.build_coder_message(inst), encoding="utf-8"
        )
    distribuicao = dataset.distribution_by_repo(instancias)
    (base / "amostra.json").write_text(
        json.dumps(
            {
                "instancias": [
                    {"instance_id": i.instance_id, "repo": i.repo, "image": i.image}
                    for i in instancias
                ],
                "por_repositorio": distribuicao,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[dry-run] {len(instancias)} instância(s) em {base}")
    for repo, n in distribuicao.items():
        print(f"  {repo}: {n}")
    print(
        f"[dry-run] Para usar este sorteio: --resume-dir {run_dir}. "
        "Se for descartá-lo, apague o diretório (ele não é ignorado pelo git)."
    )


# ---------------------------------------------------------------------------
# Fase 2 — loop
# ---------------------------------------------------------------------------


def _testar_conexao_modelo(model: str) -> None:
    """Pre-flight: chamada mínima ao modelo, com os headers da produção."""
    import traceback

    import litellm

    from shared.llm import copilot_completion_kwargs, openrouter_completion_kwargs

    print(f"\n[PRE-FLIGHT] Testando conexão com o modelo '{model}'...")
    try:
        litellm.completion(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            timeout=20,
            **copilot_completion_kwargs(model),
            **openrouter_completion_kwargs(model),
        )
    except Exception:  # noqa: BLE001 — qualquer falha aborta antes de gastar horas
        traceback.print_exc()
        print(f"[PRE-FLIGHT ERROR] Falha ao conectar ao modelo '{model}'.")
        raise SystemExit(1)
    print("[PRE-FLIGHT] Modelo OK.")


def _testar_docker() -> None:
    import docker

    try:
        docker.from_env().ping()
    except Exception as exc:  # noqa: BLE001
        print(f"[PRE-FLIGHT ERROR] Docker indisponível: {exc}")
        raise SystemExit(1)
    if platform.machine() not in ("x86_64", "AMD64"):
        print(
            "[PRE-FLIGHT] Aviso: as imagens do SWE-bench são x86_64; nesta "
            f"arquitetura ({platform.machine()}) elas rodarão emuladas e lentas."
        )
    print("[PRE-FLIGHT] Docker OK.")


def _registro_de_falha_na_preparacao(inst: SWEInstance, erro: str) -> dict[str, Any]:
    """Registro de uma instância cujo loop nem começou.

    Marcado com `falha_preparacao`: a retomada tenta de novo (a causa costuma
    ser transitória, como um pull de imagem) e, se persistir, a correção a trata
    como status próprio — fora da matriz da métrica 3, porque o validador nunca
    rodou.
    """
    return {
        "instance_id": inst.instance_id,
        "falha_preparacao": True,
        "repo": inst.repo,
        "difficulty": inst.difficulty,
        "rodadas": 0,
        "turnos_coder": 0,
        "historico_notas": [],
        "motivo_terminacao": "erro_operacional",
        "status_desfecho": "reprovado",
        "veredito_validador": None,
        "patch": {"arquivo": None, "vazio": True, "arquivos": [], "excluidos": {}},
        "erro": f"Falha na preparação do workspace: {erro}",
        "timeout": False,
        "duracao_s": 0.0,
        "uso": {},
    }


def _montar_registro(inst: SWEInstance, run, seed, patch_result, patch_rel: str | None,
                     patch_erro: str | None) -> dict[str, Any]:
    desfecho = run.desfecho
    return {
        "instance_id": inst.instance_id,
        "repo": inst.repo,
        "difficulty": inst.difficulty,
        "rodadas": run.guarda.get("rodadas_executor", 0),
        "turnos_coder": run.guarda.get("turnos_coder", 0),
        "historico_notas": desfecho.get("historico_notas") or [],
        "motivo_terminacao": desfecho.get("motivo_terminacao"),
        "status_desfecho": desfecho.get("status"),
        "conceito": desfecho.get("conceito"),
        "nota_final": desfecho.get("nota_final"),
        "veredito_validador": run.veredito_validador,
        "loop_stop_reason": run.state.get("loop_stop_reason"),
        "execucao": run.execucao,
        "guarda": run.guarda,
        "patch": {
            "arquivo": patch_rel,
            "vazio": patch_result.empty,
            "arquivos": patch_result.files,
            "excluidos": patch_result.excluded,
            "binarios_por_codificacao": patch_result.binary_fallback,
            "erro": patch_erro,
        },
        "preparacao": {
            "conflitos": seed.conflicts,
            "membros_pulados": seed.skipped_members,
        },
        "erro": run.error,
        "timeout": run.timed_out,
        "duracao_s": run.duration_s,
        # Pausas da guarda (rate limit e controle de ritmo) não são tempo do loop.
        "pausa_rate_limit_s": sum(run.guarda.get("pausas_rate_limit_s") or []),
        "pausa_ritmo_s": run.guarda.get("pausa_ritmo_s") or 0.0,
        "duracao_ativa_s": round(
            run.duration_s
            - sum(run.guarda.get("pausas_rate_limit_s") or [])
            - (run.guarda.get("pausa_ritmo_s") or 0.0),
            2,
        ),
        "uso": run.uso,
        "texto_final": run.texto_final,
        "desfecho": desfecho,
    }


async def _executar_loop(args: argparse.Namespace, run_dir: Path,
                         instancias: list[SWEInstance]) -> None:
    """Fase 2: uma instância por vez, sempre no mesmo workspace."""
    from benchmarks.coding_review.swebench import environment, loop_runner
    from benchmarks.coding_review.swebench import patch as patch_mod
    from benchmarks.coding_review.swebench.guard_plugin import BenchmarkGuardPlugin
    from benchmarks.coding_review.swebench.snapshot import SnapshotError
    from shared.workspace import get_agent_workspace

    coder_src = get_agent_workspace("cr_coder")
    tasks_dir = get_agent_workspace("cr_context_engineer")
    plugin = BenchmarkGuardPlugin(
        coder_src, max_tokens_per_minute=args.max_tokens_per_minute
    )

    progress_path = run_dir / PROGRESS_FILE
    patches_dir = run_dir / PATCHES_DIR
    patches_dir.mkdir(parents=True, exist_ok=True)
    concluidos = _carregar_progresso(progress_path)
    if concluidos:
        print(f"[run] Retomando: {len(concluidos)} instância(s) já concluída(s).")

    for idx, inst in enumerate(instancias, start=1):
        prefixo = f"[run] ({idx}/{len(instancias)}) {inst.instance_id}"
        anterior = concluidos.get(inst.instance_id)
        if _concluida(anterior):
            print(f"{prefixo}: CACHE")
            continue
        if anterior is not None:
            causa = "a preparação" if anterior.get("falha_preparacao") else "o provedor de LLM"
            print(f"{prefixo}: refazendo ({causa} tinha falhado)")

        # Rate limit do provedor é temporário: espera (com backoff) e refaz a
        # instância do zero, para o run seguir sozinho. Só depois das
        # tentativas é que ele para, como antes.
        seed, run, erro_preparacao = None, None, None
        for tentativa in range(args.provider_retries + 1):
            # Isolamento: todo o `coder/` (src, tasks, execution...) zera.
            environment.clear_directory(coder_src.parent)
            try:
                seed = environment.seed_workspace(coder_src, inst.image)
            except Exception as exc:  # noqa: BLE001 — falha vira registro, não queda
                erro_preparacao = str(exc)
                break
            loop_runner.write_task_file(tasks_dir, inst)
            run = await loop_runner.run_loop(
                inst, plugin=plugin, timeout_s=args.instance_timeout
            )
            if not _falha_do_provedor(run.error) or tentativa == args.provider_retries:
                break
            espera = args.provider_wait * (2 ** tentativa)
            print(
                f"{prefixo}: LLM indisponível ({str(run.error)[:110]}). Nova tentativa "
                f"{tentativa + 1}/{args.provider_retries} em {espera / 60:.0f} min."
            )
            await asyncio.sleep(espera)

        if erro_preparacao is not None:
            print(f"{prefixo}: FALHA NA PREPARAÇÃO ({erro_preparacao})")
            _append_progresso(
                progress_path, _registro_de_falha_na_preparacao(inst, erro_preparacao)
            )
            continue

        patch_erro = None
        try:
            patch_result = patch_mod.extract_patch(
                coder_src,
                seed.baseline_tree,
                test_patch_paths=inst.test_patch_paths,
                baseline_ignored=seed.baseline_ignored,
            )
        except SnapshotError as exc:
            patch_result, patch_erro = patch_mod.PatchResult(patch=""), str(exc)
        patch_rel = f"{PATCHES_DIR}/{inst.instance_id}.diff"
        (run_dir / patch_rel).write_text(patch_result.patch, encoding="utf-8")

        registro = _montar_registro(inst, run, seed, patch_result, patch_rel, patch_erro)
        if _falha_do_provedor(run.error):
            # Cota/rede/credencial: seguir só gravaria falsas falhas do loop em
            # todas as instâncias restantes. Para aqui; a retomada refaz esta.
            registro["falha_provedor"] = True
            _append_progresso(progress_path, registro)
            print(f"{prefixo}: LLM INDISPONÍVEL ({run.error})")
            raise SystemExit(
                "[run] Run interrompido: o provedor de LLM continuou falhando depois de "
                f"{args.provider_retries} nova(s) tentativa(s) (cota, rate limit, "
                "credencial ou rede). Nada foi contabilizado como falha do loop. "
                f"Quando normalizar, retome com --resume-dir {run_dir}"
            )
        _append_progresso(progress_path, registro)
        print(
            f"{prefixo}: rodadas={registro['rodadas']} "
            f"motivo={registro['motivo_terminacao']} "
            f"validador={registro['veredito_validador'] or '—'} "
            f"patch={'vazio' if patch_result.empty else f'{len(patch_result.files)} arquivo(s)'} "
            f"({run.duration_s}s)"
        )


# ---------------------------------------------------------------------------
# Fase 3 — correção oficial
# ---------------------------------------------------------------------------


def _ler_patch(run_dir: Path, registro: dict[str, Any]) -> str:
    relativo = (registro.get("patch") or {}).get("arquivo")
    if not relativo:
        return ""
    caminho = run_dir / relativo
    return caminho.read_text(encoding="utf-8") if caminho.is_file() else ""


def _fase_grading(
    args: argparse.Namespace, run_dir: Path, registros: list[dict[str, Any]],
    dataset_path: Path, swebench_version: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Corrige os patches no harness oficial.

    Instâncias com falha na preparação não vão ao harness (não há loop a
    avaliar): recebem o status próprio `falha_preparacao`.

    Returns:
        `(resultados por instância, metadados da correção)` — os metadados
        (versão, código de saída) acompanham o relatório.
    """
    modelo = model_name_for_predictions(args.model)
    avaliaveis = [
        r for r in registros
        if not r.get("falha_preparacao") and not r.get("falha_provedor")
    ]
    patches = [(r["instance_id"], _ler_patch(run_dir, r)) for r in avaliaveis]
    predictions_path = run_dir / PREDICTIONS_FILE
    grading.write_predictions(predictions_path, patches, model_name_or_path=modelo)

    saida = {
        r["instance_id"]: {
            "status": GRADE_PREP_FAILED if r.get("falha_preparacao") else GRADE_PROVIDER_FAILED,
            "resolvido": False, "patch_aplicado": None,
            "detalhe": r.get("erro") or "Falha antes de o loop produzir resultado.",
            "causa": GRADE_PREP_FAILED if r.get("falha_preparacao") else GRADE_PROVIDER_FAILED,
        }
        for r in registros
        if r.get("falha_preparacao") or r.get("falha_provedor")
    }
    run_id = run_dir.name
    meta: dict[str, Any] = {"swebench_version": swebench_version, "run_id": run_id,
                            "returncode": None, "duracao_s": 0.0, "comando": None}
    if patches:
        instance_ids = [iid for iid, _ in patches]
        comando = grading.build_command(
            args.swebench_python,
            dataset_path=dataset_path.resolve(),
            predictions_path=predictions_path.resolve(),
            run_id=run_id,
            instance_ids=instance_ids,
            max_workers=args.grading_workers,
            timeout=args.grading_timeout,
        )
        grading_dir = run_dir / GRADING_DIR
        print(f"[grading] Harness oficial (swebench {swebench_version}) em {grading_dir} …")
        t0 = time.time()
        retorno = grading.run_official_grading(comando, grading_dir=grading_dir)
        resultados = grading.parse_results(
            grading_dir,
            run_id=run_id,
            model_name_or_path=modelo,
            instance_ids=instance_ids,
            empty_patch_ids={iid for iid, p in patches if not p.strip()},
        )
        saida.update({iid: r.as_dict() for iid, r in resultados.items()})
        meta.update(returncode=retorno, duracao_s=round(time.time() - t0, 2), comando=comando)
        if retorno != 0:
            print(f"[grading] Aviso: harness terminou com código {retorno} "
                  f"(ver {grading.GRADING_LOG}).")

    (run_dir / GRADING_FILE).write_text(
        json.dumps({**meta, "resultados": saida}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return saida, meta


def _sanidade_gold(args: argparse.Namespace, run_dir: Path, instancias: list[SWEInstance],
                   dataset_path: Path, swebench_version: str) -> list[str]:
    """Harness oficial com os patches OFICIAIS: valida o ambiente de correção.

    Devolve as instâncias que não resolvem nem com o gold — não medem o loop,
    medem o ambiente, e devem ser documentadas como exclusão.
    """
    instance_ids = [i.instance_id for i in instancias]
    run_id = f"{run_dir.name}_gold"
    grading_dir = run_dir / GOLD_GRADING_DIR
    comando = grading.build_command(
        args.swebench_python,
        dataset_path=dataset_path.resolve(),
        predictions_path=_GOLD_MODEL,
        run_id=run_id,
        instance_ids=instance_ids,
        max_workers=args.grading_workers,
        timeout=args.grading_timeout,
    )
    print(f"[gold] Harness oficial com os patches oficiais em {grading_dir} …")
    retorno = grading.run_official_grading(comando, grading_dir=grading_dir)
    resultados = grading.parse_results(
        grading_dir,
        run_id=run_id,
        model_name_or_path=_GOLD_MODEL,
        instance_ids=instance_ids,
        empty_patch_ids=set(),
    )
    falhas = [iid for iid, r in resultados.items() if not r.resolved]
    (run_dir / GOLD_FILE).write_text(
        json.dumps(
            {
                "swebench_version": swebench_version,
                "run_id": run_id,
                "returncode": retorno,
                "comando": comando,
                "nao_resolvidas_com_gold": falhas,
                "resultados": {iid: r.as_dict() for iid, r in resultados.items()},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[gold] {len(instance_ids) - len(falhas)}/{len(instance_ids)} resolvidas com o gold.")
    if falhas:
        print("[gold] Não resolvem nem com o gold (documente como exclusão): " + ", ".join(falhas))
    return falhas


def _sanidade_executor(run_dir: Path, instancias: list[SWEInstance]) -> dict[str, Any]:
    """Solução oficial + harness do executor, instância a instância (sem LLM)."""
    from collections import Counter

    from benchmarks.coding_review.swebench import executor_sanity, loop_runner
    from shared.tools.coding_tools.harness_execucao import executar_harness_validacao
    from shared.workspace import get_agent_workspace

    coder_src = get_agent_workspace("cr_coder")
    tasks_dir = get_agent_workspace("cr_context_engineer")
    checkpoint = run_dir / EXECUTOR_SANITY_PROGRESS
    feitos = _carregar_progresso(checkpoint)

    for idx, inst in enumerate(instancias, start=1):
        prefixo = f"[executor] ({idx}/{len(instancias)}) {inst.instance_id}"
        anterior = feitos.get(inst.instance_id)
        if anterior and anterior.get("resultado") != executor_sanity.RESULTADO_PREPARACAO:
            print(f"{prefixo}: CACHE ({anterior.get('resultado')})")
            continue
        t0 = time.time()
        registro = executor_sanity.check_instance(
            inst,
            coder_src=coder_src,
            tasks_dir=tasks_dir,
            harness=executar_harness_validacao,
            write_task=loop_runner.write_task_file,
        )
        registro["duracao_s"] = round(time.time() - t0, 2)
        _append_progresso(checkpoint, registro)
        feitos[inst.instance_id] = registro
        print(f"{prefixo}: {registro['resultado']} ({registro['duracao_s']}s)")

    registros = [feitos[i.instance_id] for i in instancias if i.instance_id in feitos]
    por_resultado = Counter(r["resultado"] for r in registros)
    resumo = {
        "n": len(registros),
        "sucesso": por_resultado.get(executor_sanity.RESULTADO_SUCESSO, 0),
        "por_resultado": dict(sorted(por_resultado.items())),
        "sem_sucesso": {
            r["instance_id"]: r["resultado"]
            for r in registros
            if r["resultado"] != executor_sanity.RESULTADO_SUCESSO
        },
    }
    (run_dir / EXECUTOR_SANITY_FILE).write_text(
        json.dumps({**resumo, "instancias": registros}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[executor] Com a solução oficial, o harness do executor deu sucesso em "
          f"{resumo['sucesso']}/{resumo['n']}: {resumo['por_resultado']}")
    return resumo


def _ler_sanidade_executor(run_dir: Path) -> dict[str, Any] | None:
    """Resumo do `--executor-sanity`, se ele foi rodado."""
    caminho = run_dir / EXECUTOR_SANITY_FILE
    if not caminho.is_file():
        return None
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return {chave: dados.get(chave) for chave in ("n", "sucesso", "por_resultado", "sem_sucesso")}


# ---------------------------------------------------------------------------
# Fase 4 — relatório
# ---------------------------------------------------------------------------


def _ler_exclusoes_gold(run_dir: Path) -> frozenset[str]:
    """Instâncias que não resolveram nem com o patch oficial (`--gold-sanity`)."""
    caminho = run_dir / GOLD_FILE
    if not caminho.is_file():
        return frozenset()
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"[run] Aviso: {GOLD_FILE} ilegível; nenhuma exclusão aplicada.")
        return frozenset()
    return frozenset(dados.get("nao_resolvidas_com_gold") or [])


def _consolidar(
    metadata: dict[str, Any],
    registros: list[dict[str, Any]],
    resultados: dict[str, dict[str, Any]] | None,
    *,
    correcao: dict[str, Any] | None = None,
    excluidas: frozenset[str] = frozenset(),
    sanidade_executor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from benchmarks.coding_review.swebench.loop_runner import (
        MOTIVO_ERRO_OPERACIONAL,
        MOTIVO_ESTOURO_CONTEXTO,
        is_context_overflow,
    )

    nao_avaliado = {"status": GRADE_NOT_GRADED, "resolvido": None,
                    "patch_aplicado": None, "detalhe": "Correção não executada."}
    # Registros gravados antes do rótulo `estouro_de_contexto` existir saíam
    # como `erro_operacional`; o texto do erro basta para reclassificá-los.
    registros = [
        {**r, "motivo_terminacao": MOTIVO_ESTOURO_CONTEXTO}
        if r.get("motivo_terminacao") == MOTIVO_ERRO_OPERACIONAL
        and is_context_overflow(r.get("erro"))
        else r
        for r in registros
    ]
    instancias = [
        {
            **r,
            "grading": (resultados or {}).get(r["instance_id"], nao_avaliado),
            "excluida_pelo_gold": r["instance_id"] in excluidas,
        }
        for r in registros
    ]
    params = metadata.get("parametros", {})
    ambiente = metadata.get("ambiente", {})
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {"repo_id": DATASET_REPO_ID, "revision": params.get("dataset_revision")},
        "parametros": params,
        "ambiente": ambiente,
        "correcao": correcao,
        "sanidade_executor": sanidade_executor,
        "metricas": aggregate(
            instancias, teto=ambiente.get("max_loop_iterations"), excluidas=excluidas
        ),
        "instancias": instancias,
    }


def _persistir_relatorio(relatorio: dict[str, Any], run_dir: Path) -> tuple[Path, Path]:
    json_path = run_dir / "report.json"
    json_path.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = run_dir / "report.md"
    md_path.write_text(render_markdown(relatorio) + "\n", encoding="utf-8")
    return json_path, md_path


def _imprimir_resumo(relatorio: dict[str, Any], json_path: Path, md_path: Path) -> None:
    m = relatorio["metricas"]
    m1, m2, m3 = m["metrica_1_resolucao"], m["metrica_2_loop"], m["metrica_3_validador"]
    print("\n=== RESULTADO ===")
    print(f"Métrica 1 — resolvidas: {m1['k']}/{m1['n']} (IC 95%: {m1['ic95']})")
    print(f"Métrica 2 — rodadas (média): {m2['rodadas']['media']} | paradas: {m2['motivo_parada']}")
    print(f"Métrica 3 — falsos positivos: {m3['falsos_positivos']}/{m3['aprovadas']} aprovações")
    print(f"Relatório JSON: {json_path}")
    print(f"Resumo Markdown: {md_path}")


def main(argv: list[str] | None = None) -> int:
    # Progresso visível em tempo real mesmo com a saída redirecionada a arquivo.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    args = _parse_args(argv)
    _resolver_modelo_da_retomada(args)
    _validar_args(args)

    instancias, parquet = _carregar_instancias(args)
    if args.resume_dir is not None:
        run_dir = args.resume_dir
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = args.output_dir / _construir_nome_run(args.model, len(instancias), timestamp)
    metadata = _validar_e_persistir_metadata(run_dir, _parametros(args, instancias))

    if args.dry_run:
        _executar_dry_run(run_dir, instancias)
        return 0

    if args.executor_sanity:
        bootstrap.prepare_environment(run_dir / WORKSPACE_DIR, model=args.model)
        _testar_docker()
        _sanidade_executor(run_dir, instancias)
        return 0

    swebench_version: str | None = None
    if not args.skip_grading:
        swebench_version = grading.installed_version(args.swebench_python)
        if swebench_version != grading.SWEBENCH_VERSION:
            print(
                f"[run] Aviso: swebench {swebench_version} instalado; a versão "
                f"validada é {grading.SWEBENCH_VERSION}."
            )

    if args.gold_sanity:
        _sanidade_gold(args, run_dir, instancias, parquet, swebench_version or "")
        return 0

    if not args.grade_only:
        bootstrap.prepare_environment(run_dir / WORKSPACE_DIR, model=args.model)
        _testar_conexao_modelo(args.model)
        _testar_docker()
        from src.agents.workflow_coding_review.agent import _code_execute_loop

        ambiente = _coletar_ambiente(_code_execute_loop.max_iterations, swebench_version)
        ambiente["max_tokens_por_minuto"] = args.max_tokens_per_minute
        _registrar_ambiente(metadata, ambiente)
        _gravar_metadata(run_dir, metadata)
        asyncio.run(_executar_loop(args, run_dir, instancias))
    elif swebench_version is not None:
        metadata.setdefault("ambiente", {})["swebench_version"] = swebench_version
        _gravar_metadata(run_dir, metadata)

    concluidos = _carregar_progresso(run_dir / PROGRESS_FILE)
    registros = [concluidos[i.instance_id] for i in instancias if i.instance_id in concluidos]
    if len(registros) < len(instancias):
        print(f"[run] Aviso: {len(instancias) - len(registros)} instância(s) sem registro.")

    resultados, correcao = None, None
    if not args.skip_grading and registros:
        resultados, correcao = _fase_grading(
            args, run_dir, registros, parquet, swebench_version or ""
        )

    relatorio = _consolidar(
        metadata, registros, resultados,
        correcao=correcao,
        excluidas=_ler_exclusoes_gold(run_dir),
        sanidade_executor=_ler_sanidade_executor(run_dir),
    )
    json_path, md_path = _persistir_relatorio(relatorio, run_dir)
    _imprimir_resumo(relatorio, json_path, md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
