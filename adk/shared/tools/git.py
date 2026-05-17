"""Ferramentas Git compartilhadas entre agentes."""

import subprocess
from subprocess import run


def tool_git_add(arquivos: str, *, cwd: str | None = None) -> dict:
    """Ferramenta usada para executar git add no terminal e adicionar arquivos

    Args:
        arquivos (str): Parâmetro de inserção dos arquivos a serem adicionados
        cwd (str | None): Diretório de execução (injetado pela factory quando aplicável).

    Returns:
        dict: Contém status da operação, saída e erros
    """

    if arquivos:
        comando = ["git", "add"] + arquivos.split()

    else:
        comando = ["git", "add", "."]

    resposta = run(comando, capture_output=True, text=True, cwd=cwd)

    return {
        "sucesso": resposta.returncode == 0,
        "stdout": resposta.stdout,
        "stderr": resposta.stderr,
        "returncode": resposta.returncode,
    }


def trava_seguranca_git_commit(mensagem: str, *, cwd: str | None = None) -> dict:
    """Ferramenta usada para validar se há alterações prontas para commit e retornar o diff para análise

    Args:
        mensagem (str): Mensagem de commit sugerida pelo agente
        cwd (str | None): Diretório de execução (injetado pela factory quando aplicável).

    Returns:
        dict: Contém status da validação, mensagem e diff das alterações staged
    """

    diff_res = run(["git", "diff", "--staged"], capture_output=True, text=True, cwd=cwd)

    diff = diff_res.stdout

    if not diff.strip():
        return {"sucesso": False, "mensagem": "Nada para commitar"}

    return {"sucesso": True, "mensagem": mensagem, "diff": diff}


def tool_git_commit(mensagem: str, *, cwd: str | None = None) -> dict:
    """Ferramenta usada para executar git commit no terminal

    Args:
        mensagem (str): Parâmetro da mensagem que o agente designa para o commit
        cwd (str | None): Diretório de execução (injetado pela factory quando aplicável).

    Returns:
        dict: Contém status da operação, saída do comando e possíveis erros
    """

    trava = trava_seguranca_git_commit(mensagem, cwd=cwd)

    if not trava["sucesso"]:
        return {"sucesso": False, "mensagem": trava["mensagem"]}

    aprovado = True

    if not aprovado:
        return {"sucesso": False, "mensagem": "Commit não autorizado"}

    resposta = run(["git", "commit", "-m", mensagem], capture_output=True, text=True, cwd=cwd)

    return {
        "sucesso": resposta.returncode == 0,
        "stdout": resposta.stdout,
        "stderr": resposta.stderr,
        "returncode": resposta.returncode,
    }


def tool_git_checkout(branch: str, criar: bool = False, *, cwd: str | None = None) -> dict:
    """Ferramenta para trocar/criar uma branch

    Args:
        branch (str): Nome da branch
        criar (bool): Informar se vai ser criada a branch, se True cria a branch antes de trocar
        cwd (str | None): Diretório de execução (injetado pela factory quando aplicável).

    Returns:
        dict: Retorna o resultado da execução do comando de checkout
    """

    if criar:
        comando = ["git", "checkout", "-b"] + branch.split()
    else:
        comando = ["git", "checkout"] + branch.split()

    resposta_checkout = run(comando, capture_output=True, text=True, cwd=cwd)

    return {
        "sucesso": resposta_checkout.returncode == 0,
        "comando": comando,
        "stdout": resposta_checkout.stdout,
        "stderr": resposta_checkout.stderr,
        "returncode": resposta_checkout.returncode,
    }


def tool_ler_diff(branch_alvo: str = "main", *, cwd: str | None = None) -> dict:
    """Extrai diferenças de código (diff) via Git.

    Args:
        branch_alvo: Branch contra a qual comparar.
        cwd (str | None): Diretório de execução (injetado pela factory quando aplicável).

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
        return {
            "sucesso": False,
            "erro": f"Falha no git diff: {resposta.stderr}",
            "diff": None,
        }

    if not resposta.stdout.strip():
        return {
            "sucesso": False,
            "erro": f"Nenhuma alteração encontrada em relação à branch '{branch_alvo}'.",
            "diff": None,
        }

    return {"sucesso": True, "erro": None, "diff": resposta.stdout}


def tool_preparar_commit(mensagem: str, *, cwd: str | None = None) -> dict:
    """Valida se há alterações staged e retorna o diff para análise.
    NÃO executa o commit. Apresente o resumo retornado ao usuário e aguarde autorização.
    Apenas após a aprovação chame tool_confirmar_commit com a mesma mensagem.

    Args:
        mensagem (str): Mensagem de commit sugerida pelo agente.
        cwd (str | None): Diretório de execução (injetado pela factory quando aplicável).

    Returns:
        dict: {sucesso, mensagem, diff} ou {sucesso=False, mensagem=motivo}.
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
            "mensagem": "Nada para commitar (working tree clean ou alterações não foram adicionadas com git add).",
        }
    return {"sucesso": True, "mensagem": mensagem, "diff": diff}


def tool_confirmar_commit(mensagem: str, *, cwd: str | None = None) -> dict:
    """Efetiva o git commit. SÓ DEVE ser chamada após o usuário aprovar o resumo
    gerado por tool_preparar_commit. Esta tool deve ser registrada no agente com
    require_confirmation=True como dupla trava.

    Args:
        mensagem (str): Mensagem do commit (idealmente a mesma de tool_preparar_commit).
        cwd (str | None): Diretório de execução (injetado pela factory quando aplicável).

    Returns:
        dict: {sucesso, stdout, stderr, returncode} ou {sucesso=False, mensagem=motivo}.
    """
    diff_res = run(
        ["git", "diff", "--staged"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if not diff_res.stdout.strip():
        return {
            "sucesso": False,
            "mensagem": "Nada para commitar no momento da confirmação.",
        }

    resposta = run(
        ["git", "commit", "-m", mensagem],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return {
        "sucesso": resposta.returncode == 0,
        "stdout": resposta.stdout,
        "stderr": resposta.stderr,
        "returncode": resposta.returncode,
    }
