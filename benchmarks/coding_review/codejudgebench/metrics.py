"""Métricas do benchmark CodeJudgeBench sobre o reviewer.

Três famílias, que respondem a perguntas diferentes:

1. **Julgamento do par** (a pergunta do CodeJudgeBench): o reviewer distingue a
   correção que funciona da que não funciona?
   - ``accuracy``: pares ``correct`` / pares avaliáveis — empate conta como erro.
   - ``accuracy_ties_half``: empate vale meio acerto (equivale a sortear entre
     as duas respostas quando o reviewer não as distingue).
   - ``decisiveness``: fração de pares em que os vereditos diferem.
   - ``accuracy_when_decided``: acerto só entre os pares decididos.

2. **Qualidade da decisão por resposta** (a pergunta da issue #421: com que
   frequência o reviewer aprova código ruim ou reprova código bom?):
   - ``false_approve_rate``: ``neg`` (falha nos testes) aprovadas / ``neg`` julgadas.
   - ``false_block_rate``: ``pos`` (passa nos testes) bloqueadas / ``pos`` julgadas.

3. **Aderência de formato**:
   - ``invalid_first_attempt_rate``: respostas cuja 1ª tentativa não trouxe status
     reconhecível pelo manifesto, entre as que o reviewer chegou a responder.
   - ``invalid_final_rate``: o mesmo, após os retries.
   - ``format_only_failures``: tentativas em que o manifesto não achou status,
     mas a leitura tolerante achou — o reviewer decidiu, só escreveu fora do padrão.

Viés posicional: não se aplica ao modo pontual (cada chamada vê uma resposta só,
não há ordem A/B). Fica registrado como ``None`` com a justificativa.

Intervalos de confiança: Wilson a 95%, adequado a proporções com n pequeno.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from math import sqrt

from .grading import OUTCOMES_AVALIAVEIS, OUTCOMES_DECIDIDOS, OUTCOMES_EMPATE

_Z95 = 1.959963984540054

POSITIONAL_BIAS_NOTE = (
    "Não aplicável ao modo pontual: cada revisão vê uma única resposta, então "
    "não existe ordem A/B a inverter."
)


def wilson_interval(sucessos: int, n: int, z: float = _Z95) -> tuple[float, float] | None:
    """Intervalo de Wilson para uma proporção; None se n == 0."""
    if n <= 0:
        return None
    p = sucessos / n
    denominador = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / denominador
    margem = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominador
    return (round(max(0.0, centro - margem), 4), round(min(1.0, centro + margem), 4))


def _taxa(parte: int | float, total: int) -> float | None:
    return round(parte / total, 4) if total else None


def _proporcao(sucessos: int, n: int) -> dict:
    return {"value": _taxa(sucessos, n), "k": sucessos, "n": n, "ci95": wilson_interval(sucessos, n)}


def _respostas(registros: list[dict]) -> list[dict]:
    return [r[lado] for r in registros for lado in ("pos", "neg") if r.get(lado)]


def compute_metrics(registros: list[dict]) -> dict:
    """Calcula todas as métricas a partir dos registros de par do progress.jsonl."""
    desfechos = Counter(r["outcome"] for r in registros)
    avaliaveis = sum(desfechos[o] for o in OUTCOMES_AVALIAVEIS)
    decididos = sum(desfechos[o] for o in OUTCOMES_DECIDIDOS)
    empates = sum(desfechos[o] for o in OUTCOMES_EMPATE)
    corretos = desfechos["correct"]

    respostas = _respostas(registros)
    pos_julgadas = [r["pos"] for r in registros if r["pos"]["outcome_kind"] == "ok"]
    neg_julgadas = [r["neg"] for r in registros if r["neg"]["outcome_kind"] == "ok"]

    # Aderência: só conta quem o reviewer de fato respondeu (sem erro de API).
    primeiras = [r["attempts"][0] for r in respostas if r.get("attempts")]
    respondidas_1a = [a for a in primeiras if not a.get("error")]
    invalidas_1a = sum(1 for a in respondidas_1a if a["verdict"] == "absent")
    finais = [r for r in respostas if r["outcome_kind"] in ("ok", "invalid")]
    invalidas_final = sum(1 for r in finais if r["outcome_kind"] == "invalid")
    tentativas = [a for r in respostas for a in r.get("attempts", [])]
    so_formato = sum(
        1
        for a in tentativas
        if a["verdict"] == "absent" and not a.get("error") and a.get("lenient_status") in ("APROVADO", "BLOQUEADO")
    )

    # Por dificuldade (só pares avaliáveis).
    por_dificuldade: dict[str, dict] = {}
    agrupado: dict[str, list[str]] = defaultdict(list)
    for r in registros:
        if r["outcome"] in OUTCOMES_AVALIAVEIS:
            agrupado[r.get("difficulty") or "?"].append(r["outcome"])
    for dificuldade in sorted(agrupado):
        lista = agrupado[dificuldade]
        por_dificuldade[dificuldade] = _proporcao(lista.count("correct"), len(lista))

    # Hipótese do ruído SDLC: em que camadas caem as issues críticas das
    # respostas CORRETAS que o reviewer bloqueou?
    camadas_bloqueio_indevido: Counter = Counter()
    for pos in pos_julgadas:
        if pos["verdict"] == "fail":
            for issue in pos.get("issues") or []:
                if issue.get("severity") == "critical":
                    camadas_bloqueio_indevido[issue.get("layer") or "unknown"] += 1

    return {
        "pairs": {
            "total": len(registros),
            "evaluable": avaliaveis,
            "outcomes": dict(sorted(desfechos.items())),
        },
        "judgment": {
            "accuracy": _proporcao(corretos, avaliaveis),
            "accuracy_ties_half": _taxa(corretos + 0.5 * empates, avaliaveis),
            "decisiveness": _proporcao(decididos, avaliaveis),
            "accuracy_when_decided": _proporcao(corretos, decididos),
            "positional_bias": None,
            "positional_bias_note": POSITIONAL_BIAS_NOTE,
        },
        "decision": {
            "false_approve_rate": _proporcao(sum(1 for r in neg_julgadas if r["verdict"] == "pass"), len(neg_julgadas)),
            "false_block_rate": _proporcao(sum(1 for r in pos_julgadas if r["verdict"] == "fail"), len(pos_julgadas)),
            "critical_issue_layers_on_false_blocks": dict(camadas_bloqueio_indevido.most_common()),
        },
        "format": {
            "invalid_first_attempt_rate": _proporcao(invalidas_1a, len(respondidas_1a)),
            "invalid_final_rate": _proporcao(invalidas_final, len(finais)),
            "responses_with_retry": sum(1 for r in respostas if len(r.get("attempts", [])) > 1),
            "format_only_failures": so_formato,
            "gate_applied": sum(1 for a in tentativas if a.get("gate_applied")),
        },
        "operational": {
            "responses_with_operational_error": sum(1 for r in respostas if r["outcome_kind"] == "operational"),
            "responses_without_code": sum(1 for r in respostas if r["outcome_kind"] == "no_code"),
        },
        "by_difficulty": por_dificuldade,
        "usage": {
            "reviews": len(tentativas),
            "llm_interactions": sum(a.get("llm_interactions", 0) for a in tentativas),
            "prompt_tokens": sum(a.get("prompt_tokens", 0) for a in tentativas),
            "completion_tokens": sum(a.get("completion_tokens", 0) for a in tentativas),
            "review_duration_s": round(sum(a.get("duration_s", 0.0) for a in tentativas), 2),
        },
    }
