"""Consolidação e tratamento estatístico do benchmark (protocolo §11, §12 e §13).

Lê benchmark/judgments/*.json, consolida as notas dos juízes e aplica os testes
exigidos pelo protocolo: descritivas com IC 95%, Friedman com post-hoc de
Nemenyi, Wilcoxon pareado, Cliff's Delta e Kendall's W.

Uso:
    adk/.venv/bin/python benchmark/analyze.py
"""

import itertools
import json
import sys

import numpy as np

from config import ALFA, CANDIDATOS, CRITERIOS, JUDGMENTS, RESULTS, ROTULOS

try:
    import pandas as pd
    from scipy import stats
except ImportError:
    sys.exit(
        "faltam dependências estatísticas. Instale com:\n"
        "  cd adk && uv pip install pandas scipy scikit-posthocs"
    )


def carregar() -> pd.DataFrame:
    registros = []
    for arq in sorted(JUDGMENTS.glob("*.json")):
        d = json.loads(arq.read_text(encoding="utf-8"))
        linha = {
            "candidato": d["candidato"],
            "caso": d["caso"],
            "execucao": d["execucao"],
            "juiz": d["juiz"],
            "nota_final": d["nota_final"],
            "latencia_juiz_s": d.get("latencia_s"),
            "tokens_total": d.get("tokens_total"),
        }
        linha.update(d["notas"])
        registros.append(linha)
    if not registros:
        sys.exit("nenhum julgamento encontrado em benchmark/judgments/")
    return pd.DataFrame(registros)


def descritivas(serie: pd.Series) -> dict:
    n = len(serie)
    media = serie.mean()
    desvio = serie.std(ddof=1) if n > 1 else 0.0
    if n > 1:
        margem = stats.t.ppf(0.975, n - 1) * desvio / np.sqrt(n)
    else:
        margem = np.nan
    return {
        "n": n,
        "media": media,
        "mediana": serie.median(),
        "desvio_padrao": desvio,
        "minimo": serie.min(),
        "maximo": serie.max(),
        "ic95_inf": media - margem,
        "ic95_sup": media + margem,
        "coef_variacao": desvio / media if media else np.nan,
    }


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> tuple[float, str]:
    maior = sum((a > b) for a in x for b in y)
    menor = sum((a < b) for a in x for b in y)
    delta = (maior - menor) / (len(x) * len(y))
    mag = abs(delta)
    if mag < 0.147:
        rotulo = "desprezível"
    elif mag < 0.33:
        rotulo = "pequeno"
    elif mag < 0.474:
        rotulo = "médio"
    else:
        rotulo = "grande"
    return delta, rotulo


def matriz_pareada(consolidado: pd.DataFrame) -> pd.DataFrame:
    """Blocos (caso, execução) × candidatos, mantendo apenas blocos completos."""
    largo = consolidado.pivot_table(
        index=["caso", "execucao"], columns="candidato", values="nota_final"
    )
    presentes = [c for c in CANDIDATOS if c in largo.columns]
    return largo[presentes].dropna()


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    df = carregar()

    # Protocolo §11: quando há múltiplos juízes, a nota da execução é a média deles.
    consolidado = (
        df.groupby(["candidato", "caso", "execucao"], as_index=False)
        .agg({**{c: "mean" for c in CRITERIOS}, "nota_final": "mean"})
    )
    consolidado.to_csv(RESULTS / "consolidado.csv", index=False)

    print("=" * 72)
    print("DESCRITIVAS POR MODELO (nota final)")
    print("=" * 72)
    linhas = []
    for modelo, grupo in consolidado.groupby("candidato"):
        n_juizes = df.loc[df["candidato"] == modelo, "juiz"].nunique()
        linhas.append(
            {"candidato": modelo, "n_juizes": n_juizes, **descritivas(grupo["nota_final"])}
        )
    tabela = pd.DataFrame(linhas).sort_values("media", ascending=False)
    tabela.to_csv(RESULTS / "descritivas.csv", index=False)
    print(tabela.to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    if tabela["n_juizes"].nunique() > 1:
        print(
            "\naviso: candidatos avaliados por quantidades diferentes de juízes "
            "(autoavaliação descartada). As médias não têm precisão comparável."
        )

    print()
    print("=" * 72)
    print("NOTA MÉDIA POR CRITÉRIO")
    print("=" * 72)
    por_criterio = consolidado.groupby("candidato")[CRITERIOS].mean().T
    por_criterio.index = [ROTULOS[c] for c in por_criterio.index]
    por_criterio.to_csv(RESULTS / "por_criterio.csv")
    print(por_criterio.to_string(float_format=lambda v: f"{v:.3f}"))

    largo = matriz_pareada(consolidado)
    k, n = largo.shape[1], largo.shape[0]
    print()
    print("=" * 72)
    print(f"TESTES PAREADOS  ({n} bloco(s) completo(s), {k} modelo(s))")
    print("=" * 72)

    if n < 2 or k < 2:
        print("blocos insuficientes para inferência — colete mais execuções")
        return

    if k >= 3:
        # Protocolo §13: três ou mais modelos → Friedman.
        chi2, p = stats.friedmanchisquare(*[largo[c].to_numpy() for c in largo.columns])
        w = chi2 / (n * (k - 1))  # Kendall's W derivado da estatística de Friedman
        print(f"Friedman: chi2={chi2:.4f}  p={p:.5f}  (alfa={ALFA})")
        print(f"Kendall's W (concordância global): {w:.4f}")
        if p < ALFA:
            print("-> diferença significativa; aplicando post-hoc de Nemenyi")
            try:
                import scikit_posthocs as sp

                nemenyi = sp.posthoc_nemenyi_friedman(largo.to_numpy())
                nemenyi.index = nemenyi.columns = largo.columns
                nemenyi.to_csv(RESULTS / "nemenyi.csv")
                print(nemenyi.to_string(float_format=lambda v: f"{v:.5f}"))
            except ImportError:
                print("   scikit-posthocs ausente: uv pip install scikit-posthocs")
        else:
            print("-> sem diferença estatisticamente significativa entre os modelos")
    else:
        # Protocolo §13: exatamente dois modelos → Wilcoxon.
        a, b = largo.columns
        _, p = stats.wilcoxon(largo[a], largo[b])
        print(f"Wilcoxon {a} vs {b}: p={p:.5f}")

    print()
    print("Comparações par a par (Wilcoxon + Cliff's Delta):")
    pares = []
    for a, b in itertools.combinations(largo.columns, 2):
        x, y = largo[a].to_numpy(), largo[b].to_numpy()
        p = stats.wilcoxon(x, y).pvalue if not np.allclose(x, y) else 1.0
        delta, magnitude = cliffs_delta(x, y)
        pares.append(
            {
                "modelo_a": a,
                "modelo_b": b,
                "wilcoxon_p": p,
                "significativo": p < ALFA,
                "cliffs_delta": delta,
                "magnitude": magnitude,
            }
        )
    tabela_pares = pd.DataFrame(pares)
    tabela_pares.to_csv(RESULTS / "pareado.csv", index=False)
    print(tabela_pares.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

    print()
    print(f"CSVs gravados em {RESULTS}")


if __name__ == "__main__":
    main()
