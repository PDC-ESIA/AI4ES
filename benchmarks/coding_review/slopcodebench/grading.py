"""Avaliação de um checkpoint pelo protocolo OFICIAL do SlopCodeBench.

Filosofia: nada de grading é reimplementado aqui. Este módulo é uma camada fina
sobre o harness oficial (`slop_code`) e chama as MESMAS funções que o runner
oficial chama a cada checkpoint:

- ``evaluate_agent_snapshot``: roda a suíte oculta do checkpoint (core,
  functionality, error e regressão dos checkpoints anteriores) no container
  Docker do ambiente e calcula as métricas de qualidade do snapshot;
- ``PassPolicy.ANY``: política padrão do harness — a trajetória para quando um
  checkpoint passa em zero testes (os restantes contam como não resolvidos);
- ``create_problem_reports`` + ``update_results_jsonl``: consolidam cada
  checkpoint numa linha de ``checkpoint_results.jsonl`` (pass rates, diff,
  churn, verbosidade e erosão via ``scb-check``).

**Por que subprocesso.** O harness não cabe no venv do `adk` sem mudar
dependências do projeto (ele rebaixa `litellm` e OpenTelemetry). Por isso ele
tem venv próprio (Python 3.12, criado pelo ``uv.lock`` dos autores): na primeira
execução, ``ensure_harness`` baixa o commit fixado para ``datasets/`` (fora do
git) e roda ``uv sync``, como o HumanEval faz com o dataset.
``SCBENCH_HARNESS_PATH`` permite usar outro checkout. Este arquivo tem duas
metades:

- **lado do benchmark** (funções públicas): roda no venv do `adk`, junto do
  coder, e delega cada operação ao venv do harness;
- **lado do harness** (``_h_*`` + ``main``): roda no venv do harness, como
  ``python -m benchmarks.coding_review.slopcodebench.grading <operação>``,
  recebendo JSON pela entrada padrão e gravando JSON num arquivo de saída.

O template de prompt e a especificação do ambiente são lidos dos arquivos
oficiais do próprio checkout (``configs/``), não copiados para cá.

**Python 3.12.** O lado do harness importa este arquivo (e ``dataset.py``) num
interpretador 3.12, enquanto o ``ruff`` do projeto formata para 3.14. Não use
aqui sintaxe exclusiva de 3.13+ — em especial ``except A, B:`` sem parênteses,
que o ``ruff format`` produz a partir de ``except (A, B):``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .dataset import (
    DEFAULT_DATASETS_DIR,
    DOWNLOAD_MARKER,
    ScbProblem,
    download_tarball,
    mark_complete,
    source_commit,
)

HARNESS_PATH_ENV = "SCBENCH_HARNESS_PATH"
# Commit fixado do harness oficial (SprocketLab/slop-code-bench).
HARNESS_COMMIT = "31ceea3add480edb33431e70475c4c70597e6b31"
HARNESS_URL = (
    f"https://github.com/SprocketLab/slop-code-bench/archive/{HARNESS_COMMIT}.tar.gz"
)
PROMPT_TEMPLATE = "just-solve"
ENVIRONMENT_NAME = "docker-python3.12-uv"
PASS_POLICY = "any"
SNAPSHOT_DIR_NAME = "snapshot"
INFERENCE_RESULT_FILENAME = "inference_result.json"
CHECKPOINT_RESULTS_FILENAME = "checkpoint_results.jsonl"

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MODULE = "benchmarks.coding_review.slopcodebench.grading"


@dataclass
class GradeResult:
    """Veredito oficial de um checkpoint."""

    passed_policy: bool
    pass_counts: dict[str, int] = field(default_factory=dict)
    total_counts: dict[str, int] = field(default_factory=dict)
    error: str | None = None


# ---------------------------------------------------------------------------
# Lado do benchmark (venv do adk)
# ---------------------------------------------------------------------------


def _uv_sync(raiz: Path) -> None:
    """Cria o venv do harness a partir do `uv.lock` dos próprios autores."""
    # O venv do adk (se ativado) não pode ser confundido com o do harness.
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    subprocess.run(
        ["uv", "sync", "--frozen", "--python", "3.12", "--project", str(raiz)],
        check=True,
        env=env,
    )


def ensure_harness(
    datasets_dir: Path = DEFAULT_DATASETS_DIR,
    *,
    url: str = HARNESS_URL,
    sync=_uv_sync,
) -> Path:
    """Garante o harness no commit fixado, baixando e instalando se preciso.

    Como o catálogo (e o dataset do HumanEval), fica em `datasets/`, fora do
    git. O venv do harness é próprio (Python 3.12, `uv.lock` dos autores) e não
    toca o venv do `adk`.

    Returns:
        Diretório do harness (``datasets/slop-code-bench-<commit>``).
    """
    destino = datasets_dir / f"slop-code-bench-{HARNESS_COMMIT}"
    if (destino / DOWNLOAD_MARKER).is_file():
        return destino

    print(f"[harness] Baixando o harness oficial do SlopCodeBench de {url} …")
    download_tarball(url, destino)
    print("[harness] Instalando o venv do harness (Python 3.12, uv.lock dos autores) …")
    sync(destino)
    mark_complete(destino, HARNESS_COMMIT)
    print(f"[harness] Harness pronto em {destino}.")
    return destino


def harness_root() -> Path:
    """Harness oficial: `SCBENCH_HARNESS_PATH` se definido, senão o download fixado."""
    valor = os.environ.get(HARNESS_PATH_ENV)
    raiz = Path(valor).expanduser().resolve() if valor else ensure_harness()
    if not _harness_python(raiz).is_file():
        raise FileNotFoundError(
            f"Venv do harness não encontrado em {raiz}/.venv. Rode "
            f"`uv sync --frozen --python 3.12 --project {raiz}`."
        )
    return raiz


def _harness_python(raiz: Path) -> Path:
    return raiz / ".venv" / "bin" / "python"


def _chamar_harness(operacao: str, payload: dict) -> dict:
    """Executa uma operação no venv do harness e devolve o resultado (JSON)."""
    raiz = harness_root()
    with tempfile.TemporaryDirectory() as tmp:
        saida = Path(tmp) / "out.json"
        env = {**os.environ, HARNESS_PATH_ENV: str(raiz)}
        # O PYTHONPATH do processo do benchmark (adk/) não pode vazar para o
        # interpretador do harness.
        env.pop("PYTHONPATH", None)
        proc = subprocess.run(
            [str(_harness_python(raiz)), "-m", _MODULE, operacao, str(saida)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=_REPO_ROOT,
            env=env,
        )
        if proc.returncode != 0 or not saida.is_file():
            raise RuntimeError(
                f"Operação '{operacao}' do harness falhou (exit={proc.returncode}):\n"
                f"{(proc.stderr or proc.stdout)[-3000:]}"
            )
        return json.loads(saida.read_text(encoding="utf-8"))


def check_harness() -> dict:
    """Pre-flight: o harness importa e o ambiente oficial é carregável."""
    return _chamar_harness("check", {})


def provenance() -> dict:
    """Versão/commit do harness e versão do `scb-check` (para o metadata.json)."""
    return _chamar_harness("provenance", {})


def render_prompt(
    problem: ScbProblem, checkpoint: str, *, is_first_checkpoint: bool
) -> tuple[str, str]:
    """Prompt oficial do checkpoint e nome do arquivo de entrada (ex.: ``launch.py``)."""
    r = _chamar_harness(
        "render",
        {
            "problem_path": str(problem.path),
            "checkpoint": checkpoint,
            "is_first_checkpoint": is_first_checkpoint,
        },
    )
    return r["prompt"], r["entry_file"]


def checkpoint_output_dir(
    problem: ScbProblem, problem_run_dir: Path, checkpoint: str
) -> Path:
    """Diretório do checkpoint no layout oficial (criado se não existir)."""
    r = _chamar_harness(
        "checkpoint_dir",
        {
            "problem_path": str(problem.path),
            "problem_run_dir": str(problem_run_dir),
            "checkpoint": checkpoint,
        },
    )
    return Path(r["path"])


def write_inference_result(
    save_dir: Path,
    *,
    started: datetime,
    completed: datetime,
    prompt_tokens: int,
    completion_tokens: int,
    cached_tokens: int,
    reasoning_tokens: int,
    steps: int,
    had_error: bool,
    error_message: str | None,
) -> None:
    """Grava o `inference_result.json` no formato oficial (tokens, tempo, erro).

    O custo em USD fica 0: o workflow não expõe preço por modelo. Os tokens são
    registrados integralmente.
    """
    _chamar_harness(
        "inference_result",
        {
            "save_dir": str(save_dir),
            "started": started.isoformat(),
            "completed": completed.isoformat(),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cached_tokens": cached_tokens,
            "reasoning_tokens": reasoning_tokens,
            "steps": steps,
            "had_error": had_error,
            "error_message": error_message,
        },
    )


def grade_checkpoint(
    problem: ScbProblem, checkpoint: str, save_dir: Path
) -> GradeResult:
    """Avalia o snapshot de um checkpoint com a suíte oculta oficial."""
    try:
        r = _chamar_harness(
            "grade",
            {
                "problem_path": str(problem.path),
                "checkpoint": checkpoint,
                "save_dir": str(save_dir),
            },
        )
    except Exception as exc:  # noqa: BLE001 — falha de avaliação vira dado
        return GradeResult(passed_policy=False, error=f"{type(exc).__name__}: {exc}")
    return GradeResult(**r)


def build_checkpoint_results(
    scb_run_dir: Path,
    problems: list[ScbProblem],
    results_file: Path,
    states: dict[str, dict[str, str]],
) -> list[dict]:
    """Consolida todos os checkpoints avaliados em `checkpoint_results.jsonl`.

    Args:
        states: ``{problema: {checkpoint: "ran" | "error" | "skipped"}}``, os
            estados que o runner oficial registra em `run_info.yaml`.
    """
    _chamar_harness(
        "results",
        {
            "scb_run_dir": str(scb_run_dir),
            "problem_paths": [str(p.path) for p in problems],
            "results_file": str(results_file),
            "states": states,
        },
    )
    if not results_file.is_file():
        return []
    return [
        json.loads(linha)
        for linha in results_file.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]


def progress_bins(pares: list[tuple[str, str]]) -> list[float]:
    """Fase de progresso de cada (problema, checkpoint), via `compute_progress_bins`."""
    r = _chamar_harness("progress_bins", {"pairs": [list(p) for p in pares]})
    return r["bins"]


# ---------------------------------------------------------------------------
# Lado do harness (venv do slop-code-bench)
# ---------------------------------------------------------------------------


def _h_root() -> Path:
    return Path(os.environ[HARNESS_PATH_ENV])


def _h_environment():
    from slop_code.entrypoints.config import loader as config_loader

    return config_loader.resolve_environment(
        _h_root() / "configs" / "environments" / f"{ENVIRONMENT_NAME}.yaml"
    )


def _h_problem_and_checkpoint(payload: dict):
    from slop_code.evaluation import ProblemConfig

    problem_config = ProblemConfig.from_yaml(Path(payload["problem_path"]))
    checkpoint = dict(problem_config.iterate_checkpoint_items())[payload["checkpoint"]]
    return problem_config, checkpoint


def _h_docker_ready():
    """Ambiente oficial com a imagem base construída (`slop-code:<ambiente>`).

    É o mesmo passo que todo comando `eval` oficial faz antes de avaliar; sem
    ele o `docker run` falha por imagem inexistente.
    """
    from slop_code.entrypoints.commands import common

    environment = _h_environment()
    common.ensure_docker_ready(environment)
    return environment


def _h_check(_payload: dict) -> dict:
    _h_docker_ready()
    return {"ok": True}


def _h_provenance(_payload: dict) -> dict:
    import importlib.metadata as md

    from slop_code.metrics.checkpoint.driver import SCB_CHECK_VERSION

    return {
        "version": md.version("slop-code-bench"),
        "commit": source_commit(_h_root()),
        "scb_check_version": SCB_CHECK_VERSION,
    }


def _h_render(payload: dict) -> dict:
    from slop_code.common.render import render_prompt as _render

    problem_config, _ = _h_problem_and_checkpoint(payload)
    environment = _h_environment()
    template = (
        _h_root() / "configs" / "prompts" / f"{PROMPT_TEMPLATE}.jinja"
    ).read_text(encoding="utf-8")
    prompt = _render(
        spec_text=problem_config.get_checkpoint_spec(payload["checkpoint"]),
        context={
            "is_continuation": not payload["is_first_checkpoint"],
            "agent_type": "cr_coder",
            "agent_version": "",
            "model_name": None,
        },
        prompt_template=template,
        entry_file=environment.format_entry_file(problem_config.entry_file),
        entry_command=environment.get_command(
            problem_config.entry_file, is_agent_run=True
        ),
    )
    return {
        "prompt": prompt,
        "entry_file": environment.format_entry_file(problem_config.entry_file),
    }


def _h_checkpoint_dir(payload: dict) -> dict:
    import yaml
    from slop_code import common
    from slop_code.agent_runner import reporting

    problem_config, checkpoint = _h_problem_and_checkpoint(payload)
    problem_run_dir = Path(payload["problem_run_dir"])
    problem_run_dir.mkdir(parents=True, exist_ok=True)

    # `problem.yaml`, como o runner oficial grava no início de cada problema
    # (mesma serialização de `reporting.setup_output_directory`); a
    # consolidação oficial exige este arquivo.
    problem_yaml = problem_run_dir / common.PROBLEM_CONFIG_NAME
    if not problem_yaml.is_file():
        with problem_yaml.open("w") as f:
            yaml.dump(
                common.serialize_path_dict(problem_config.model_dump(mode="json")),
                f,
                indent=2,
                sort_keys=True,
            )

    path = reporting.setup_checkpoint_output_directory(
        checkpoint=checkpoint, output_path=problem_run_dir
    )
    return {"path": str(path)}


def _h_inference_result(payload: dict) -> dict:
    from slop_code.agent_runner.agent import CheckpointInferenceResult
    from slop_code.agent_runner.models import UsageTracker
    from slop_code.common.llms import TokenUsage

    save_dir = Path(payload["save_dir"])
    started = datetime.fromisoformat(payload["started"])
    completed = datetime.fromisoformat(payload["completed"])
    usage = UsageTracker(
        steps=payload["steps"],
        net_tokens=TokenUsage(
            input=payload["prompt_tokens"],
            output=payload["completion_tokens"],
            cache_read=payload["cached_tokens"],
            reasoning=payload["reasoning_tokens"],
        ),
    )
    resultado = CheckpointInferenceResult(
        started=started,
        completed=completed,
        elapsed=(completed - started).total_seconds(),
        usage=usage,
        had_error=payload["had_error"],
        error_message=payload["error_message"],
        checkpoint_path=save_dir.resolve(),
        snapshot_dir=Path(SNAPSHOT_DIR_NAME),
    )
    (save_dir / INFERENCE_RESULT_FILENAME).write_text(
        resultado.model_dump_json(indent=2), encoding="utf-8"
    )
    return {"ok": True}


def _h_grade(payload: dict) -> dict:
    from slop_code.agent_runner.runner import evaluate_agent_snapshot
    from slop_code.evaluation import PassPolicy

    problem_config, checkpoint = _h_problem_and_checkpoint(payload)
    save_dir = Path(payload["save_dir"])
    report, _quality = evaluate_agent_snapshot(
        checkpoint=checkpoint,
        save_dir=save_dir,
        snapshot_dir=save_dir / SNAPSHOT_DIR_NAME,
        problem=problem_config,
        environment=_h_docker_ready(),
    )
    if report.infrastructure_failure:
        # O pytest nem chegou a rodar (ex.: container não subiu): não é um
        # veredito sobre o código. Detalhes em <save_dir>/evaluation/stderr.txt.
        raise RuntimeError(
            "Falha de infraestrutura na avaliação oficial; ver "
            f"{save_dir / 'evaluation' / 'stderr.txt'}"
        )

    def _grupos(contagens) -> dict:
        return {getattr(k, "value", str(k)): v for k, v in contagens.items()}

    return {
        "passed_policy": PassPolicy(PASS_POLICY).check(
            report.pass_counts, report.total_counts
        ),
        "pass_counts": _grupos(report.pass_counts),
        "total_counts": _grupos(report.total_counts),
    }


def _h_results(payload: dict) -> dict:
    import yaml
    from slop_code import common
    from slop_code.entrypoints import evaluation as evaluation_entry
    from slop_code.entrypoints.commands import repopulate_diffs
    from slop_code.entrypoints.evaluation.metrics import update_results_jsonl
    from slop_code.evaluation import ProblemConfig

    results_file = Path(payload["results_file"])
    if results_file.exists():
        results_file.unlink()

    reports: list = []
    for problem_path in map(Path, payload["problem_paths"]):
        problem_dir = Path(payload["scb_run_dir"]) / problem_path.name
        if not problem_dir.is_dir():
            continue
        # `run_info.yaml` com o estado de cada checkpoint (ran/error/skipped),
        # a parte de `reporting.save_results` que a consolidação oficial lê.
        estados = payload["states"].get(problem_path.name, {})
        with (problem_dir / common.RUN_INFO_FILENAME).open("w") as f:
            yaml.dump({"summary": {"checkpoints": estados}}, f, sort_keys=True)
        # `diff.json` de cada checkpoint (snapshot vs. snapshot anterior), de
        # onde saem `lines_added`/`lines_removed`/`churn_ratio`. O runner
        # oficial o grava ao fechar o checkpoint; aqui usamos a lógica do
        # comando oficial `slop-code repopulate-diffs`.
        repopulate_diffs._process_problem(problem_dir)
        problem_reports, _ = evaluation_entry.create_problem_reports(
            problem_dir, ProblemConfig.from_yaml(problem_path)
        )
        reports.extend(problem_reports)

    if reports:
        update_results_jsonl(results_file, reports)
    return {"reports": len(reports)}


def _h_progress_bins(payload: dict) -> dict:
    import pandas as pd
    from slop_code.visualization.data_transforms import compute_progress_bins

    df = compute_progress_bins(
        pd.DataFrame(payload["pairs"], columns=["problem", "checkpoint"])
    )
    return {"bins": [float(b) for b in df["progress_bin"]]}


_OPERACOES = {
    "check": _h_check,
    "provenance": _h_provenance,
    "render": _h_render,
    "checkpoint_dir": _h_checkpoint_dir,
    "inference_result": _h_inference_result,
    "grade": _h_grade,
    "results": _h_results,
    "progress_bins": _h_progress_bins,
}


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada no venv do harness: ``<operação> <arquivo-de-saída>``."""
    operacao, saida = argv if argv is not None else sys.argv[1:]
    resultado = _OPERACOES[operacao](json.loads(sys.stdin.read() or "{}"))
    Path(saida).write_text(json.dumps(resultado, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
