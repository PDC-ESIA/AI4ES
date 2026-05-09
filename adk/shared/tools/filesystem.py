"""Ferramentas de filesystem compartilhadas entre agentes."""

from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, field_validator

EXTENSOES_PERMITIDAS = {
    ".py", ".js", ".ts", ".html", ".css", ".json",
    ".md", ".txt", ".yaml", ".yml", ".toml", ".env.example",
}

DIRETORIOS_PROIBIDOS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".env",
}


class RelatorioSchema(BaseModel):
    conteudo: str = Field(..., description="Conteúdo em Markdown do relatório")
    nome_arquivo: str = Field(
        default="doubt_artifact_revisao.md",
        description="Nome do arquivo de saída",
    )

    @field_validator("nome_arquivo")
    @classmethod
    def validar_extensao(cls, v: str) -> str:
        if not v.endswith(".md"):
            raise ValueError("O relatório DEVE ser um arquivo Markdown (.md)")
        return v


def _resolver_caminho(caminho: str, base_dir: str | None = None) -> Path:
    """Resolve caminho relativo ao base_dir (se informado) com proteção anti-traversal.

    Args:
        caminho: Caminho informado pelo agente.
        base_dir: Diretório base do agente no workspace (opcional).

    Returns:
        Path resolvido e validado.

    Raises:
        ValueError: Se o caminho tenta escapar do base_dir.
    """
    if base_dir is None:
        return Path(caminho)

    base = Path(base_dir).resolve()
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

    resolved = (base / rel).resolve()

    if not str(resolved).startswith(str(base)):
        raise ValueError(
            f"Caminho '{caminho}' escapa do diretório de trabalho do agente."
        )

    return resolved


def tool_criar_arquivo(caminho: str, conteudo: str, base_dir: str | None = None) -> dict:
    """Ferramenta para criar ou sobrescrever um arquivo no disco com o conteúdo fornecido.
    Use esta ferramenta SEMPRE que precisar escrever um arquivo completo do zero.

    Possui validações de segurança:
    - Só permite extensões conhecidas e seguras
    - Impede escrita em diretórios protegidos (.git, .venv, etc.)
    - Cria diretórios intermediários automaticamente se necessário

    Args:
        caminho (str): Caminho relativo ao diretório de trabalho atual
        conteudo (str): Conteúdo completo a ser escrito no arquivo
        base_dir (str): Diretório base do agente no workspace (injetado pela factory)

    Returns:
        dict: Contém status da operação, caminho absoluto criado e possíveis erros
    """

    if not caminho or not caminho.strip():
        return {
            "sucesso": False,
            "erro": "Caminho do arquivo não pode ser vazio.",
            "caminho": None
        }

    try:
        path = _resolver_caminho(caminho, base_dir)
    except ValueError as e:
        return {"sucesso": False, "erro": str(e), "caminho": caminho}

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


def tool_salvar_relatorio(
    conteudo: str,
    nome_arquivo: str = "doubt_artifact_revisao.md",
    base_dir: str | None = None,
) -> dict:
    """Salva relatório de revisão em Markdown no disco.

    Args:
        conteudo: Texto do relatório.
        nome_arquivo: Nome do arquivo (padrão: doubt_artifact_revisao.md).
        base_dir: Diretório base do agente no workspace (injetado pela factory).

    Returns:
        dict com sucesso, caminho, bytes_escritos e erro.
    """
    try:
        dados = RelatorioSchema(conteudo=conteudo, nome_arquivo=nome_arquivo)
    except ValidationError as e:
        return {"sucesso": False, "erro": f"Parâmetros inválidos: {e}", "caminho": None}

    try:
        path = _resolver_caminho(dados.nome_arquivo, base_dir)
    except ValueError as e:
        return {"sucesso": False, "erro": str(e), "caminho": dados.nome_arquivo}

    if base_dir is None:
        # Retrocompatível: sem base_dir, manter validação original
        if path.is_absolute() or ".." in path.parts:
            return {
                "sucesso": False,
                "erro": "Caminho deve ser relativo e sem '..'.",
                "caminho": str(path),
            }

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dados.conteudo, encoding="utf-8")
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(path.resolve()),
            "bytes_escritos": len(dados.conteudo.encode("utf-8")),
        }
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro ao salvar relatório: {e}", "caminho": str(path)}


def tool_ler_arquivo(caminho: str, base_dir: str | None = None) -> str:
    """Lê o conteúdo de um arquivo existente no disco.
    Use esta ferramenta para ler e analisar códigos ANTES de modificá-los ou corrigi-los.

    Args:
        caminho (str): Caminho do arquivo a ser lido.
        base_dir (str): Diretório base do agente no workspace (injetado pela factory).
    """
    try:
        path = _resolver_caminho(caminho, base_dir)
    except ValueError as e:
        return f"Erro: {e}"

    try:
        if not path.is_file():
            return f"Erro: O arquivo '{caminho}' não existe ou não é um arquivo válido."
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Erro inesperado ao ler o arquivo '{caminho}': {str(e)}"


def tool_substituir_trecho(
    caminho: str,
    trecho_antigo: str,
    trecho_novo: str,
    base_dir: str | None = None,
) -> str:
    """Use esta ferramenta para editar arquivos JÁ EXISTENTES, evitando reescrever o arquivo inteiro.
    Substitui um trecho de código existente (trecho_antigo) por um novo trecho (trecho_novo) em um arquivo.
    Regra CRÍTICA: O 'trecho_antigo' deve ser uma cópia EXATA do trecho atual do arquivo,
    incluindo qualquer espaço, indentação e quebra de linha.

    Args:
        caminho (str): Caminho do arquivo a ser editado.
        trecho_antigo (str): Trecho exato a ser substituído.
        trecho_novo (str): Novo trecho que substituirá o antigo.
        base_dir (str): Diretório base do agente no workspace (injetado pela factory).
    """
    try:
        path = _resolver_caminho(caminho, base_dir)
    except ValueError as e:
        return f"Erro: {e}"

    try:
        if not path.is_file():
            return f"Erro: O arquivo '{caminho}' não existe. Use tool_escrever_arquivo para criar arquivos novos."

        content = path.read_text(encoding="utf-8")

        if trecho_antigo not in content:
            return f"Erro: 'trecho_antigo' não foi encontrado da maneira exata que você informou no arquivo '{caminho}'. Lembre-se, tem que ser IDÊNTICO ao que foi retornado por tool_ler_arquivo."

        new_file_content = content.replace(trecho_antigo, trecho_novo, 1)
        path.write_text(new_file_content, encoding="utf-8")

        return f"Sucesso: O bloco de código foi substituído no arquivo '{caminho}'."

    except Exception as e:
        return f"Erro inesperado ao editar o arquivo '{caminho}': {str(e)}"
