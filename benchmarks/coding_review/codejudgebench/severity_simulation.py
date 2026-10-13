"""Simula regras de severidade sobre revisões já salvas — sem LLM (fase B, #421).

Uso (a partir da raiz do repositório):

    python -m benchmarks.coding_review.codejudgebench.severity_simulation <run_dir> [...]

Pergunta: e se as issues críticas de DESEMPENHO (TLE, complexidade) fossem
rebaixadas para `warning`? Em vez de mudar o prompt e pagar um run, a simulação
reaproveita as issues que o reviewer já escreveu em `reviews/` e recalcula o
veredito: BLOQUEADO se sobrar alguma issue crítica depois da regra.

Regras:
- V0: nenhuma mudança — mede a fidelidade do simulador ao veredito real;
- V1: toda crítica só de desempenho vira `warning`;
- V2: idem, exceto quando a falha original do código com bug foi Time Limit
  Exceeded (aí a correção é justamente sobre desempenho).

É uma aproximação: um reviewer instruído de outro jeito também escreveria
issues diferentes. Serve para dizer se a mudança vale um run, não para
substituí-lo.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from benchmarks.coding_review.codejudgebench import dataset as ds
from benchmarks.coding_review.codejudgebench.contract import parse_review_markdown
from benchmarks.coding_review.codejudgebench.regrade import _slug

REGRAS = ("V0", "V1", "V2")

_DESEMPENHO = re.compile(
    r"tle|time limit|complexidade|o\(n|o\(m|o\(\w*\^|quadr[aá]tic|desempenho|performance|lento|"
    r"escala|inaceit[aá]vel para|10\^|10\*\*",
    re.IGNORECASE,
)
_LOGICA = re.compile(
    r"incorret|errad|off-by-one|wrong|borda|edge case|n[aã]o trata|exce[cç][aã]o|indexerror|keyerror",
    re.IGNORECASE,
)
_TLE = re.compile(r"time limit|timeout|tle", re.IGNORECASE)


def so_desempenho(issue: dict) -> bool:
    """Issue que fala de desempenho e não aponta erro de lógica."""
    texto = issue.get("description") or ""
    return bool(_DESEMPENHO.search(texto)) and not _LOGICA.search(texto)


def falha_original_foi_tle(par: ds.RepairPair) -> bool:
    meta = par.wrong_meta or {}
    return bool(_TLE.search(f"{meta.get('error_message') or ''} {meta.get('error') or ''}"))


def veredito_simulado(markdown: str, par: ds.RepairPair, regra: str) -> str:
    criticas = [i for i in parse_review_markdown(markdown).issues if i["severity"] == "critical"]

    def rebaixada(issue: dict) -> bool:
        if regra == "V0" or not so_desempenho(issue):
            return False
        return regra == "V1" or not falha_original_foi_tle(par)

    return "fail" if any(not rebaixada(i) for i in criticas) else "pass"


def simular(run_dir: Path, pares: dict[str, ds.RepairPair]) -> dict[str, dict]:
    relatorio = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    resultado: dict[str, dict] = {}
    for regra in REGRAS:
        acertos = aprova_neg = bloqueia_pos = concorda = total = 0
        for registro in relatorio["pairs"]:
            par = pares[registro["pair_id"]]
            vereditos = {}
            for which in ("pos", "neg"):
                md = run_dir / "reviews" / f"{_slug(registro['pair_id'])}_{which}.md"
                vereditos[which] = veredito_simulado(md.read_text(encoding="utf-8"), par, regra)
                concorda += vereditos[which] == registro[which]["verdict"]
                total += 1
            acertos += vereditos["pos"] == "pass" and vereditos["neg"] == "fail"
            aprova_neg += vereditos["neg"] == "pass"
            bloqueia_pos += vereditos["pos"] == "fail"
        resultado[regra] = {
            "pares": len(relatorio["pairs"]),
            "acertos": acertos,
            "aprova_neg": aprova_neg,
            "bloqueia_pos": bloqueia_pos,
            "concorda_com_real": f"{concorda}/{total}",
        }
    return resultado


def main(argv: list[str] | None = None) -> int:
    dirs = [Path(a) for a in (argv if argv is not None else sys.argv[1:])]
    if not dirs:
        print(__doc__)
        return 2
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    cache = Path(__file__).resolve().parent / "datasets"
    pares = {p.pair_id: p for p in ds.load_all(cache, ds.DEFAULT_SPLIT)}
    for run_dir in dirs:
        print(f"\n## {run_dir.name}\n")
        print("| Regra | Acurácia | Aprovou neg | Bloqueou pos | Vereditos iguais ao real |")
        print("| --- | --- | --- | --- | --- |")
        for regra, r in simular(run_dir, pares).items():
            print(
                f"| {regra} | {r['acertos']}/{r['pares']} | {r['aprova_neg']}/{r['pares']} "
                f"| {r['bloqueia_pos']}/{r['pares']} | {r['concorda_com_real']} |"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
