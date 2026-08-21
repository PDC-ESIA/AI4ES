"""Métricas do piloto da Fase 3 (Protocolo §9.4 e §10).

Métricas implementadas:
  - EM (Exact Match) e F1 token-level, normalização estilo SQuAD official.
  - Unanswerable Rate (recusa correta em perguntas sem resposta).
  - False Positive Answering (inventou resposta quando deveria recusar).
  - Quasi Exact Match (GAIA): normalização por tipo (string/número/lista).
  - pass^k (consistência): fração de casos com k/k repetições corretas.

Nota sobre Supporting Fact P/R (HotpotQA): o prompt padronizado do piloto pede
apenas a resposta curta, não evidências — portanto SF P/R é N/A nesta rodada
(decisão documentada no relatório; versão com prompt de evidências fica para a
Fase 4, conforme ajuste ao protocolo).

Todos os comparadores são case-insensitive e ignoram pontuação/artigos.
"""

import math
import re
import string
from collections import defaultdict

# Tokens canônicos de recusa (normalizados). O prompt do SQuAD usa "unanswerable";
# o do LongBench/qasper usa "not specified". Sinônimos comuns aceitos na avaliação.
REJECTION_TOKENS = {
    "unanswerable",
    "not answerable",
    "no answer",
    "cannot be answered",
    "cannot answer",
    "not specified",
    "not mentioned",
    "not in the passage",
    "insufficient information",
    "unknown",
}

_ARTICLES = {"a", "an", "the"}
_PUNCT_TABLE = str.maketrans("", "", string.punctuation)


def normalize_text(s: str) -> str:
    s = s.lower().translate(_PUNCT_TABLE)
    return " ".join(w for w in s.split() if w not in _ARTICLES)


def extract_answer(raw: str | None) -> str:
    """Primeira linha não vazia da resposta (o pedido foi 'respond ONLY ...')."""
    if not raw:
        return ""
    for line in raw.strip().splitlines():
        line = line.strip()
        if line:
            # remove prefixos conversacionais curtos que vazam apesar da instrução
            line = re.sub(r"^(answer|final answer)\s*[:\-]\s*", "", line, flags=re.I)
            return line.rstrip(" .")
    return ""


def is_rejection(pred_norm: str) -> bool:
    if not pred_norm:
        return True  # resposta vazia conta como não-resposta (registrada à parte)
    return pred_norm in REJECTION_TOKENS


def exact_match(pred: str, golds: list[str]) -> bool:
    p = normalize_text(pred)
    return any(p == normalize_text(g) for g in golds if g)


def f1_score(pred: str, golds: list[str]) -> float:
    def _f1(p_tokens: list[str], g_tokens: list[str]) -> float:
        common = set(p_tokens) & set(g_tokens)
        if not common:
            return 0.0
        precision = len(common) / len(p_tokens)
        recall = len(common) / len(g_tokens)
        return 2 * precision * recall / (precision + recall)

    p = normalize_text(pred).split()
    best = 0.0
    for g in golds:
        if not g:
            continue
        gt = normalize_text(g).split()
        if not p and not gt:
            best = max(best, 1.0)
            continue
        best = max(best, _f1(p, gt))
    return best


def quasi_exact_match_gaia(pred: str, golds: list[str]) -> bool:
    """Normalização por tipo: número compara numericamente; string sem espaços/pontuação."""

    def canon(x: str):
        x = x.strip()
        try:
            num = float(x.replace(",", "").replace("%", "").rstrip("."))
            return ("num", round(num, 6))
        except ValueError:
            pass
        return ("str", re.sub(r"[\s\W_]+", "", x.lower()))

    p = canon(pred)
    for g in golds:
        try:
            if p == canon(g):
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def case_metrics(benchmark: str, pred_raw: str | None, case: dict) -> dict:
    """Avalia uma única resposta contra o caso. Retorna métricas binárias/contínuas."""
    pred = extract_answer(pred_raw)
    pred_norm = normalize_text(pred)
    golds = [g for g in case.get("gold_answers", []) if g]

    m = {
        "em": 0.0,
        "f1": 0.0,
        "answered": 0.0 if is_rejection(pred_norm) else 1.0,
        "correct": 0.0,
        "rejection_correct": None,
        "false_positive_answering": None,
    }
    if benchmark == "gaia_l1":
        m["em"] = 1.0 if quasi_exact_match_gaia(pred, golds) else 0.0
        m["f1"] = m["em"]
        m["correct"] = m["em"]
        return m

    if benchmark == "squad_v2" and not case["answerable"]:
        recusou = is_rejection(pred_norm)
        m["rejection_correct"] = 1.0 if recusou else 0.0
        m["false_positive_answering"] = 0.0 if recusou else 1.0
        return m

    m["em"] = float(exact_match(pred, golds))
    m["f1"] = f1_score(pred, golds)
    m["correct"] = m["em"]
    return m


def aggregate_benchmark(benchmark: str, cases_results: dict[str, list[dict]]) -> dict:
    """Agrega resultados por caso: média entre repetições + pass^k por caso.

    cases_results: {case_id: [métricas rep1, rep2, ..., repK]}
    """
    per_case_mean = defaultdict(float)
    counters = defaultdict(float)
    n_cases = len(cases_results)
    k_values = sorted({len(reps) for reps in cases_results.values()})

    pass_k_acc = 0.0
    for cid, reps in cases_results.items():
        k = len(reps)
        for key in ("em", "f1", "correct"):
            per_case_mean[key] += sum(r[key] for r in reps) / k
        if all(r["correct"] == 1.0 for r in reps):
            pass_k_acc += 1.0
        rej = [r["rejection_correct"] for r in reps if r["rejection_correct"] is not None]
        fpa = [r["false_positive_answering"] for r in reps if r["false_positive_answering"] is not None]
        if rej:
            counters["rejection_correct_total"] += sum(rej) / len(rej)
            counters["rejection_cases"] += 1
        if fpa:
            counters["fpa_total"] += sum(fpa) / len(fpa)
            counters["fpa_cases"] += 1

    out = {
        "n_cases": n_cases,
        "k_reps": k_values[-1] if k_values else 0,
        "EM_mean": per_case_mean["em"] / n_cases if n_cases else 0.0,
        "F1_mean": per_case_mean["f1"] / n_cases if n_cases else 0.0,
        "pass_k_consistency": pass_k_acc / n_cases if n_cases else 0.0,
    }
    if counters["rejection_cases"]:
        out["unanswerable_rate"] = counters["rejection_correct_total"] / counters["rejection_cases"]
        out["n_unanswerable_cases"] = int(counters["rejection_cases"])
    if counters["fpa_cases"]:
        out["false_positive_answering"] = counters["fpa_total"] / counters["fpa_cases"]
    out["answered_rate"] = None  # preenchido pelo agregador se aplicável
    return out


def latency_percentiles(values: list[float]) -> dict:
    if not values:
        return {}
    vs = sorted(values)

    def pct(p: float) -> float:
        idx = min(len(vs) - 1, math.ceil(p / 100 * len(vs)) - 1)
        return round(vs[idx], 3)

    return {"p50_s": pct(50), "p95_s": pct(95), "mean_s": round(sum(vs) / len(vs), 3)}
