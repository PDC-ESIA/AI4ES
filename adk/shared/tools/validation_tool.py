"""Ferramentas de apoio ao sub-agente de validação de requisitos."""

import os
from pathlib import Path


def _base_dir() -> Path:
    """Retorna o diretório base absoluto para resolução de caminhos das tools."""
    env = os.environ.get("ADK_AGENT_DATA_DIR")
    return (Path.cwd() / env).resolve() if env else Path.cwd()


def ler_artefatos_gerados(tipo: str = "") -> str:
    """
    Lê todos os artefatos de requisitos já gerados em docs/Time_1_Requisitos/.
    Retorna o conteúdo concatenado para análise de validação.

    Args:
        tipo: Filtro opcional por tipo (HU, RF, RNF, RN). Se vazio, lê todos.

    Returns:
        Texto concatenado de todos os artefatos encontrados, com separadores.
    """
    env = os.environ.get("ADK_DOCS_DIR")
    base = Path.cwd().resolve()
    docs_base = (base / env).resolve() if env else (base / "docs").resolve()
    raiz_docs = docs_base / "Time_1_Requisitos"

    mapa_pastas = {
        "HU": "HUs",
        "RF": "RFs",
        "RNF": "RNFs",
        "RN": "RNs",
    }

    if not raiz_docs.exists():
        return "Erro: diretório docs/Time_1_Requisitos/ não encontrado."

    tipo_normalizado = (tipo or "").strip().upper()

    if tipo_normalizado and tipo_normalizado in mapa_pastas:
        pastas = [raiz_docs / mapa_pastas[tipo_normalizado]]
    elif tipo_normalizado and tipo_normalizado not in mapa_pastas:
        return f"Erro: tipo '{tipo}' inválido. Use: HU, RF, RNF, RN ou deixe vazio para todos."
    else:
        pastas = [raiz_docs / nome for nome in mapa_pastas.values()]
        # Inclui também arquivos na raiz (ex: Glossario.md)
        pastas.append(raiz_docs)

    resultados = []
    arquivos_lidos = 0

    for pasta in pastas:
        if not pasta.exists():
            continue
        arquivos = sorted(
            f for f in pasta.iterdir()
            if f.is_file() and f.suffix.lower() == ".md"
        )
        for arq in arquivos:
            try:
                conteudo = arq.read_text(encoding="utf-8")
                resultados.append(
                    f"--- Arquivo: {arq} ---\n{conteudo}"
                )
                arquivos_lidos += 1
            except Exception as e:
                resultados.append(f"--- Erro ao ler {arq.name}: {e} ---")

    if not resultados:
        return "Nenhum artefato de requisito encontrado em docs/Time_1_Requisitos/."

    header = f"Total de artefatos lidos: {arquivos_lidos}\n\n"
    return header + "\n\n".join(resultados)
