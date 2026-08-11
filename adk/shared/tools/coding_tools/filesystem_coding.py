"""Ferramentas de filesystem compartilhadas entre agentes."""

import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

EXTENSOES_PERMITIDAS = {
    ".py",
    ".js",
    ".ts",
    ".html",
    ".css",
    ".json",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
    ".csv",
    ".env.example",
}

# Nomes de arquivo sem extensão (ou com extensão não-padrão) permitidos
# por serem artefatos legítimos de infraestrutura/build.
NOMES_PERMITIDOS = {
    "Dockerfile",
    ".dockerignore",
}

DIRETORIOS_PROIBIDOS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".env",
}

ID_REQ_PATTERN = re.compile(r"^[A-Z]{1,4}-\d{3}$")


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


def _resolver_caminho(caminho: str, base_dir: Optional[str] = None) -> Path:
    """Resolve caminho relativo ao base_dir (se informado) com proteção anti-traversal.

    Args:
        caminho: Caminho informado pelo agente.
        base_dir: Diretório base do agente no workspace (opcional).

    Returns:
        Path resolvido e validado.

    Raises:
        ValueError: Se o caminho tenta escapar do base_dir (absolute ou ..).
    """
    if base_dir is None:
        return Path(caminho)

    base = Path(base_dir).resolve()
    rel = Path(caminho)

    if rel.is_absolute():
        raise ValueError(
            f"Caminho absoluto não permitido com base_dir: '{caminho}'. "
            f"Use caminhos relativos ao seu diretório de trabalho."
        )

    if ".." in rel.parts:
        raise ValueError(
            f"Path traversal não permitido: '{caminho}'. "
            f"Não use '..' no caminho."
        )

    return base / rel


def tool_criar_arquivo(caminho: str, conteudo: str, base_dir: Optional[str] = None) -> dict:
    """Cria ou sobrescreve um arquivo no disco com o conteúdo fornecido.

    Use esta capacidade sempre que precisar materializar um arquivo do zero —
    código novo, documento, configuração. Se o arquivo já existir, o conteúdo
    é integralmente substituído (não é append). Diretórios intermediários são
    criados automaticamente.

    Não use para edição parcial de arquivos existentes; para isso há uma
    capacidade dedicada de substituição de trecho.

    Validações automáticas:
    - Só permite extensões: .py, .js, .ts, .html, .css, .json, .md, .txt,
      .yaml, .yml, .toml, .csv, .env.example.
    - Bloqueia escrita em .git, .venv, venv, node_modules, __pycache__, .env.

    Args:
        caminho: Caminho do arquivo. Quando há base_dir, é relativo a ele
            (não pode ser absoluto nem conter ".."). Sem base_dir, é relativo
            ao CWD do processo.
        conteudo: Texto completo a escrever (UTF-8).
        base_dir: Diretório base do agente injetado pela factory. Permite
            isolamento workspace-bound. Quando None, comportamento legado.

    Returns:
        dict com chaves: `sucesso` (bool), `caminho` (str do path resolvido
        ou input em caso de erro), `bytes_escritos` (int, só em sucesso),
        `erro` (str ou None). Em falha, `sucesso=False` e `erro` traz a
        mensagem.
    """
    if not caminho or not caminho.strip():
        return {
            "sucesso": False,
            "erro": "Caminho do arquivo não pode ser vazio.",
            "caminho": None,
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
            "caminho": caminho,
        }

    if path.suffix not in EXTENSOES_PERMITIDAS and path.name not in NOMES_PERMITIDOS:
        return {
            "sucesso": False,
            "erro": (
                f"Extensão '{path.suffix}' não permitida. "
                f"Permitidas: {', '.join(sorted(EXTENSOES_PERMITIDAS))}. "
                f"Nomes especiais: {', '.join(sorted(NOMES_PERMITIDOS))}"
            ),
            "caminho": caminho,
        }

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(conteudo, encoding="utf-8")
        return {
            "sucesso": True,
            "caminho": str(path),
            "bytes_escritos": len(conteudo.encode("utf-8")),
            "erro": None,
        }
    except PermissionError as e:
        return {"sucesso": False, "erro": f"Permissão negada: {e}", "caminho": caminho}
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro inesperado: {e}", "caminho": caminho}


