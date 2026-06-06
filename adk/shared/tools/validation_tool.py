"""Ferramentas de apoio ao sub-agente de validação de requisitos."""

import os
from pathlib import Path


def _base_dir() -> Path:
    """Retorna o diretório base absoluto para resolução de caminhos das tools."""
    env = os.environ.get("ADK_AGENT_DATA_DIR")
    return (Path.cwd() / env).resolve() if env else Path.cwd()


def ler_artefatos_gerados(tipo: str = "", ids: str = "") -> str:
    """
    Lê artefatos de requisitos já gerados em docs/Time_1_Requisitos/.
    Retorna o conteúdo concatenado para análise de validação.

    Args:
        tipo: Filtro opcional por tipo (HU, RF, RNF, RN). Se vazio, lê todos.
        ids: Lista de IDs específicos separados por vírgula (ex: "HU-001,RF-002,RNF-003").
             Se fornecido, lê APENAS esses arquivos. Ignora o parâmetro 'tipo'.

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

    # Modo 1: Lista de IDs específicos (prioridade)
    ids_limpos = [id_req.strip() for id_req in ids.split(",") if id_req.strip()]
    
    if ids_limpos:
        resultados = []
        arquivos_lidos = 0
        nao_encontrados = []
        
        for id_req in ids_limpos:
            # Infere o tipo pelo prefixo (ex: HU-001 → HU)
            tipo_inferido = id_req.split("-")[0].upper()
            
            if tipo_inferido not in mapa_pastas:
                nao_encontrados.append(id_req)
                continue
            
            pasta = raiz_docs / mapa_pastas[tipo_inferido]
            arquivo = pasta / f"{id_req}.md"
            
            if arquivo.exists():
                try:
                    conteudo = arquivo.read_text(encoding="utf-8")
                    resultados.append(f"--- Arquivo: {arquivo} ---\n{conteudo}")
                    arquivos_lidos += 1
                except Exception as e:
                    resultados.append(f"--- Erro ao ler {arquivo.name}: {e} ---")
            else:
                nao_encontrados.append(id_req)
        
        if not resultados:
            msg = "Nenhum artefato encontrado."
            if nao_encontrados:
                msg += f" IDs não encontrados: {', '.join(nao_encontrados)}"
            return msg
        
        header = f"Total de artefatos lidos: {arquivos_lidos}\n"
        if nao_encontrados:
            header += f"IDs não encontrados: {', '.join(nao_encontrados)}\n"
        header += "\n"
        return header + "\n\n".join(resultados)
    
    # Modo 2: Filtro por tipo ou todos

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
