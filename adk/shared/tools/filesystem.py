"""Ferramentas de filesystem compartilhadas entre agentes."""

import os
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, field_validator

EXTENSOES_PERMITIDAS = {
    ".py", ".js", ".ts", ".html", ".css", ".json",
    ".md", ".txt", ".yaml", ".yml", ".toml", ".env.example",
}

DIRETORIOS_PROIBIDOS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".env",
}

_ERRO_AGENT_WORKSPACE_AUSENTE = (
    "AGENT_WORKSPACE não está definida nas variáveis de ambiente. "
    "Peça ao usuário qual pasta deve receber os arquivos gerados (caminho absoluto recomendado) "
    "e oriente-o a definir a variável AGENT_WORKSPACE com esse caminho no .env (ou ambiente) "
    "e reiniciar o servidor antes de tentar de novo."
)


def _workspace_root_resolved() -> tuple[Path | None, str | None]:
    """Retorna (raiz, None) ou (None, mensagem de erro) se ``AGENT_WORKSPACE`` estiver ausente."""
    raw = os.environ.get("AGENT_WORKSPACE", "").strip()
    if not raw:
        return None, _ERRO_AGENT_WORKSPACE_AUSENTE
    p = Path(raw)
    root = p.resolve() if p.is_absolute() else (Path.cwd() / p).resolve()
    return root, None


def _resolve_safe_under_workspace(rel: str) -> tuple[Path | None, str | None]:
    """Resolve ``rel`` dentro do workspace; retorna (path, erro)."""
    root, werr = _workspace_root_resolved()
    if werr:
        return None, werr

    path = Path(rel)
    if path.is_absolute() or ".." in path.parts:
        return None, "Caminho deve ser relativo ao workspace, sem '..'."
    full = (root / path).resolve()
    try:
        full.relative_to(root)
    except ValueError:
        return None, "Caminho fora do workspace."
    return full, None


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
        caminho (str): Caminho relativo ao workspace (variável de ambiente obrigatória ``AGENT_WORKSPACE``).
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
 
    caminho_limpo = caminho.strip()
    partes_rel = set(Path(caminho_limpo).parts[:-1])
    bloqueados = partes_rel & DIRETORIOS_PROIBIDOS
    if bloqueados:
        return {
            "sucesso": False,
            "erro": f"Escrita não permitida em diretório protegido: {bloqueados}",
            "caminho": caminho
        }

    path, err = _resolve_safe_under_workspace(caminho_limpo)
    if err:
        return {"sucesso": False, "erro": err, "caminho": caminho}
 
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

    path, err = _resolve_safe_under_workspace(dados.nome_arquivo)
    if err:
        return {"sucesso": False, "erro": err, "caminho": dados.nome_arquivo}

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dados.conteudo, encoding="utf-8")
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(path),
            "bytes_escritos": len(dados.conteudo.encode("utf-8")),
        }
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro ao salvar relatório: {e}", "caminho": str(path)}
