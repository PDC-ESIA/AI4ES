"""Ferramentas Git compartilhadas entre agentes."""

import subprocess
from subprocess import run
from typing import Optional


def _resolve_cwd(cwd: Optional[str]) -> Optional[str]:
    """Normaliza cwd: string vazia ou None → None (usa dir corrente)."""
    return cwd if cwd else None


def tool_git_add(arquivos: str, *, cwd: Optional[str] = None) -> dict:
    """Adiciona arquivos ao stage do Git (git add).

    Use depois de criar ou editar arquivos, quando estiver pronto para
    preparar a mudança para versionamento. Recebe nomes de arquivo
    separados por espaço; quando string vazia, equivale a `git add .`
    (use com cautela — preferir listar arquivos explicitamente).

    Args:
        arquivos: Lista de paths separados por espaço (ex:
            "src/app.py tests/test_app.py"). Vazio = `git add .`
            (todos os modificados).
        cwd: Diretório de execução do comando git. Injetado pela
            factory quando aplicável.

    Returns:
        dict com chaves: `sucesso` (bool), `stdout` (str), `stderr`
        (str), `returncode` (int). `sucesso=True` quando returncode==0.
    """

    if arquivos:
        comando = ["git", "add"] + arquivos.split()

    else:
        comando = ["git", "add", "."]

    resposta = run(comando, capture_output=True, text=True, cwd=_resolve_cwd(cwd))

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

    diff_res = run(["git", "diff", "--staged"], capture_output=True, text=True, cwd=_resolve_cwd(cwd))

    diff = diff_res.stdout

    if not diff.strip():
        return {"sucesso": False, "mensagem": "Nada para commitar"}

    return {"sucesso": True, "mensagem": mensagem, "diff": diff}


def tool_git_commit(mensagem: str, *, cwd: Optional[str] = None) -> dict:
    """Registra um commit no Git com a mensagem fornecida.

    Esta tool registra o commit DIRETAMENTE — não há gate de aprovação
    embutido (apesar do nome). Em fluxos com supervisão humana, NÃO use
    esta tool: use o par `tool_preparar_commit` (apresenta diff/resumo) e
    `tool_confirmar_commit` (efetiva após o "sim" do supervisor) para
    obter a trava de aprovação real. A tool valida internamente que há
    alterações staged antes de commitar; sem stage, retorna falha
    sem efeito.

    Convenção de mensagem do projeto (Conventional Commits):
    `<tipo>(<escopo>): #<issue> <descrição>`. Tipos permitidos:
    feat, fix, docs, refactor, test, chore, ci, style, perf.

    Args:
        mensagem: Mensagem completa do commit, já formatada conforme
            Conventional Commits.
        cwd: Diretório de execução do comando git. Injetado pela
            factory.

    Returns:
        dict com chaves: `sucesso` (bool), `stdout`, `stderr`,
        `returncode` em caso de execução. Quando não há nada para
        commitar: `{sucesso: False, mensagem: "Nada para commitar"}`.
    """

    trava = trava_seguranca_git_commit(mensagem, cwd=_resolve_cwd(cwd))

    if not trava["sucesso"]:
        return {"sucesso": False, "mensagem": trava["mensagem"]}

    aprovado = True

    if not aprovado:
        return {"sucesso": False, "mensagem": "Commit não autorizado"}

    resposta = run(["git", "commit", "-m", mensagem], capture_output=True, text=True, cwd=_resolve_cwd(cwd))

    return {
        "sucesso": resposta.returncode == 0,
        "stdout": resposta.stdout,
        "stderr": resposta.stderr,
        "returncode": resposta.returncode,
    }


def tool_git_checkout(branch: str, criar: bool = False, *, cwd: Optional[str] = None) -> dict:
    """Troca ou cria uma branch de trabalho no Git.

    Use no início de uma tarefa para isolar a mudança em sua própria
    branch (recomendado o padrão do projeto:
    `feature/code/<issue>-descricao-curta` ou
    `hotfix/code/<issue>-descricao-curta`). Para alternar entre branches
    já existentes, use `criar=False`; para inicializar nova branch,
    `criar=True`.

    Args:
        branch: Nome da branch alvo.
        criar: Se True, executa `git checkout -b` criando a branch
            antes de trocar. Default False.
        cwd: Diretório de execução. Injetado pela factory.

    Returns:
        dict com chaves: `sucesso` (bool), `comando` (lista do shell
        executado), `stdout`, `stderr`, `returncode`.
    """

    if criar:
        comando = ["git", "checkout", "-b"] + branch.split()
    else:
        comando = ["git", "checkout"] + branch.split()

    resposta_checkout = run(comando, capture_output=True, text=True, cwd=_resolve_cwd(cwd))

    return {
        "sucesso": resposta_checkout.returncode == 0,
        "comando": comando,
        "stdout": resposta_checkout.stdout,
        "stderr": resposta_checkout.stderr,
        "returncode": resposta_checkout.returncode,
    }


