"""Compara dois runs do CodeJudgeBench par a par — o veredito de cada mudança.

Uso (a partir da raiz do repositório):

    python -m benchmarks.coding_review.codejudgebench.compare <run_A> <run_B> [--output comparacao.md]

`A` é a referência (ex.: o baseline) e `B` o candidato (ex.: o reviewer com a
mudança da fase). Os dois runs precisam ter avaliado os mesmos pares; a
comparação usa só os pares em comum e avisa quando os conjuntos diferem.

Para cada métrica, cada par vira um valor binário em A e em B (acertou o par?
aprovou a neg? bloqueou a pos?). O teste de McNemar exato usa só os pares em que
A e B discordam: se a mudança não tivesse efeito, as discordâncias se dividiriam
meio a meio entre os dois sentidos. Comparar as taxas de cada run em separado
ignoraria esse pareamento e desperdiçaria a maior parte da informação.
"""

from __future__ import annotations

import argparse
import json
import sys
from math import comb
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from benchmarks.coding_review.codejudgebench.grading import OUTCOMES_AVALIAVEIS


def mcnemar_exact(so_a: int, so_b: int) -> float:
    """p-valor bilateral do McNemar exato (binomial com p=0,5 nas discordâncias)."""
    n = so_a + so_b
    if n == 0:
        return 1.0
    k = min(so_a, so_b)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n)


def _carregar(run_dir: Path) -> dict:
    relatorio = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    meta = relatorio.get("metadata") or {}
    codigo = meta.get("code") or {}
    return {
        "nome": run_dir.name,
        "modelo": (meta.get("config") or {}).get("model"),
        "label": meta.get("label"),
        "commit": (codigo.get("commit") or "")[:8] or None,
        "dirty": codigo.get("dirty"),
        "pares": {p["pair_id"]: p for p in relatorio["pairs"]},
    }


# Cada métrica: (chave, rótulo, quem entra na comparação, o valor binário do par).
# "maior é melhor" orienta a leitura do delta na tabela.
_METRICAS = (
    (
        "accuracy",
        "Acurácia do julgamento",
        lambda p: p["outcome"] in OUTCOMES_AVALIAVEIS,
        lambda p: p["outcome"] == "correct",
        True,
    ),
    (
        "false_approve",
        "Aprovou código que falha nos testes",
        lambda p: p["neg"]["outcome_kind"] == "ok",
        lambda p: p["neg"]["verdict"] == "pass",
        False,
    ),
    (
        "false_block",
        "Bloqueou código que passa nos testes",
        lambda p: p["pos"]["outcome_kind"] == "ok",
        lambda p: p["pos"]["verdict"] == "fail",
        False,
    ),
)


def compare(run_a: Path, run_b: Path) -> dict:
    """Comparação pareada de B contra A nas métricas principais."""
    a, b = _carregar(run_a), _carregar(run_b)
    comuns = sorted(set(a["pares"]) & set(b["pares"]))
    resultado: dict = {
        "a": {k: v for k, v in a.items() if k != "pares"},
        "b": {k: v for k, v in b.items() if k != "pares"},
        "pares_comuns": len(comuns),
        "so_em_a": sorted(set(a["pares"]) - set(b["pares"])),
        "so_em_b": sorted(set(b["pares"]) - set(a["pares"])),
        "metricas": {},
    }
    for chave, rotulo, entra, valor, maior_melhor in _METRICAS:
        ids = [i for i in comuns if entra(a["pares"][i]) and entra(b["pares"][i])]
        va = {i: valor(a["pares"][i]) for i in ids}
        vb = {i: valor(b["pares"][i]) for i in ids}
        so_a = sum(1 for i in ids if va[i] and not vb[i])
        so_b = sum(1 for i in ids if vb[i] and not va[i])
        n = len(ids)
        resultado["metricas"][chave] = {
            "rotulo": rotulo,
            "n": n,
            "a": sum(va.values()),
            "b": sum(vb.values()),
            "taxa_a": round(sum(va.values()) / n, 4) if n else None,
            "taxa_b": round(sum(vb.values()) / n, 4) if n else None,
            "so_a": so_a,
            "so_b": so_b,
            "p": round(mcnemar_exact(so_a, so_b), 6),
            "maior_melhor": maior_melhor,
        }
    resultado["mudancas"] = [
        {
            "pair_id": i,
            "difficulty": b["pares"][i].get("difficulty"),
            "a": a["pares"][i]["outcome"],
            "b": b["pares"][i]["outcome"],
        }
        for i in comuns
        if a["pares"][i]["outcome"] != b["pares"][i]["outcome"]
    ]
    return resultado


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.1f}%"


