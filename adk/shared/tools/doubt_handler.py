import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict

def registrar_duvida(
    id_artefato: str,
    descricao: str,
    categoria: str,
    severidade: str,
    contexto: Optional[str] = None,
    sugestao: Optional[str] = None,
    caminho_projeto: str = "."
) -> str:
    """
    Registra uma dúvida no arquivo Doubt_Artifact.md do projeto ou cria um novo se não existir.
    
    Args:
        id_artefato: Identificador do artefato afetado (ex: HU-001, test_login).
        descricao: Descrição clara da dúvida ou incerteza.
        categoria: Categoria da dúvida (Falta de Contexto, Bloqueio Lógico, Ambiguidade, Erro Técnico).
        severidade: Nível de criticidade (Baixa, Média, Alta, Crítica).
        contexto: Trecho de código, prompt ou referência que gerou a dúvida.
        sugestao: Sugestão do agente para resolução.
        caminho_projeto: Caminho base para salvar o artefato.
        
    Returns:
        Caminho do arquivo de dúvida atualizado.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    base_path = Path(caminho_projeto)
    doubt_file = base_path / "Doubt_Artifact.md"
    
    # Template para uma nova entrada
    nova_entrada = f"""
### [D-{datetime.now().strftime("%y%m%d%H%M%S")}] - {id_artefato}
- **Data:** {timestamp}
- **Categoria:** {categoria}
- **Severidade:** {severidade}
- **Descrição:** {descricao}
- **Contexto:** {contexto if contexto else "N/A"}
- **Sugestão do Agente:** {sugestao if sugestao else "N/A"}
- **Status:** 🔴 Aberta
- **Resposta Humana:** _(Aguardando revisão)_

---
"""

    if not doubt_file.exists():
        header = f"""# Doubt Artifact — Registro de Dúvidas e Bloqueios
Este arquivo centraliza as dúvidas identificadas pelos agentes para revisão humana (Human-in-the-Loop).

## Histórico de Dúvidas
"""
        with open(doubt_file, "w", encoding="utf-8") as f:
            f.write(header)
            f.write(nova_entrada)
    else:
        with open(doubt_file, "a", encoding="utf-8") as f:
            f.write(nova_entrada)
            
    return str(doubt_file.absolute())

def listar_duvidas_pendentes(caminho_projeto: str = ".") -> List[Dict]:
    """
    Lê o arquivo Doubt_Artifact.md e retorna as dúvidas que ainda não possuem resposta.
    """
    doubt_file = Path(caminho_projeto) / "Doubt_Artifact.md"
    if not doubt_file.exists():
        return []
    
    # Lógica simples de parseamento para exemplo (em produção usaria regex ou parser MD)
    with open(doubt_file, "r", encoding="utf-8") as f:
        conteudo = f.read()
    
    duvidas = []
    # Divide por seções de dúvida
    secoes = conteudo.split("### [D-")[1:]
    for secao in secoes:
        if "🔴 Aberta" in secao:
            # Extração básica de metadados
            linhas = secao.split("\n")
            id_full = "D-" + linhas[0].split("]")[0]
            duvidas.append({
                "id": id_full,
                "status": "Aberta",
                "preview": linhas[4] if len(linhas) > 4 else ""
            })
            
    return duvidas

def registrar_resposta_humana(id_duvida: str, resposta: str, caminho_projeto: str = ".") -> bool:
    """
    Atualiza uma dúvida específica com a resposta fornecida pelo humano.
    """
    doubt_file = Path(caminho_projeto) / "Doubt_Artifact.md"
    if not doubt_file.exists():
        return False
        
    with open(doubt_file, "r", encoding="utf-8") as f:
        linhas = f.readlines()
        
    updated = False
    for i, linha in enumerate(linhas):
        if f"### [{id_duvida}]" in linha:
            # Procura o campo de status e resposta nas próximas linhas
            for j in range(i+1, min(i+10, len(linhas))):
                if "- **Status:**" in linhas[j]:
                    linhas[j] = "- **Status:** ✅ Resolvida\n"
                if "- **Resposta Humana:**" in linhas[j]:
                    linhas[j] = f"- **Resposta Humana:** {resposta}\n"
                    updated = True
                    break
        if updated: break
            
    if updated:
        with open(doubt_file, "w", encoding="utf-8") as f:
            f.writelines(linhas)
            
    return updated
