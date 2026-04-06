"""Ferramentas Git compartilhadas entre agentes."""

import subprocess
from subprocess import run


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


def tool_ler_diff(branch_alvo: str = "main") -> dict:
    """Extrai diferenças de código (diff) via Git.

    Args:
        branch_alvo: Branch contra a qual comparar.

    Returns:
        dict com sucesso, erro e diff.
    """
    resposta = subprocess.run(
        ["git", "diff", branch_alvo],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if resposta.returncode != 0:
        return {"sucesso": False, "erro": f"Falha no git diff: {resposta.stderr}", "diff": None}

    if not resposta.stdout.strip():
        return {
            "sucesso": False,
            "erro": f"Nenhuma alteração encontrada em relação à branch '{branch_alvo}'.",
            "diff": None,
        }

    return {"sucesso": True, "erro": None, "diff": resposta.stdout}
