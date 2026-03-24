import logging
import requests
from datetime import datetime
from google.adk.tools import ToolContext
from pydantic import BaseModel, Field, field_validator
from subprocess import run
import os
from pathlib import Path


def tool_git_add(arquivos: str) -> dict:
    """Ferramenta usada para executar git add no terminal e adicionar arquivos
    
    Args:
        arquivos (str): Parâmetro de inserção dos arquivos a serem adicionados

    Returns:
        dict: Contém status da operação, saída e erros    
    """
    
    if arquivos:
        comando = ['git', 'add'] + arquivos.split()

    else:
        comando = ['git', 'add', '.']

    resposta = run(
        comando,
        capture_output=True,
        text=True
    )

    return {
        "sucesso": resposta.returncode == 0,
        "stdout": resposta.stdout,
        "stderr": resposta.stderr,
        "returncode": resposta.returncode
        }


def trava_seguranca_git_commit(mensagem: str) -> dict:
    """Ferramenta usada para validar se há alterações prontas para commit e retornar o diff para análise
    
    Args:
        mensagem (str): Mensagem de commit sugerida pelo agente

    Returns:
        dict: Contém status da validação, mensagem e diff das alterações staged
    """

    diff_res = run(
        ["git", "diff", "--staged"],
        capture_output=True,
        text=True
    )

    diff = diff_res.stdout

    if not diff.strip():
        return {
            "sucesso": False,
            "mensagem": "Nada para commitar"
        }
    
    return {
        "sucesso": True,
        "mensagem": mensagem,
        "diff": diff
    }


def tool_git_commit(mensagem: str) -> dict:
    """Ferramenta usada para executar git commit no terminal
    
    Args:
        mensagem (str): Parâmetro da mensagem que o agente designa para o commit
    

    Returns:
        dict: Contém status da operação, saída do comando e possíveis erros
    """
    
    trava = trava_seguranca_git_commit(mensagem)

    if not trava["sucesso"]:
        return {
            "sucesso": False,
            "mensagem": trava["mensagem"]
        }
    
    aprovado = True

    if not aprovado:
        return {
            "sucesso": False,
            "mensagem": "Commit não autorizado"
        }
        

    resposta = run(
        ['git', 'commit', '-m', mensagem],
        capture_output=True,
        text=True
    )

    return {
        "sucesso": resposta.returncode == 0,
        "stdout": resposta.stdout,
        "stderr": resposta.stderr,
        "returncode": resposta.returncode
    }


def tool_git_checkout(branch: str, criar: bool = False) -> dict:
    """Ferramenta para trocar/criar uma branch
    
    Args:
        branch (str): Nome da branch
        criar (bool): Informar se vai ser criada a branch, se True cria a branch antes de trocar
        
    Returns:
        dict: Retorna o resultado da execução do comando de checkout
    """

    if criar:
        comando = ['git', 'checkout', '-b'] + branch.split()
    else:
        comando = ['git', 'checkout'] + branch.split()

    resposta_checkout = run(
        comando,
        capture_output=True,
        text=True
    )

    return {
        "sucesso": resposta_checkout.returncode == 0,
        "comando": comando,
        "stdout": resposta_checkout.stdout,
        "stderr": resposta_checkout.stderr,
        "returncode": resposta_checkout.returncode
    }


EXTENSOES_PERMITIDAS = {
    ".py", ".js", ".ts", ".html", ".css", ".json",
    ".md", ".txt", ".yaml", ".yml", ".toml", ".env.example"
}


DIRETORIOS_PROIBIDOS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".env"
}
 
 
def tool_criar_arquivo(caminho: str, conteudo: str) -> dict:
    """Ferramenta para criar ou sobrescrever um arquivo no disco com o conteúdo fornecido.
 
    Possui validações de segurança:
    - Só permite extensões conhecidas e seguras
    - Impede escrita em diretórios protegidos (.git, .venv, etc.)
    - Cria diretórios intermediários automaticamente se necessário
 
    Args:
        caminho (str): Caminho relativo ao diretório de trabalho atual 
        conteudo (str): Conteúdo completo a ser escrito no arquivo
 
    Returns:
        dict: Contém status da operação, caminho absoluto criado e possíveis erros
    """
 
    if not caminho or not caminho.strip():
        return {
            "sucesso": False,
            "erro": "Caminho do arquivo não pode ser vazio.",
            "caminho": None
        }
 
    path = Path(caminho)
 
    partes = set(path.parts[:-1])  
    bloqueados = partes & DIRETORIOS_PROIBIDOS
    if bloqueados:
        return {
            "sucesso": False,
            "erro": f"Escrita não permitida em diretório protegido: {bloqueados}",
            "caminho": caminho
        }
 
    if path.suffix not in EXTENSOES_PERMITIDAS:
        return {
            "sucesso": False,
            "erro": (
                f"Extensão '{path.suffix}' não permitida. "
                f"Permitidas: {', '.join(sorted(EXTENSOES_PERMITIDAS))}"
            ),
            "caminho": caminho
        }


    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(conteudo, encoding="utf-8")
 
        return {
            "sucesso": True,
            "caminho": str(path.resolve()),
            "bytes_escritos": len(conteudo.encode("utf-8")),
            "erro": None
        }
 
    except PermissionError as e:
        return {
            "sucesso": False,
            "erro": f"Permissão negada: {e}",
            "caminho": caminho
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": f"Erro inesperado: {e}",
            "caminho": caminho
        }
 