def _p(p: float) -> str:
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def _leitura(m: dict) -> str:
    if m["taxa_a"] is None or m["so_a"] + m["so_b"] == 0:
        return "sem diferença"
    melhorou = (m["taxa_b"] > m["taxa_a"]) == m["maior_melhor"]
    if m["taxa_b"] == m["taxa_a"]:
        return "sem diferença"
    sentido = "melhorou" if melhorou else "piorou"
    return f"{sentido} (significativo)" if m["p"] < 0.05 else f"{sentido} (não significativo)"


def _descricao_run(r: dict) -> str:
    versao = (r["commit"] or "?") + (" + alterações não commitadas" if r["dirty"] else "")
    return f"`{r['nome']}` · modelo `{r['modelo']}` · rótulo `{r['label'] or '—'}` · código `{versao}`"


def render_markdown(resultado: dict) -> str:
    linhas = [
        "# Comparação pareada — CodeJudgeBench",
        "",
        f"- **A (referência):** {_descricao_run(resultado['a'])}",
        f"- **B (candidato):** {_descricao_run(resultado['b'])}",
        f"- **Pares em comum:** {resultado['pares_comuns']}",
    ]
    if resultado["so_em_a"] or resultado["so_em_b"]:
        linhas.append(
            f"- **Atenção:** os runs não avaliaram os mesmos pares ({len(resultado['so_em_a'])} só em A, "
            f"{len(resultado['so_em_b'])} só em B); a comparação usa só os comuns."
        )
    linhas += [
        "",
        "| Métrica | A | B | Δ | Só A · só B | McNemar p | Leitura |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m in resultado["metricas"].values():
        delta = (
            "—"
            if m["taxa_a"] is None
            else f"{(m['taxa_b'] - m['taxa_a']) * 100:+.1f} p.p."
        )
        linhas.append(
            f"| {m['rotulo']} | {_pct(m['taxa_a'])} ({m['a']}/{m['n']}) | {_pct(m['taxa_b'])} ({m['b']}/{m['n']}) "
            f"| {delta} | {m['so_a']} · {m['so_b']} | {_p(m['p'])} | {_leitura(m)} |"
        )
    linhas += [
        "",
        "> \"Só A · só B\": pares em que só um dos runs marcou a métrica — o acerto na primeira linha,",
        "> o erro nas outras duas. O McNemar usa apenas esses pares discordantes.",
        "",
        f"## Pares que mudaram de desfecho ({len(resultado['mudancas'])})",
        "",
    ]
    if resultado["mudancas"]:
        linhas += ["| Par | Dificuldade | A | B |", "| --- | --- | --- | --- |"]
        linhas += [
            f"| {c['pair_id']} | {c['difficulty']} | `{c['a']}` | `{c['b']}` |" for c in resultado["mudancas"]
        ]
    else:
        linhas.append("Nenhum.")
    return "\n".join(linhas) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="benchmarks.coding_review.codejudgebench.compare",
        description="Compara dois runs do CodeJudgeBench par a par (McNemar exato).",
    )
    parser.add_argument("run_a", type=Path, help="Run de referência (ex.: baseline).")
    parser.add_argument("run_b", type=Path, help="Run candidato (ex.: reviewer com a mudança).")
    parser.add_argument("--output", type=Path, default=None, help="Grava o markdown neste arquivo.")
    args = parser.parse_args(argv)

    for fluxo in (sys.stdout,):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    texto = render_markdown(compare(args.run_a, args.run_b))
    if args.output:
        args.output.write_text(texto, encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
