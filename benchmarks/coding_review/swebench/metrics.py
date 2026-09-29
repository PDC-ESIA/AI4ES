"""As três métricas da issue #417, calculadas sobre os registros por instância.

Funções puras: recebem os registros montados pelo `run.py` (um dict por
instância, com o que aconteceu no loop e o resultado do harness oficial) e não
importam nada do `adk/`.

1. **Taxa de resolução** — resolvidas ÷ TODAS as instâncias do run. Patch vazio,
   erro de avaliação, falha na preparação e instância não avaliada contam como
   não resolvidas (e são discriminados à parte). Com intervalo de Wilson (95%),
   e também sem as instâncias que nem o patch oficial resolve (`--gold-sanity`).
2. **Rodadas e motivo de parada** — rodadas = turnos do executor contados pelo
   plugin de guarda. Motivo classificado a partir do `motivo_terminacao` da
   produção (`task_iterator.classificar_desfecho`), ver `classificar_parada`.
3. **Concordância do validador** — matriz de confusão entre o último veredito
   do validador e o `resolved` oficial, só sobre instâncias com gabarito
   conhecido. A issue pede os falsos positivos; a matriz sai de graça. Cada
   aprovação é qualificada (suíte vazia/pulada, patch vazio, testes não
   identificados), porque o validador aprova pelo status técnico da suíte que o
   PRÓPRIO coder declarou.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from typing import Any, Iterable

Z_95 = 1.959963984540054

# Status de correção (ver `grading.py`).
GRADE_RESOLVED = "resolved"
GRADE_UNRESOLVED = "unresolved"
GRADE_EMPTY_PATCH = "empty_patch"
GRADE_ERROR = "error"
GRADE_NOT_GRADED = "not_graded"
# O loop nunca rodou (ex.: pull da imagem falhou): nada a corrigir.
GRADE_PREP_FAILED = "falha_preparacao"
# Status em que o gabarito é conhecido (entram na matriz da métrica 3).
_GABARITO_CONHECIDO = frozenset({GRADE_RESOLVED, GRADE_UNRESOLVED, GRADE_EMPTY_PATCH})

# Categorias do motivo de parada (métrica 2).
PARADA_APROVACAO = "aprovacao_do_validador"
PARADA_POLITICA = "politica_de_progresso"
PARADA_MAX_ITER = "max_iterations"
PARADA_OUTRO = "outro"

# `motivo_terminacao` produzidos por `task_iterator.classificar_desfecho` e
# pelo próprio `loop_runner` (erro/timeout da instância).
MOTIVO_APROVADO = "aprovado"
PREFIXOS_POLITICA = ("bloqueado_", "aceito_com_ressalvas_")
MOTIVOS_ERRO = frozenset({"erro_operacional", "timeout_da_instancia"})

STATUS_ACEITO_COM_RESSALVAS = "aceito_com_ressalvas"
STATUS_TESTES_PULADO = "pulado"


def wilson_interval(sucessos: int, n: int, z: float = Z_95) -> tuple[float, float] | None:
    """Intervalo de confiança de Wilson para uma proporção; `None` se n == 0."""
    if n <= 0:
        return None
    p = sucessos / n
    z2 = z * z
    denominador = 1 + z2 / n
    centro = (p + z2 / (2 * n)) / denominador
    meia = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denominador
    return (max(0.0, centro - meia), min(1.0, centro + meia))


def rate(sucessos: int, n: int) -> dict[str, Any]:
    """Proporção com o intervalo de Wilson, pronta para o relatório."""
    intervalo = wilson_interval(sucessos, n)
    return {
        "k": sucessos,
        "n": n,
        "taxa": round(sucessos / n, 4) if n else None,
        "ic95": [round(intervalo[0], 4), round(intervalo[1], 4)] if intervalo else None,
    }


def iteration_stats(valores: list[int]) -> dict[str, Any]:
    """Média, mediana, extremos e distribuição das rodadas."""
    if not valores:
        return {"n": 0, "media": None, "mediana": None, "min": None, "max": None,
                "distribuicao": {}}
    return {
        "n": len(valores),
        "media": round(statistics.fmean(valores), 2),
        "mediana": statistics.median(valores),
        "min": min(valores),
        "max": max(valores),
        "distribuicao": {str(v): c for v, c in sorted(Counter(valores).items())},
    }


def classificar_parada(motivo: str | None, rodadas: int, teto: int | None) -> tuple[str, str]:
    """Categoria do motivo de parada e o detalhe (o `motivo_terminacao`).

    Ordem de precedência:
    1. `aprovado` → aprovação do validador;
    2. `bloqueado_*` / `aceito_com_ressalvas_*` → política de progresso (ela
       grava `loop_stop_reason`; o prefixo vem daí). Vale mesmo que a parada
       tenha coincidido com a rodada do teto — foi a política que parou;
    3. erro/timeout da instância → outro;
    4. sem nada acima e rodadas ≥ teto → `max_iterations` (a produção não dá
       rótulo próprio a esse caso; ele aparece como `reprovado_apos_loop` ou
       `validation_ausente_ou_invalida`);
    5. o resto → outro (ex.: o LLM do executor chamou `exit_loop` sem
       aprovação, ou o veredito ficou ausente).
    """
    motivo = motivo or "desconhecido"
    if motivo == MOTIVO_APROVADO:
        return PARADA_APROVACAO, motivo
    if motivo.startswith(PREFIXOS_POLITICA):
        return PARADA_POLITICA, motivo
    if motivo in MOTIVOS_ERRO:
        return PARADA_OUTRO, motivo
    if teto and rodadas >= teto:
        return PARADA_MAX_ITER, motivo
    return PARADA_OUTRO, motivo


def _status_grading(registro: dict[str, Any]) -> str:
    return (registro.get("grading") or {}).get("status") or GRADE_NOT_GRADED


def _resolvido(registro: dict[str, Any]) -> bool:
    return _status_grading(registro) == GRADE_RESOLVED


def _aprovado(registro: dict[str, Any]) -> bool:
    return registro.get("veredito_validador") == "aprovado"


def qualify_approval(registro: dict[str, Any]) -> dict[str, bool]:
    """Qualificadores de uma aprovação (o que a sustentava de fato)."""
    execucao = registro.get("execucao") or {}
    comandos = execucao.get("test_commands") or []
    identificados = execucao.get("testes_identificados")
    suite_vazia = not comandos or execucao.get("status_testes") == STATUS_TESTES_PULADO
    return {
        "suite_vazia_ou_pulada": suite_vazia,
        "patch_vazio": bool((registro.get("patch") or {}).get("vazio")),
        "testes_nao_identificados": bool(comandos) and not identificados,
    }


def confusion_matrix(pares: Iterable[tuple[bool, bool]]) -> dict[str, int]:
    """Matriz de confusão a partir de pares (aprovado, resolvido)."""
    matriz = {"vp": 0, "fp": 0, "fn": 0, "vn": 0}
    for aprovado, resolvido in pares:
        if aprovado and resolvido:
            matriz["vp"] += 1
        elif aprovado:
            matriz["fp"] += 1
        elif resolvido:
            matriz["fn"] += 1
        else:
            matriz["vn"] += 1
    return matriz


def _metrica_1(registros: list[dict[str, Any]], excluidas: frozenset[str]) -> dict[str, Any]:
    status = Counter(_status_grading(r) for r in registros)
    causas = Counter(
        (r.get("grading") or {}).get("causa")
        for r in registros
        if not _resolvido(r) and (r.get("grading") or {}).get("causa")
    )
    validas = [r for r in registros if r["instance_id"] not in excluidas]
    return {
        **rate(status.get(GRADE_RESOLVED, 0), len(registros)),
        "por_status": dict(sorted(status.items())),
        "causas_nao_resolvidas": dict(sorted(causas.items())),
        "excluidas_gold": sorted(excluidas),
        "sem_exclusoes_gold": rate(sum(1 for r in validas if _resolvido(r)), len(validas)),
    }


def _metrica_2(registros: list[dict[str, Any]], teto: int | None) -> dict[str, Any]:
    categorias: Counter[str] = Counter()
    detalhes: dict[str, Counter[str]] = defaultdict(Counter)
    divergencias = []
    for r in registros:
        rodadas = int(r.get("rodadas") or 0)
        categoria, detalhe = classificar_parada(r.get("motivo_terminacao"), rodadas, teto)
        categorias[categoria] += 1
        detalhes[categoria][detalhe] += 1
        if rodadas != len(r.get("historico_notas") or []):
            divergencias.append(r["instance_id"])
    return {
        "teto_max_iterations": teto,
        "rodadas": iteration_stats([int(r.get("rodadas") or 0) for r in registros]),
        "motivo_parada": dict(sorted(categorias.items())),
        "motivo_parada_detalhe": {
            cat: dict(sorted(cont.items())) for cat, cont in sorted(detalhes.items())
        },
        "divergencias_rodadas_vs_historico": divergencias,
    }


def _metrica_3(registros: list[dict[str, Any]], excluidas: frozenset[str]) -> dict[str, Any]:
    # Instâncias que nem o patch oficial resolve têm gabarito não confiável.
    com_gabarito = [
        r for r in registros
        if _status_grading(r) in _GABARITO_CONHECIDO and r["instance_id"] not in excluidas
    ]
    matriz = confusion_matrix((_aprovado(r), _resolvido(r)) for r in com_gabarito)
    aprovadas = [r for r in com_gabarito if _aprovado(r)]
    falsos_positivos = [r for r in aprovadas if not _resolvido(r)]

    qualificadores: Counter[str] = Counter()
    qualificadores_fp: Counter[str] = Counter()
    for r in aprovadas:
        for nome, ativo in qualify_approval(r).items():
            if ativo:
                qualificadores[nome] += 1
                if not _resolvido(r):
                    qualificadores_fp[nome] += 1

    ressalvas = [
        r for r in registros if r.get("status_desfecho") == STATUS_ACEITO_COM_RESSALVAS
    ]
    return {
        "matriz": matriz,
        "com_gabarito": len(com_gabarito),
        "sem_gabarito": len(registros) - len(com_gabarito),
        "excluidas_gold": sum(1 for r in registros if r["instance_id"] in excluidas),
        "aprovadas": len(aprovadas),
        "falsos_positivos": len(falsos_positivos),
        "falsos_positivos_ids": [r["instance_id"] for r in falsos_positivos],
        "taxa_fp_entre_aprovadas": rate(len(falsos_positivos), len(aprovadas)),
        "precisao": rate(matriz["vp"], matriz["vp"] + matriz["fp"]),
        "recall": rate(matriz["vp"], matriz["vp"] + matriz["fn"]),
        "aprovacoes_qualificadas": dict(sorted(qualificadores.items())),
        "falsos_positivos_qualificados": dict(sorted(qualificadores_fp.items())),
        "aceito_com_ressalvas": {
            "total": len(ressalvas),
            "resolvidas": sum(1 for r in ressalvas if _resolvido(r)),
        },
    }


def _por_repo(registros: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    tabela: dict[str, dict[str, int]] = defaultdict(
        lambda: {"n": 0, "resolvidas": 0, "aprovadas": 0}
    )
    for r in registros:
        linha = tabela[r.get("repo") or "desconhecido"]
        linha["n"] += 1
        linha["resolvidas"] += int(_resolvido(r))
        linha["aprovadas"] += int(_aprovado(r))
    return dict(sorted(tabela.items(), key=lambda kv: (-kv[1]["n"], kv[0])))


def _operacional(registros: list[dict[str, Any]]) -> dict[str, Any]:
    uso: Counter[str] = Counter()
    por_agente: dict[str, Counter[str]] = defaultdict(Counter)
    for r in registros:
        uso_instancia = r.get("uso") or {}
        uso.update({
            k: int(v)
            for k, v in uso_instancia.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        })
        for agente, linha in (uso_instancia.get("por_agente") or {}).items():
            por_agente[agente].update({k: int(v or 0) for k, v in linha.items()})
    return {
        "erros_operacionais": [r["instance_id"] for r in registros if r.get("erro") and not r.get("timeout")],
        "timeouts": [r["instance_id"] for r in registros if r.get("timeout")],
        "ambiente_violado": [
            r["instance_id"] for r in registros if (r.get("guarda") or {}).get("ambiente_violado")
        ],
        "venv_no_manifesto": [
            r["instance_id"] for r in registros if (r.get("guarda") or {}).get("venv_no_manifesto")
        ],
        "duracao_total_s": round(sum(float(r.get("duracao_s") or 0) for r in registros), 2),
        "uso_llm": {
            **dict(uso),
            "total_tokens": uso.get("prompt_tokens", 0) + uso.get("completion_tokens", 0),
            "por_agente": {a: dict(c) for a, c in sorted(por_agente.items())},
        },
    }


def aggregate(
    registros: list[dict[str, Any]],
    *,
    teto: int | None,
    excluidas: frozenset[str] | set[str] = frozenset(),
) -> dict[str, Any]:
    """Consolida as três métricas e os recortes auxiliares do relatório.

    Args:
        excluidas: instâncias que não resolvem nem com o patch oficial
            (`--gold-sanity`). A métrica 1 sai com e sem elas; a métrica 3 as
            deixa fora da matriz, porque o gabarito delas não é confiável.
    """
    excluidas = frozenset(excluidas)
    return {
        "n_instancias": len(registros),
        "metrica_1_resolucao": _metrica_1(registros, excluidas),
        "metrica_2_loop": _metrica_2(registros, teto),
        "metrica_3_validador": _metrica_3(registros, excluidas),
        "por_repositorio": _por_repo(registros),
        "operacional": _operacional(registros),
    }
