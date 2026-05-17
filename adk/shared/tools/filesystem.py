"""Ferramentas de filesystem compartilhadas entre agentes."""

import re
from pathlib import Path

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


def _resolver_caminho(caminho: str, base_dir: str | None = None) -> Path:
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


def tool_criar_arquivo(caminho: str, conteudo: str, base_dir: str | None = None) -> dict:
    """Cria/sobrescreve arquivo no disco com o conteúdo fornecido.

    Use esta ferramenta SEMPRE que precisar escrever um arquivo completo do zero.

    Possui validações de segurança:
    - Só permite extensões conhecidas e seguras
    - Impede escrita em diretórios protegidos (.git, .venv, etc.)
    - Cria diretórios intermediários automaticamente se necessário

    Args:
        caminho: Caminho do arquivo (relativo a base_dir se fornecido, ou ao CWD).
        conteudo: Conteúdo a escrever.
        base_dir: Diretório base do agente (injetado pela factory quando aplicável).

    Returns:
        dict com sucesso, caminho, bytes_escritos, erro.
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

    if path.suffix not in EXTENSOES_PERMITIDAS:
        return {
            "sucesso": False,
            "erro": (
                f"Extensão '{path.suffix}' não permitida. "
                f"Permitidas: {', '.join(sorted(EXTENSOES_PERMITIDAS))}"
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
    conteudo: str, nome_arquivo: str = "doubt_artifact_revisao.md", base_dir: str | None = None
) -> dict:
    """Salva relatório de revisão em Markdown no disco.

    Args:
        conteudo: Texto do relatório.
        nome_arquivo: Nome do arquivo (padrão: doubt_artifact_revisao.md).
        base_dir: Diretório base do agente (injetado pela factory quando aplicável).

    Returns:
        dict com sucesso, caminho, bytes_escritos e erro.
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


def tool_ler_arquivo(caminho: str, base_dir: str | None = None) -> str:
    """Lê o conteúdo completo de um arquivo no disco.

    Args:
        caminho: Caminho do arquivo (relativo a base_dir se fornecido, ou ao CWD).
        base_dir: Diretório base do agente (injetado pela factory quando aplicável).

    Returns:
        str: Conteúdo do arquivo, ou mensagem de erro.
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
    caminho: str, trecho_antigo: str, trecho_novo: str, base_dir: str | None = None
) -> str:
    """Use esta ferramenta para editar arquivos JÁ EXISTENTES, evitando reescrever o arquivo inteiro.
    Substitui um trecho de código existente (trecho_antigo) por um novo trecho (trecho_novo) em um arquivo.
    Regra CRÍTICA: O 'trecho_antigo' deve ser uma cópia EXATA do trecho atual do arquivo,
    incluindo qualquer espaço, indentação e quebra de linha.

    Args:
        caminho: Caminho do arquivo (relativo a base_dir se fornecido, ou ao CWD).
        trecho_antigo: Trecho exato a ser substituído.
        trecho_novo: Novo trecho.
        base_dir: Diretório base do agente (injetado pela factory quando aplicável).

    Returns:
        str: Mensagem de sucesso ou erro.
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


def tool_salvar_artefato_requisito(tipo: str, id_req: str, conteudo_md: str) -> str:
    """Salva um artefato de requisito (HU, RF, RNF, RN, Glossario).

    Args:
        tipo: Tipo do artefato (HU, RF, RNF, RN, Glossario)
        id_req: Identificador único do requisito (ex: HU-001, RF-002)
        conteudo_md: Conteúdo do artefato em formato Markdown
    """
    mapa_pastas = {
        "HU": "docs/Time_1_Requisitos/HUs",
        "RF": "docs/Time_1_Requisitos/RFs",
        "RNF": "docs/Time_1_Requisitos/RNFs",
        "RN": "docs/Time_1_Requisitos/RNs",
        "GLOSSARIO": "docs/Time_1_Requisitos",
    }

    tipo_normalizado = (tipo or "").strip().upper()
    id_req_normalizado = (id_req or "").strip()
    pasta_base = mapa_pastas.get(tipo_normalizado, "docs/Time_1_Requisitos/Outros")

    try:
        if tipo_normalizado != "GLOSSARIO":
            if not ID_REQ_PATTERN.fullmatch(id_req_normalizado):
                return "ERRO ao salvar artefato: id_req inválido. Use o padrão AAAA-999."

        nome_arquivo = f"{id_req_normalizado}.md" if tipo_normalizado != "GLOSSARIO" else "Glossario.md"

        pasta_base_path = Path(pasta_base).resolve()
        pasta_base_path.mkdir(parents=True, exist_ok=True)
        caminho_completo = (pasta_base_path / nome_arquivo).resolve()

        if (
            caminho_completo.parent != pasta_base_path
            and pasta_base_path not in caminho_completo.parents
        ):
            return "ERRO ao salvar artefato: caminho de saída inválido."

        caminho_completo.write_text(conteudo_md, encoding="utf-8")

        return f"SUCESSO: {tipo} {id_req} salvo em {caminho_completo}"
    except Exception as e:
        return f"ERRO ao salvar artefato: {str(e)}"


def tool_ler_workspace(caminho: str, base_dir: str | None = None) -> str:
    """Lê o conteúdo de um arquivo do workspace global (read-only cross-workspace).

    Diferente de tool_ler_arquivo (escopo do agente), permite ler arquivos de
    qualquer subpasta do workspace centralizado — útil para o reviewer/qa
    consultarem outputs de outros agentes.

    Args:
        caminho: Caminho relativo à raiz do workspace (ex: 'coder/main.py').
        base_dir: Raiz do workspace (injetada pela factory como workspace_root).

    Returns:
        Conteúdo do arquivo ou mensagem de erro.
    """
    if base_dir is None:
        return "Erro: tool_ler_workspace requer base_dir (raiz do workspace)."

    try:
        path = _resolver_caminho(caminho, base_dir)
    except ValueError as e:
        return f"Erro: {e}"

    if not path.is_file():
        return f"Erro: arquivo '{caminho}' não existe em {base_dir}."

    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Erro ao ler '{caminho}': {e}"


def tool_listar_workspace(caminho: str = ".", base_dir: str | None = None) -> str | list[str]:
    """Lista o conteúdo de um diretório do workspace global.

    Args:
        caminho: Caminho relativo à raiz do workspace. Default: "." (raiz).
        base_dir: Raiz do workspace (injetada pela factory).

    Returns:
        Lista de nomes (arquivos+diretórios) ou string de erro.
    """
    if base_dir is None:
        return "Erro: tool_listar_workspace requer base_dir (raiz do workspace)."

    try:
        path = _resolver_caminho(caminho, base_dir)
    except ValueError as e:
        return f"Erro: {e}"

    if not path.is_dir():
        return f"Erro: diretório '{caminho}' não existe em {base_dir}."

    try:
        return sorted(p.name for p in path.iterdir())
    except Exception as e:
        return f"Erro ao listar '{caminho}': {e}"
