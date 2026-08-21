"""Cálculo da métrica pass@k do HumanEval.

Usa o estimador não-enviesado do artigo original (Chen et al., 2021):

    pass@k = 1 - C(n - c, k) / C(n, k)

onde ``n`` é o número de amostras geradas por problema, ``c`` é o número de
amostras corretas e ``k`` é o parâmetro da métrica. O resultado final é a média
do estimador sobre todos os problemas.
"""

from __future__ import annotations

from math import comb


def pass_at_k(n: int, c: int, k: int) -> float:
    """Estimador não-enviesado de pass@k para UM problema.

    Args:
        n: total de amostras geradas para o problema.
        c: número de amostras corretas.
        k: parâmetro da métrica.

    Returns:
        Probabilidade estimada de, ao sortear k das n amostras, ao menos uma
        estar correta. Retorna 1.0 se `k >= n` e houver ao menos um acerto.
    """
    if k <= 0:
        raise ValueError("k deve ser >= 1.")
    if n <= 0:
        return 0.0
    if c <= 0:
        return 0.0
    if n - c < k:
        # Impossível sortear k amostras sem pegar nenhuma correta.
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def aggregate_pass_at_k(
    per_problem: list[tuple[int, int]], ks: list[int]
) -> dict[int, float]:
    """Agrega pass@k sobre todos os problemas (média do estimador).

    Args:
        per_problem: lista de tuplas ``(n, c)`` por problema — total de amostras
            e número de amostras corretas.
        ks: valores de k a computar.

    Returns:
        Mapa ``{k: pass@k médio}``. Um k é omitido se algum problema tiver n < k
        (a métrica não é definível para todos os problemas nesse caso).
    """
    if not per_problem:
        return {k: 0.0 for k in ks}

    resultado: dict[int, float] = {}
    for k in ks:
        if any(n < k for n, _ in per_problem):
            # k maior que o nº de amostras de algum problema: métrica indefinida.
            continue
        media = sum(pass_at_k(n, c, k) for n, c in per_problem) / len(per_problem)
        resultado[k] = media
    return resultado
