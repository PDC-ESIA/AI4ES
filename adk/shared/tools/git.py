"""Ferramentas Git compartilhadas entre agentes."""

import subprocess
from subprocess import run


def tool_git_add(arquivos: str, cwd: str | None = None) -> dict:
    """Ferramenta usada para executar git add no terminal e adicionar arquivos

    Args:
        arquivos (str): Parâmetro de inserção dos arquivos a serem adicionados
        cwd (str): Diretório de trabalho para execução do comando (injetado pela factory)

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
        text=True,
        cwd=cwd,
    )

    return {
        "sucesso": resposta.returncode == 0,
        "stdout": resposta.stdout,
        "stderr": resposta.stderr,
        "returncode": resposta.returncode
    }


def tool_preparar_commit(mensagem: str, cwd: str | None = None) -> dict:
    """Ferramenta usada para validar se há alterações prontas para commit e retornar o diff para análise.
    NÃO executa o commit, apenas prepara o resumo. Apresente o resumo retornado ao usuário e aguarde autorização.

    Args:
        mensagem (str): Mensagem de commit sugerida pelo agente
        cwd (str): Diretório de trabalho para execução do comando

    Returns:
        dict: Contém status da validação, mensagem e diff das alterações staged
    """

    diff_res = run(
        ["git", "diff", "--staged"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )

    diff = diff_res.stdout

    if not diff.strip():
        return {
            "sucesso": False,
            "mensagem": "Nada para commitar (working tree clean ou alterações não adicionadas com git add)"
        }

    return {
        "sucesso": True,
        "mensagem": mensagem,
        "diff": diff
    }


def tool_confirmar_commit(mensagem: str, cwd: str | None = None) -> dict:
    """Ferramenta usada para efetivar o git commit no terminal após aprovação do usuário.
    SÓ DEVE ser chamada após o usuário aprovar o resumo gerado por tool_preparar_commit.

    Args:
        mensagem (str): Mensagem do commit
        cwd (str): Diretório de trabalho para execução do comando (injetado pela factory)

    Returns:
        dict: Contém status da operação, saída do comando e possíveis erros
    """

    # Verificação final para evitar commits vazios
    diff_res = run(
        ["git", "diff", "--staged"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if not diff_res.stdout.strip():
        return {
            "sucesso": False,
            "mensagem": "Nada para commitar no momento da confirmação"
        }

    resposta = run(
        ['git', 'commit', '-m', mensagem],
        capture_output=True,
        text=True,
        cwd=cwd,
    )

    return {
        "sucesso": resposta.returncode == 0,
        "stdout": resposta.stdout,
        "stderr": resposta.stderr,
        "returncode": resposta.returncode
    }


def tool_git_checkout(branch: str, criar: bool = False, cwd: str | None = None) -> dict:
    """Ferramenta para trocar/criar uma branch

    Args:
        branch (str): Nome da branch
        criar (bool): Informar se vai ser criada a branch, se True cria a branch antes de trocar
        cwd (str): Diretório de trabalho para execução do comando (injetado pela factory)

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
        text=True,
        cwd=cwd,
    )

    return {
        "sucesso": resposta_checkout.returncode == 0,
        "comando": comando,
        "stdout": resposta_checkout.stdout,
        "stderr": resposta_checkout.stderr,
        "returncode": resposta_checkout.returncode
    }


def tool_ler_diff(branch_alvo: str = "main", cwd: str | None = None) -> dict:
    """Extrai diferenças de código (diff) via Git.

    Args:
        branch_alvo: Branch contra a qual comparar.
        cwd: Diretório de trabalho para execução do comando (injetado pela factory).

    Returns:
        dict com sucesso, erro e diff.
    """
    resposta = subprocess.run(
        ["git", "diff", branch_alvo],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
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