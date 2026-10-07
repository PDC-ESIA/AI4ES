"""Correção pelo harness OFICIAL do SWE-bench (não reimplementamos o grading).

O pacote `swebench` roda num venv SEPARADO, chamado por subprocesso:
- o `adk/` usa Python 3.14, e o `swebench` não declara suporte a essa versão;
- isola as dependências do harness (docker, datasets, etc.) das do projeto.
A versão é fixada (`SWEBENCH_VERSION`) e conferida antes da correção.

Fluxo:
1. `write_predictions` grava o `predictions.jsonl` (uma linha por instância,
   inclusive as de patch vazio — o harness as contabiliza como `empty_patch`);
2. `build_command` monta a chamada ao `swebench.harness.run_evaluation`,
   passando o MESMO parquet fixado que o benchmark usou (o harness aceita um
   `.parquet` local como `--dataset_name`), para que execução e gabarito usem os
   mesmos dados;
3. `parse_results` lê o `report.json` POR INSTÂNCIA em
   `logs/run_evaluation/<run_id>/<modelo>/<instance_id>/report.json` — formato
   estável entre versões — em vez do relatório agregado, cujo nome e local
   mudaram entre a v4 e a v5. Sem report, o `run_instance.log` diz se o patch
   não aplicou ou se os testes estouraram o timeout (não resolvida, como no
   SWE-bench) ou se foi erro de avaliação.

Verificado contra o código do `swebench` 5.0.2 (`harness/run_evaluation.py`,
`harness/reporting.py`, `harness/grading.py`, `harness/utils.py`).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .metrics import (
    GRADE_EMPTY_PATCH,
    GRADE_ERROR,
    GRADE_RESOLVED,
    GRADE_UNRESOLVED,
)

SWEBENCH_VERSION = "5.0.2"
_LOG_DIR = Path("logs") / "run_evaluation"
_REPORT_FILE = "report.json"
_INSTANCE_LOG = "run_instance.log"
GRADING_LOG = "run_evaluation.log"

# Quando o patch não aplica ou os testes estouram o timeout, o harness levanta
# `EvaluationError` ANTES de gravar o report.json e registra o motivo no log da
# instância (`harness/run_evaluation.py`, `constants.APPLY_PATCH_FAIL`). O
# SWE-bench conta essas instâncias como não resolvidas; aqui também — elas
# julgam o patch, não a infraestrutura. Qualquer outra ausência de report é
# erro de avaliação.
_MARCADORES_NAO_RESOLVIDA = (
    (">>>>> Patch Apply Failed", "patch_nao_aplicou",
     "O patch não aplicou no /testbed do harness oficial."),
    ("Test timed out after", "timeout_dos_testes",
     "Os testes oficiais estouraram o timeout da correção."),
)


class GradingError(RuntimeError):
    """O harness oficial não pôde ser executado."""


@dataclass
class GradeOutcome:
    """Resultado oficial de uma instância."""

    status: str
    resolved: bool
    patch_applied: bool | None = None
    detail: str = ""
    cause: str | None = None

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "resolvido": self.resolved,
            "patch_aplicado": self.patch_applied,
            "detalhe": self.detail,
            "causa": self.cause,
        }


def write_predictions(
    path: Path, patches: Iterable[tuple[str, str]], *, model_name_or_path: str
) -> None:
    """Grava `predictions.jsonl` no formato do SWE-bench."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for instance_id, patch in patches:
            linha = {
                "instance_id": instance_id,
                "model_name_or_path": model_name_or_path,
                "model_patch": patch,
            }
            fh.write(json.dumps(linha, ensure_ascii=False) + "\n")


def build_command(
    python: str,
    *,
    dataset_path: Path,
    predictions_path: Path | str,
    run_id: str,
    instance_ids: list[str],
    max_workers: int,
    timeout: int,
) -> list[str]:
    """Linha de comando do `run_evaluation` (executada com cwd = diretório de grading)."""
    return [
        python,
        "-m",
        "swebench.harness.run_evaluation",
        "--dataset_name",
        str(dataset_path),
        "--predictions_path",
        str(predictions_path),
        "--run_id",
        run_id,
        "--max_workers",
        str(max_workers),
        "--timeout",
        str(timeout),
        "--report_dir",
        ".",
        "--instance_ids",
        *instance_ids,
    ]


def installed_version(python: str) -> str:
    """Versão do `swebench` instalada no interpretador informado."""
    try:
        saida = subprocess.run(
            [
                python,
                "-c",
                "import importlib.metadata as m; print(m.version('swebench'))",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GradingError(
            f"`swebench` indisponível em {python!r}. Crie o venv do harness "
            f"oficial (ver README) e instale `swebench=={SWEBENCH_VERSION}`."
        ) from exc
    return saida.stdout.strip()


def run_official_grading(command: list[str], *, grading_dir: Path) -> int:
    """Executa o harness oficial; a saída vai para `run_evaluation.log`."""
    grading_dir.mkdir(parents=True, exist_ok=True)
    with (grading_dir / GRADING_LOG).open("w", encoding="utf-8") as log:
        processo = subprocess.run(
            command, cwd=grading_dir, stdout=log, stderr=subprocess.STDOUT
        )
    return processo.returncode


def instance_report_path(
    grading_dir: Path, run_id: str, model_name_or_path: str, instance_id: str
) -> Path:
    """Onde o harness grava o `report.json` de uma instância."""
    modelo = model_name_or_path.replace("/", "__")
    return grading_dir / _LOG_DIR / run_id / modelo / instance_id / _REPORT_FILE


def _outcome_sem_report(log_path: Path) -> GradeOutcome:
    """Classifica uma instância sem report.json pelo log dela."""
    try:
        log = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        log = ""
    for marcador, causa, detalhe in _MARCADORES_NAO_RESOLVIDA:
        if marcador in log:
            aplicou = causa != "patch_nao_aplicou"
            return GradeOutcome(GRADE_UNRESOLVED, False, aplicou, detalhe, causa)
    return GradeOutcome(
        GRADE_ERROR, False, None, "report.json ausente e sem causa conhecida no log.",
        "erro_de_avaliacao",
    )


def parse_results(
    grading_dir: Path,
    *,
    run_id: str,
    model_name_or_path: str,
    instance_ids: list[str],
    empty_patch_ids: set[str],
) -> dict[str, GradeOutcome]:
    """Resultado oficial de cada instância, a partir dos `report.json`."""
    resultados: dict[str, GradeOutcome] = {}
    for instance_id in instance_ids:
        if instance_id in empty_patch_ids:
            resultados[instance_id] = GradeOutcome(
                GRADE_EMPTY_PATCH, False, None, "Patch vazio: não avaliado pelo harness."
            )
            continue

        caminho = instance_report_path(grading_dir, run_id, model_name_or_path, instance_id)
        if not caminho.is_file():
            resultados[instance_id] = _outcome_sem_report(caminho.with_name(_INSTANCE_LOG))
            continue
        try:
            entrada = json.loads(caminho.read_text(encoding="utf-8"))[instance_id]
            resolvido = bool(entrada["resolved"])
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            resultados[instance_id] = GradeOutcome(
                GRADE_ERROR, False, None, f"report.json ilegível: {exc!r}",
                "erro_de_avaliacao",
            )
            continue
        resultados[instance_id] = GradeOutcome(
            GRADE_RESOLVED if resolvido else GRADE_UNRESOLVED,
            resolvido,
            entrada.get("patch_successfully_applied"),
        )
    return resultados
