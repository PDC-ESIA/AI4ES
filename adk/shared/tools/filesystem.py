import os
from pathlib import Path

def tool_criar_arquivo(caminho: str, conteudo: str) -> str:
    """Cria um arquivo simples com o conteúdo fornecido."""
    try:
        path = Path(caminho)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(conteudo, encoding="utf-8")
        return f"Arquivo criado com sucesso: {caminho}"
    except Exception as e:
        return f"ERRO ao criar arquivo: {str(e)}"

def tool_salvar_relatorio(caminho: str, conteudo: str) -> str:
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
