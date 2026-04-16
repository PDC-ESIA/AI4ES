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
 


def tool_salvar_relatorio(conteudo: str, nome_arquivo: str = "doubt_artifact_revisao.md") -> dict:
    """Salva relatório de revisão em Markdown no disco.

    Args:
        conteudo: Texto do relatório.
        nome_arquivo: Nome do arquivo (padrão: doubt_artifact_revisao.md).

    Returns:
        dict com sucesso, caminho, bytes_escritos e erro.
    """
    try:
        dados = RelatorioSchema(conteudo=conteudo, nome_arquivo=nome_arquivo)
    except ValidationError as e:
        return {"sucesso": False, "erro": f"Parâmetros inválidos: {e}", "caminho": None}

    path = Path(dados.nome_arquivo)

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
