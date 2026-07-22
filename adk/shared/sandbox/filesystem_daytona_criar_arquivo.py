"""Versão da tool de criação de arquivo usando sandbox Daytona.

Mesma assinatura e validações de shared/tools/filesystem.py, trocando
apenas o destino final da escrita: sandbox remoto em vez de disco local.
"""

from pathlib import Path
from typing import Optional

from shared.sandbox.session_sandbox import get_or_create_sandbox
from shared.tools.filesystem import (
    DIRETORIOS_PROIBIDOS,
    EXTENSOES_PERMITIDAS,
    NOMES_PERMITIDOS,
    _resolver_caminho,
)

def _resolver_caminho_daytona(caminho: str, base_dir: Optional[str] = None) -> Path:
    """Resolve caminhos virtuais para o sandbox Daytona com proteção anti-traversal.

    Diferente de _resolver_caminho, esta função NÃO chama .resolve() no SO
    local, evitando que caminhos da máquina host (ex: /home/usuario/...)
    vazem para dentro da árvore de diretórios do container remoto.

    Args:
        caminho: Caminho informado pelo agente (ex: "ola.py" ou "src/main.py").
        base_dir: Subpasta virtual no sandbox (ex: "workspace/coder").

    Returns:
        Path relativo limpo para ser usado no Daytona SDK.

    Raises:
        ValueError: Se o caminho tentar usar '..' ou for absoluto.
    """
    rel = Path(caminho)

    if rel.is_absolute():
        raise ValueError(
            f"Caminho absoluto não permitido: '{caminho}'. "
            f"Use caminhos relativos ao seu diretório de trabalho."
        )

    if ".." in rel.parts:
        raise ValueError(
            f"Path traversal não permitido: '{caminho}'. "
            f"Não use '..' no caminho."
        )

    if base_dir:
        # Une base_dir e caminho em uma estrutura de Path virtual pura
        base = Path(base_dir.strip("/"))
        return base / rel

    return rel

def tool_criar_arquivo_daytona(
    caminho: str, conteudo: str, base_dir: Optional[str] = None
) -> dict:
    """Cria ou sobrescreve um arquivo dentro do sandbox Daytona da sessão.

    Mesmo comportamento e validações de tool_criar_arquivo, mas o
    destino é um sandbox remoto isolado em vez do disco local.

    Args:
        caminho: Caminho do arquivo, relativo a base_dir.
        conteudo: Texto completo a escrever (UTF-8).
        base_dir: Subpasta do agente dentro do sandbox (injetado pela
            factory, ex: "workspace/coder").

    Returns:
        dict com `sucesso`, `caminho`, `bytes_escritos`, `erro`.
    """
    if not caminho or not caminho.strip():
        return {"sucesso": False, "erro": "Caminho do arquivo não pode ser vazio.", "caminho": None}

    try:
        path = _resolver_caminho_daytona(caminho, base_dir)
    except ValueError as e:
        return {"sucesso": False, "erro": str(e), "caminho": caminho}

    partes = set(path.parts[:-1])
    bloqueados = partes & DIRETORIOS_PROIBIDOS
    if bloqueados:
        return {"sucesso": False, "erro": f"Escrita não permitida em diretório protegido: {bloqueados}", "caminho": caminho}

    if path.suffix not in EXTENSOES_PERMITIDAS and path.name not in NOMES_PERMITIDOS:
        return {"sucesso": False, "erro": f"Extensão '{path.suffix}' não permitida.", "caminho": caminho}

    # A ÚNICA parte que muda de verdade: destino da escrita
    try:
        sandbox = get_or_create_sandbox()
        
        try:
            sandbox.fs.create_folder("workspace", "777")
        except Exception:
            pass

        sandbox.fs.upload_file(conteudo.encode("utf-8"), str(path))
        return {
            "sucesso": True,
            "caminho": str(path),
            "bytes_escritos": len(conteudo.encode("utf-8")),
            "erro": None,
        }
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro ao escrever no sandbox: {e}", "caminho": caminho}