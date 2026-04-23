import os
from pathlib import Path

def tool_criar_arquivo(caminho: str, conteudo: str) -> dict:
    """Cria um arquivo com validações básicas de segurança."""
    caminho_limpo = (caminho or "").strip()
    retorno_base = {"sucesso": False, "caminho": caminho_limpo, "bytes_escritos": 0, "erro": None}
    extensoes_permitidas = {".py", ".md", ".json", ".txt", ".yaml", ".yml", ".toml", ".csv"}
    diretorios_protegidos = {".git", ".venv", "node_modules", "__pycache__"}

    try:
        if not caminho_limpo:
            retorno_base["erro"] = "Caminho vazio não permitido."
            return retorno_base

        path_relativo = Path(caminho_limpo)
        if path_relativo.is_absolute():
            retorno_base["erro"] = "Caminho absoluto não permitido."
            return retorno_base

        if ".." in path_relativo.parts:
            retorno_base["erro"] = "Caminho com '..' não permitido."
            return retorno_base

        if any(parte.lower() in diretorios_protegidos for parte in path_relativo.parts):
            retorno_base["erro"] = "Escrita em diretório protegido não permitida."
            return retorno_base

        if path_relativo.suffix.lower() not in extensoes_permitidas:
            retorno_base["erro"] = (
                f"Extensão não permitida: {path_relativo.suffix or '<sem extensão>'}."
            )
            return retorno_base

        raiz = Path.cwd().resolve()
        path_final = (raiz / path_relativo).resolve()
        if path_final != raiz and raiz not in path_final.parents:
            retorno_base["erro"] = "Caminho fora do diretório permitido."
            return retorno_base

        path_final.parent.mkdir(parents=True, exist_ok=True)
        path_final.write_text(conteudo, encoding="utf-8")
        return {
            "sucesso": True,
            "caminho": str(path_final),
            "bytes_escritos": len(conteudo.encode("utf-8")),
            "erro": None,
        }
    except Exception as e:
        retorno_base["erro"] = f"ERRO ao criar arquivo: {str(e)}"
        return retorno_base

def tool_salvar_relatorio(caminho: str, conteudo: str) -> dict:
    """Salva um relatório estruturado."""
    return tool_criar_arquivo(caminho, conteudo)

def tool_salvar_artefato_requisito(tipo: str, id_req: str, conteudo_md: str) -> str:
    """
    Salva um artefato de requisito (HU, RF, RNF, RN, Glossario).
    
    Args:
        tipo: Tipo do artefato (HU, RF, RNF, RN, Glossario)
        id_req: Identificador único do requisito (ex: HU-001, RF-002)
        conteudo_md: Conteúdo do artefato em formato Markdown   
    """
    # Mapeamento de pastas relativo à raiz do projeto
    # Em ambiente Docker do ADK, a raiz costuma ser o diretório pai ou o CWD
    mapa_pastas = {
        "HU": "docs/Time_1_Requisitos/HUs",
        "RF": "docs/Time_1_Requisitos/RFs",
        "RNF": "docs/Time_1_Requisitos/RNFs",
        "RN": "docs/Time_1_Requisitos/RNs",
        "Glossario": "docs/Time_1_Requisitos"
    }
    
    pasta_base = mapa_pastas.get(tipo, "docs/Time_1_Requisitos/Outros")
    
    try:
        os.makedirs(pasta_base, exist_ok=True)
        
        nome_arquivo = f"{id_req}.md" if tipo != "Glossario" else "Glossario.md"
        caminho_completo = os.path.join(pasta_base, nome_arquivo)
        
        with open(caminho_completo, "w", encoding="utf-8") as f:
            f.write(conteudo_md)
            
        return f"SUCESSO: {tipo} {id_req} salvo em {caminho_completo}"
    except Exception as e:
        return f"ERRO ao salvar artefato: {str(e)}"