def tool_ler_diff(branch_alvo: str = "main", *, cwd: Optional[str] = None) -> dict:
    """Lê o diff acumulado da branch atual em relação a outra branch.

    Use durante uma revisão de código para inspecionar TODAS as
    alterações pendentes — arquivos criados, modificados, deletados —
    em formato unified diff. Tipicamente compara contra `main`, mas
    aceita qualquer branch como alvo.

    IMPORTANTE: a comparação é `git diff <branch>`, que inclui o
    working tree (mudanças não commitadas), não apenas commits.
    Para comparar somente commits, prefira `git diff <branch>...HEAD`
    (não suportado por esta tool atualmente).

    Args:
        branch_alvo: Branch contra a qual comparar. Default "main".
        cwd: Diretório de execução. Injetado pela factory.

    Returns:
        dict com chaves: `sucesso` (bool), `erro` (str ou None),
        `diff` (str unified diff em sucesso, None em falha). Quando
        não há diferenças, retorna `sucesso=False` com erro explicando.
    """
    resposta = subprocess.run(
        ["git", "diff", branch_alvo],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=_resolve_cwd(cwd),
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


def tool_preparar_commit(mensagem: str, *, cwd: Optional[str] = None) -> dict:
    """Valida o stage e retorna o diff para o agente apresentar ao supervisor.

    Esta é a primeira metade do protocolo human-in-the-loop de commit:
    primeiro o agente prepara o commit (esta tool), apresenta o resumo
    do diff ao supervisor, aguarda autorização explícita, e só então
    chama a tool de confirmação para efetivar.

    NÃO executa o commit — apenas valida que há algo staged e devolve
    o diff. Use sempre antes de propor uma versão para aprovação.

    Args:
        mensagem: Mensagem de commit sugerida pelo agente, já formatada
            em Conventional Commits.
        cwd: Diretório de execução. Injetado pela factory.

    Returns:
        dict com chaves: `sucesso` (bool), `mensagem` (echo da
        mensagem em sucesso, motivo em falha), `diff` (str unified
        diff staged em sucesso). `sucesso=False` quando working tree
        clean ou nada em stage.
    """
    diff_res = run(
        ["git", "diff", "--staged"],
        capture_output=True,
        text=True,
        cwd=_resolve_cwd(cwd),
    )
    diff = diff_res.stdout
    if not diff.strip():
        return {
            "sucesso": False,
            "mensagem": "Nada para commitar (working tree clean ou alterações não foram adicionadas com git add).",
        }
    return {"sucesso": True, "mensagem": mensagem, "diff": diff}


def tool_confirmar_commit(mensagem: str, *, cwd: Optional[str] = None) -> dict:
    """Efetiva o commit Git após autorização do supervisor — segunda metade do gate.

    SÓ DEVE ser chamada após o supervisor ter respondido autorização
    explícita ao resumo apresentado via tool_preparar_commit. Esta tool
    é tipicamente registrada com require_confirmation=True como dupla
    trava de segurança.

    Re-valida o stage (defensivamente) antes de commitar — se nada
    estiver staged no momento da confirmação, retorna falha.

    Args:
        mensagem: Mensagem de commit. Idealmente a mesma apresentada
            via tool_preparar_commit para garantir consistência.
        cwd: Diretório de execução. Injetado pela factory.

    Returns:
        dict com chaves: `sucesso` (bool), `stdout`, `stderr`,
        `returncode` em execução. Em ausência de stage no momento da
        confirmação:
        `{sucesso: False, mensagem: "Nada para commitar no momento da confirmação."}`.
    """
    diff_res = run(
        ["git", "diff", "--staged"],
        capture_output=True,
        text=True,
        cwd=_resolve_cwd(cwd),
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
        cwd=_resolve_cwd(cwd),
    )
    return {
        "sucesso": resposta.returncode == 0,
        "stdout": resposta.stdout,
        "stderr": resposta.stderr,
        "returncode": resposta.returncode,
    }