def tool_salvar_relatorio(
    conteudo: str, nome_arquivo: str = "doubt_artifact_revisao.md", base_dir: Optional[str] = None
) -> dict:
    """Persiste um relatório de revisão em Markdown no disco.

    Use ao final de uma análise/revisão para deixar um artefato durável
    consumível por humanos ou por outros agentes (ex: reviewer salva o
    parecer técnico em verificacao_revisao.md). O nome do arquivo deve
    sempre terminar em .md.

    Args:
        conteudo: Texto Markdown completo do relatório.
        nome_arquivo: Nome do arquivo de saída. Default
            "doubt_artifact_revisao.md". Obrigatório terminar em .md.
        base_dir: Diretório base do agente (injetado pela factory).

    Returns:
        dict com chaves: `sucesso` (bool), `caminho` (str do path
        resolvido), `bytes_escritos` (int em sucesso), `erro` (str ou
        None). Em validação inválida ou I/O falho, `sucesso=False`.
    """
    try:
        dados = RelatorioSchema(conteudo=conteudo, nome_arquivo=nome_arquivo)
    except ValidationError as e:
        return {"sucesso": False, "erro": f"Parâmetros inválidos: {e}", "caminho": None}

    if base_dir is None:
        # Comportamento original: validação manual de segurança
        path = Path(dados.nome_arquivo)
        if path.is_absolute() or ".." in path.parts:
            return {
                "sucesso": False,
                "erro": "Caminho deve ser relativo e sem '..'.",
                "caminho": str(path),
            }
    else:
        try:
            path = _resolver_caminho(dados.nome_arquivo, base_dir)
        except ValueError as e:
            return {"sucesso": False, "erro": str(e), "caminho": dados.nome_arquivo}

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dados.conteudo, encoding="utf-8")
        return {
            "sucesso": True,
            "caminho": str(path),
            "bytes_escritos": len(dados.conteudo.encode("utf-8")),
            "erro": None,
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": f"Erro ao salvar relatório: {e}",
            "caminho": str(path),
        }


def tool_ler_arquivo(caminho: str, base_dir: Optional[str] = None) -> str:
    """Lê o conteúdo completo de um arquivo do disco como texto UTF-8.

    Use sempre que precisar do conteúdo atual de um arquivo antes de
    editá-lo, validar uma estrutura ou copiar trechos para outro local.
    Não use para arquivos binários (PDF, imagens) — esta capacidade lê
    como texto puro.

    Args:
        caminho: Caminho do arquivo. Relativo a base_dir se fornecido,
            senão ao CWD.
        base_dir: Diretório base do agente (injetado pela factory).

    Returns:
        str com o conteúdo do arquivo em UTF-8, ou string iniciada por
        "Erro:" descrevendo o problema (arquivo inexistente, path
        traversal, falha de leitura).
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
    caminho: str, trecho_antigo: str, trecho_novo: str, base_dir: Optional[str] = None
) -> str:
    """Substitui um trecho exato de um arquivo já existente por novo conteúdo.

    Use para editar arquivos preservando o restante intocado — refator
    cirúrgico, ajuste de assinatura, correção pontual. O 'trecho_antigo'
    DEVE ser uma cópia byte-a-byte do texto que está hoje no arquivo,
    incluindo indentação e quebras de linha; o casamento é exato, não
    fuzzy.

    Não use para criar arquivos novos (use a capacidade de criação de
    arquivo) nem para substituir conteúdo inteiro do arquivo.

    Args:
        caminho: Caminho do arquivo a editar. Relativo a base_dir se
            fornecido.
        trecho_antigo: Texto exato que está no arquivo hoje. Se não
            casar exatamente, a tool retorna erro sem alterar nada.
        trecho_novo: Texto que substituirá `trecho_antigo`.
        base_dir: Diretório base do agente (injetado pela factory).

    Returns:
        str com mensagem de sucesso indicando o arquivo alterado. Em
        caso de múltiplas ocorrências de `trecho_antigo`, apenas a
        PRIMEIRA é substituída — para substituir várias, chame a tool
        múltiplas vezes ou edite o trecho para ser único. Retorna
        string "Erro:" se: arquivo inexistente, trecho_antigo não
        encontrado, ou falha de I/O.
    """
    try:
        path = _resolver_caminho(caminho, base_dir)
    except ValueError as e:
        return f"Erro: {e}"

    try:
        if not path.is_file():
            return f"Erro: O arquivo '{caminho}' não existe. Use tool_criar_arquivo para criar arquivos novos."

        content = path.read_text(encoding="utf-8")

        if trecho_antigo not in content:
            return (
                f"Erro: 'trecho_antigo' não foi encontrado da maneira exata que você informou "
                f"no arquivo '{caminho}'. Lembre-se, tem que ser IDÊNTICO ao que foi retornado "
                f"por tool_ler_arquivo."
            )

        new_file_content = content.replace(trecho_antigo, trecho_novo, 1)
        path.write_text(new_file_content, encoding="utf-8")

        return f"Sucesso: O bloco de código foi substituído no arquivo '{caminho}'."
    except Exception as e:
        return f"Erro inesperado ao substituir trecho no arquivo '{caminho}': {str(e)}"
