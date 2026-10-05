"""Agregação das três métricas da issue a partir das saídas OFICIAIS do SlopCodeBench.

Nenhuma métrica é calculada do zero: todos os valores por checkpoint vêm das
linhas de ``checkpoint_results.jsonl`` produzidas pelo harness oficial. Aqui só
se agrega (contagens, médias, medianas, fases de progresso).

1. **Correção ao longo do horizonte** — ``strict_pass_rate`` (inclui regressão, "strict"),
   ``isolated_pass_rate`` (sem regressão, "isolated"), ``core_pass_rate`` e
   ``regression_passed/regression_total``; "quebrou o que funcionava" compara
   teste a teste (``regression_breaks``). Um checkpoint é "resolvido" quando a
   taxa correspondente é 1.0. Os solve rates usam como denominador TODOS os
   checkpoints previstos; os que não rodaram (early stop) contam como não
   resolvidos, como na Tabela 1 do paper.
2. **Crescimento do diff** — ``lines_added``, ``lines_removed``, ``delta.loc`` e
   ``delta.churn_ratio`` (este só a partir do 2º checkpoint).
3. **Slop** — ``verbosity`` e ``erosion`` do ``scb-check``, com os componentes
   ``cloned_pct``, ``verbosity_flagged_pct`` e ``mass.high_cc_pct``. Checkpoints
   sem workspace avaliado são excluídos, não imputados (seção 2.4 do paper).

As fases usam ``compute_progress_bins`` do próprio harness: progresso =
índice do checkpoint / nº de checkpoints do problema, em 5 faixas (20%…100%).
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from pathlib import Path
from statistics import mean, median

from .dataset import ScbProblem

# Recebe [(problema, checkpoint), ...] e devolve a faixa de progresso de cada um.
# Em produção é `grading.progress_bins` (que roda `compute_progress_bins` no
# harness); injetado para que a agregação não dependa do harness instalado.
ProgressBins = Callable[[list[tuple[str, str]]], list[float]]

CORRECTNESS_FIELDS = ("strict_pass_rate", "isolated_pass_rate", "core_pass_rate")
DIFF_FIELDS = ("lines_added", "lines_removed", "delta.loc", "delta.churn_ratio")
SLOP_FIELDS = (
    "verbosity",
    "erosion",
    "cloned_pct",
    "verbosity_flagged_pct",
    "mass.high_cc_pct",
)
SOLVE_KINDS = {
    "strict": "strict_pass_rate",
    "iso": "isolated_pass_rate",
    "core": "core_pass_rate",
}

# Referência do paper (Tabela 2), apenas para contexto no relatório.
PAPER_REFERENCE = {
    "human_panel": {"verbosity": 0.19, "erosion": 0.34},
    "agent_checkpoints": {"verbosity": 0.44, "erosion": 0.68},
    "pct_trajectories_rising": {"erosion": 77.0, "verbosity": 75.5},
}


def get_field(row: dict | None, key: str) -> float | None:
    """Lê um campo numérico, aceitando chave plana (`delta.loc`) ou aninhada."""
    if row is None:
        return None
    valor = row.get(key)
    if valor is None and "." in key:
        atual: object = row
        for parte in key.split("."):
            atual = atual.get(parte) if isinstance(atual, dict) else None
        valor = atual
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    if math.isnan(valor) or math.isinf(valor):
        return None
    return float(valor)


def _ran(row: dict | None) -> bool:
    return row is not None and row.get("state") == "ran"


def _stats(valores: list[float]) -> dict:
    if not valores:
        return {"count": 0, "mean": None, "median": None}
    return {
        "count": len(valores),
        "mean": round(mean(valores), 4),
        "median": round(median(valores), 4),
    }


def _index_rows(rows: list[dict]) -> dict[tuple[str, str], dict]:
    return {(r["problem"], r["checkpoint"]): r for r in rows}


def _expected(
    problems: list[ScbProblem], rows: list[dict]
) -> list[tuple[ScbProblem, str, dict | None]]:
    """Todos os checkpoints previstos, com a linha oficial (ou None se não rodou)."""
    indice = _index_rows(rows)
    return [
        (problem, checkpoint, indice.get((problem.name, checkpoint)))
        for problem in problems
        for checkpoint in problem.checkpoints
    ]


def _solved(row: dict | None, field: str) -> bool:
    return _ran(row) and get_field(row, field) == 1.0


def _testes(grupos: dict, situacao: str, *, so_regressao: bool = False) -> set:
    """Testes de um `evaluation.json` como (checkpoint de origem, nome)."""
    return {
        (chave.split("-", 1)[0], nome)
        for chave, grupo in grupos.items()
        if not so_regressao or chave.endswith("-Regression")
        for nome in grupo.get(situacao, [])
    }


def regression_breaks(
    scb_run_dir: Path, problems: list[ScbProblem]
) -> dict[tuple[str, str], dict[str, int]]:
    """Testes que passavam no checkpoint anterior e falharam na regressão.

    Responde "o agente quebrou o que já funcionava?" a partir do resultado
    TESTE A TESTE da avaliação oficial (`evaluation.json`, campo `tests`), sem
    métrica nova. As contagens agregadas (`regression_passed/total`) não servem
    para isso: a regressão repete todos os testes anteriores, inclusive os que
    nunca passaram.

    Returns:
        ``{(problema, checkpoint): {"passavam": n, "quebraram": m}}``, só para
        checkpoints com testes de regressão e com o checkpoint anterior avaliado.
    """
    resultado: dict[tuple[str, str], dict[str, int]] = {}
    for problem in problems:
        passaram_antes: set | None = None
        for checkpoint in problem.checkpoints:
            arquivo = scb_run_dir / problem.name / checkpoint / "evaluation.json"
            if not arquivo.is_file():
                passaram_antes = None
                continue
            grupos = json.loads(arquivo.read_text(encoding="utf-8")).get("tests", {})
            retestados = _testes(grupos, "passed", so_regressao=True) | _testes(
                grupos, "failed", so_regressao=True
            )
            if passaram_antes is not None and retestados:
                passavam = passaram_antes & retestados
                quebraram = passavam & _testes(grupos, "failed", so_regressao=True)
                resultado[(problem.name, checkpoint)] = {
                    "passavam": len(passavam),
                    "quebraram": len(quebraram),
                }
            passaram_antes = _testes(grupos, "passed")
    return resultado


def _per_phase(
    esperados: list[tuple[ScbProblem, str, dict | None]],
    progress_bins: ProgressBins,
) -> dict[str, dict]:
    """Agrupa por fase de progresso (`compute_progress_bins` oficial)."""
    bins = progress_bins([(p.name, c) for p, c, _ in esperados])
    fases: dict[str, dict] = {}
    for (_problem, _checkpoint, row), bin_ in zip(esperados, bins, strict=True):
        chave = f"{round(bin_ * 100)}%"
        fase = fases.setdefault(chave, {"checkpoints": 0, "rows": []})
        fase["checkpoints"] += 1
        fase["rows"].append(row)

    resultado: dict[str, dict] = {}
    for chave in sorted(fases, key=lambda k: int(k.rstrip("%"))):
        fase_rows = fases[chave]["rows"]
        total = fases[chave]["checkpoints"]
        ran = [r for r in fase_rows if _ran(r)]
        resultado[chave] = {
            "checkpoints": total,
            "ran": len(ran),
            **{
                f"pct_{tipo}_solved": round(
                    100 * sum(_solved(r, campo) for r in fase_rows) / total, 2
                )
                for tipo, campo in SOLVE_KINDS.items()
            },
            **{
                campo: _stats(
                    [v for r in ran if (v := get_field(r, campo)) is not None]
                )
                for campo in (*DIFF_FIELDS, *SLOP_FIELDS)
            },
        }
    return resultado


def _pct_rising(
    problems: list[ScbProblem], indice: dict[tuple[str, str], dict], campo: str
) -> dict:
    """Fração de trajetórias em que `campo` sobe do 1º ao último checkpoint rodado."""
    subiu = elegiveis = 0
    for problem in problems:
        valores = [
            v
            for c in problem.checkpoints
            if _ran(row := indice.get((problem.name, c)))
            and (v := get_field(row, campo)) is not None
        ]
        if len(valores) < 2:
            continue
        elegiveis += 1
        subiu += valores[-1] > valores[0]
    return {
        "trajectories": elegiveis,
        "rising": subiu,
        "pct": round(100 * subiu / elegiveis, 2) if elegiveis else None,
    }


def aggregate(
    rows: list[dict],
    problems: list[ScbProblem],
    progress_bins: ProgressBins,
    breaks: dict[tuple[str, str], dict[str, int]] | None = None,
) -> dict:
    """Agrega as linhas oficiais nas três seções do relatório.

    Args:
        breaks: saída de `regression_breaks` (testes que passavam e quebraram).
    """
    esperados = _expected(problems, rows)
    indice = _index_rows(rows)
    total = len(esperados)
    ran = [r for _, _, r in esperados if _ran(r)]
    breaks = breaks or {}
    com_base = [b for b in breaks.values() if b["passavam"]]
    por_problema = []
    for problem in problems:
        linhas = [indice.get((problem.name, c)) for c in problem.checkpoints]
        rodadas = [r for r in linhas if _ran(r)]
        por_problema.append(
            {
                "problem": problem.name,
                "checkpoints_expected": problem.num_checkpoints,
                "checkpoints_ran": len(rodadas),
                "strict_solved": sum(_solved(r, "strict_pass_rate") for r in linhas),
                "final_loc": get_field(rodadas[-1], "loc") if rodadas else None,
            }
        )

    correcao = {
        "checkpoints_expected": total,
        "checkpoints_ran": len(ran),
        **{
            f"pct_checkpoints_{tipo}_solved": round(
                100 * sum(_solved(r, campo) for _, _, r in esperados) / total, 2
            )
            if total
            else None
            for tipo, campo in SOLVE_KINDS.items()
        },
        "problems_partial": sum(p["strict_solved"] > 0 for p in por_problema),
        "problems_solved": sum(
            p["strict_solved"] == p["checkpoints_expected"] for p in por_problema
        ),
        "regression": {
            "checkpoints_with_regression_tests": len(breaks),
            # Checkpoints em que algum teste passava antes (há o que quebrar).
            "checkpoints_with_prior_passing_tests": len(com_base),
            "checkpoints_that_broke_prior_work": sum(
                b["quebraram"] > 0 for b in com_base
            ),
            "tests_previously_passing": sum(b["passavam"] for b in com_base),
            "tests_broken": sum(b["quebraram"] for b in com_base),
            "mean_regression_pass_rate": _stats(
                [
                    get_field(r, "regression_passed") / get_field(r, "regression_total")
                    for r in ran
                    if get_field(r, "regression_total")
                ]
            )["mean"],
        },
        **{
            campo: _stats([v for r in ran if (v := get_field(r, campo)) is not None])
            for campo in CORRECTNESS_FIELDS
        },
    }

    diff = {
        campo: _stats([v for r in ran if (v := get_field(r, campo)) is not None])
        for campo in DIFF_FIELDS
    }

    slop = {
        **{
            campo: _stats([v for r in ran if (v := get_field(r, campo)) is not None])
            for campo in SLOP_FIELDS
        },
        "pct_trajectories_rising": {
            campo: _pct_rising(problems, indice, campo)
            for campo in ("erosion", "verbosity")
        },
        "paper_reference": PAPER_REFERENCE,
    }

    return {
        "correctness": correcao,
        "diff": diff,
        "slop": slop,
        "by_phase": _per_phase(esperados, progress_bins) if esperados else {},
        "by_problem": por_problema,
        "by_checkpoint": [
            {
                "problem": problem.name,
                "checkpoint": checkpoint,
                "state": row.get("state") if row else "not_run",
                "tests_previously_passing": breaks.get(
                    (problem.name, checkpoint), {}
                ).get("passavam"),
                "tests_broken": breaks.get((problem.name, checkpoint), {}).get(
                    "quebraram"
                ),
                **{
                    campo: get_field(row, campo)
                    for campo in (
                        *CORRECTNESS_FIELDS,
                        "regression_passed",
                        "regression_total",
                        *DIFF_FIELDS,
                        *SLOP_FIELDS,
                    )
                },
            }
            for problem, checkpoint, row in esperados
        ],
    }
