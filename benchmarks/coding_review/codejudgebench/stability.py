"""Estabilidade entre execuções repetidas da mesma configuração (#421).

Uso (a partir da raiz do repositório):

    python -m benchmarks.coding_review.codejudgebench.stability <run_1> <run_2> <run_3> [...]

Os runs devem ter avaliado os mesmos pares com o mesmo reviewer e o mesmo
modelo. Responde duas perguntas diferentes:

- **O número agregado é estável?** Média e desvio padrão de cada métrica
  entre as execuções.
- **O veredito individual é estável?** Quantos pares têm o mesmo desfecho em
  todas as execuções, e quantas respostas recebem sempre o mesmo veredito.

Também calcula o voto da maioria (o veredito mais frequente de cada resposta),
para saber se repetir a revisão e votar melhoraria o resultado.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from benchmarks.coding_review.codejudgebench.metrics import wilson_interval

_METRICAS = (
    ("accuracy", "Acurácia do julgamento", lambda p: p["outcome"] == "correct"),
    ("false_approve", "Aprovou código que falha nos testes", lambda p: p["neg"]["verdict"] == "pass"),
    ("false_block", "Bloqueou código que passa nos testes", lambda p: p["pos"]["verdict"] == "fail"),
)


def _carregar(run_dir: Path) -> dict[str, dict]:
    relatorio = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    return {p["pair_id"]: p for p in relatorio["pairs"]}


def _maioria(vereditos: list[str]) -> str:
    """Veredito mais frequente; empate desempata pela ordem de aparição."""
    return max(dict.fromkeys(vereditos), key=vereditos.count)


def stability(run_dirs: list[Path]) -> dict:
    if len(run_dirs) < 2:
        raise ValueError("Informe ao menos duas execuções.")
    runs = [_carregar(d) for d in run_dirs]
    ids = sorted(set.intersection(*(set(r) for r in runs)))
    n = len(ids)

    agregado = {}
    for chave, rotulo, valor in _METRICAS:
        contagens = [sum(valor(run[i]) for i in ids) for run in runs]
        agregado[chave] = {
            "rotulo": rotulo,
            "por_execucao": contagens,
            "media": round(statistics.mean(contagens) / n, 4),
            "desvio": round(statistics.stdev(contagens) / n, 4),
        }

    mesmo_desfecho = sum(len({run[i]["outcome"] for run in runs}) == 1 for i in ids)
    mesmo_veredito = sum(
        len({run[i][w]["verdict"] for run in runs}) == 1 for i in ids for w in ("pos", "neg")
    )
    sempre_certo = sum(all(run[i]["outcome"] == "correct" for run in runs) for i in ids)
    nunca_certo = sum(all(run[i]["outcome"] != "correct" for run in runs) for i in ids)

    votos = {
        i: {w: _maioria([run[i][w]["verdict"] for run in runs]) for w in ("pos", "neg")} for i in ids
    }
    acertos_maioria = sum(v["pos"] == "pass" and v["neg"] == "fail" for v in votos.values())

    return {
        "execucoes": [d.name for d in run_dirs],
        "pares": n,
        "agregado": agregado,
        "pares_mesmo_desfecho": mesmo_desfecho,
        "respostas_mesmo_veredito": mesmo_veredito,
        "pares_sempre_certos": sempre_certo,
        "pares_sempre_errados": nunca_certo,
        "pares_instaveis": n - sempre_certo - nunca_certo,
        "maioria": {
            "acertos": acertos_maioria,
            "ci95": wilson_interval(acertos_maioria, n),
            "aprova_neg": sum(v["neg"] == "pass" for v in votos.values()),
            "bloqueia_pos": sum(v["pos"] == "fail" for v in votos.values()),
        },
    }


def render_markdown(r: dict) -> str:
    n = r["pares"]
    linhas = [
        "# Estabilidade entre execuções — CodeJudgeBench",
        "",
        *[f"- `{nome}`" for nome in r["execucoes"]],
        "",
        "| Métrica | Por execução | Média ± desvio |",
        "| --- | --- | --- |",
    ]
    for m in r["agregado"].values():
        por = " · ".join(f"{c / n * 100:.0f}%" for c in m["por_execucao"])
        linhas.append(f"| {m['rotulo']} | {por} | {m['media'] * 100:.1f}% ± {m['desvio'] * 100:.1f} p.p. |")
    total = len(r["execucoes"])
    ic = r["maioria"]["ci95"]
    linhas += [
        "",
        f"- Pares com o mesmo desfecho nas {total} execuções: {r['pares_mesmo_desfecho']}/{n}",
        f"- Respostas com o mesmo veredito nas {total} execuções: {r['respostas_mesmo_veredito']}/{2 * n}",
        f"- Pares acertados sempre: {r['pares_sempre_certos']} · errados sempre: {r['pares_sempre_errados']} "
        f"· instáveis: {r['pares_instaveis']}",
        f"- Voto da maioria: acurácia {r['maioria']['acertos']}/{n} "
        f"(IC 95% {ic[0] * 100:.1f}–{ic[1] * 100:.1f}%) · aprovou código que falha {r['maioria']['aprova_neg']} "
        f"· bloqueou código que passa {r['maioria']['bloqueia_pos']}",
    ]
    return "\n".join(linhas) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    saida = None
    if "--output" in args:
        i = args.index("--output")
        saida = Path(args[i + 1])
        del args[i : i + 2]
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    texto = render_markdown(stability([Path(a) for a in args]))
    if saida:
        saida.write_text(texto, encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
