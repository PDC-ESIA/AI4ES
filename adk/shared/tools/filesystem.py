"""Ferramentas de filesystem compartilhadas entre agentes."""

from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, field_validator
from google.adk.tools import ToolContext

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


def tool_criar_arquivo(caminho: str, conteudo: str, tool_context: ToolContext) -> dict:
    """Ferramenta para criar ou sobrescrever um arquivo no disco com o conteúdo fornecido.
       Use esta ferramenta SEMPRE que precisar escrever um arquivo completo do zero. 
>>>>>>> c5d7f2d (feat(code): #240 cria a tool necessária para acessar o workspace)
 
    Possui validações de segurança:
    - Só permite extensões conhecidas e seguras
    - Impede escrita em diretórios protegidos (.git, .venv, etc.)
    - Cria diretórios intermediários automaticamente se necessário
 
    Args:
        caminho (str): Caminho relativo ao diretório de trabalho atual 
        conteudo (str): Conteúdo completo a ser escrito no arquivo
        tool_context (ToolContext): Contexto de comunicação das tools
 
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
 
    if path.suffix not in EXTENSOES_PERMITIDAS:
        return {
            "sucesso": False,
            "erro": (
                f"Extensão '{path.suffix}' não permitida. "
                f"Permitidas: {', '.join(sorted(EXTENSOES_PERMITIDAS))}"
            ),
            "caminho": caminho
        }
    
    workspace = _resolver_workspace(tool_context)
    if workspace is None:
        return {"sucesso": False, "erro": "Workspace não inicializado. Chame tool_acessar_workspace primeiro.", "caminho": None}
 
    destino, erro = _validar_caminho_dentro_do_workspace(caminho, workspace)
    if erro:
        return {"sucesso": False, "erro": erro, "caminho": caminho}

    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(conteudo, encoding="utf-8")
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(destino),
            "bytes_escritos": len(conteudo.encode("utf-8")),
        }
    except PermissionError as e:
        return {
            "sucesso": False,
            "erro": f"Permissão negada: {e}",
            "caminho": str(destino)
        }
    except Exception as e:
        return {
            "sucesso": False, 
            "erro": f"Erro ao salvar arquivo: {e}", 
            "caminho": str(destino)
        } 


def tool_salvar_relatorio(conteudo: str, tool_context: ToolContext, nome_arquivo: str = "doubt_artifact_revisao.md") -> dict:
    """Salva relatório de revisão em Markdown no disco.

    Args:
        conteudo: Texto do relatório.
        tool_context: Contexto ADK da sessão.
        nome_arquivo: Nome do arquivo (padrão: doubt_artifact_revisao.md).

    Returns:
        dict com sucesso, caminho, bytes_escritos e erro.
    """
    try:
        dados = RelatorioSchema(conteudo=conteudo, nome_arquivo=nome_arquivo)
    except ValidationError as e:
        return {"sucesso": False, "erro": f"Parâmetros inválidos: {e}", "caminho": None}

    workspace = _resolver_workspace(tool_context)
    if workspace is None:
        return {
            "sucesso": False,
            "erro": "Workspace não inicializado. Chame tool_acessar_workspace primeiro.",
            "caminho": None,
        }
        
    destino, erro = _validar_caminho_dentro_do_workspace(dados.nome_arquivo, workspace)
    if erro:
        return {"sucesso": False, "erro": erro, "caminho": dados.nome_arquivo}

    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(dados.conteudo, encoding="utf-8")
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(destino.resolve()),
            "bytes_escritos": len(dados.conteudo.encode("utf-8")),
        }
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro ao salvar relatório: {e}", "caminho": str(destino)}



def tool_ler_arquivo(caminho: str) -> str:
    """Lê o conteúdo de um arquivo existente no disco.
    Use esta ferramenta para ler e analisar códigos ANTES de modificá-los ou corrigi-los.
    """
    try:
        path = Path(caminho)
        if not path.is_file():
            return f"Erro: O arquivo '{caminho}' não existe ou não é um arquivo válido."
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Erro inesperado ao ler o arquivo '{caminho}': {str(e)}"

def tool_substituir_trecho(caminho: str, trecho_antigo: str, trecho_novo: str) -> str:
    """ Use esta ferramenta para editar arquivos JÁ EXISTENTES, evitando reescrever o arquivo inteiro. 
    Substitui um trecho de código existente (trecho_antigo) por um novo trecho (trecho_novo) em um arquivo.
    Regra CRÍTICA: O 'trecho_antigo' deve ser uma cópia EXATA do trecho atual do arquivo,
    incluindo qualquer espaço, indentação e quebra de linha.
    """
    try:
        path = Path(caminho)
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

def _resolver_workspace(tool_context: ToolContext) -> Path | None:
    raw = tool_context.state.get("workspace_path")
    if not raw:
        return None
    return Path(raw).resolve()
 
def _validar_caminho_dentro_do_workspace(caminho: str, workspace: Path) -> tuple[Path, str | None]:

    destino = (workspace / caminho).resolve()

    try:
        destino.relative_to(workspace)  
    except ValueError:
        return destino, f"Caminho fora do workspace: '{caminho}'"
    
    partes = set(destino.relative_to(workspace).parts)
    bloqueados = partes & DIRETORIOS_PROIBIDOS
    
    if bloqueados:
        return destino, f"Escrita não permitida em diretório protegido: {bloqueados}"
    return destino, None

def tool_acessar_workspace(path: str, tool_context: ToolContext) -> dict:
    """Valida e registra o diretório de trabalho dos agentes na sessão.

    Deve ser chamada pelo orquestrador antes de qualquer outra tool de filesystem.
    Persiste o path resolvido em tool_context.state['workspace_path'] para que
    tool_criar_arquivo e tool_salvar_relatorio operem sempre dentro desse diretório.

    Args:
        path: Caminho absoluto ou relativo ao diretório de trabalho.
        tool_context: Contexto ADK da sessão.

    Returns:
        dict com status, workspace resolvido, total e lista de arquivos.
    """
    workspace = Path(path).resolve()

    workspace.mkdir(parents=True, exist_ok=True)

    if not workspace.is_dir():
        return {
            "status": "erro", 
            "mensagem": f"Path não é um diretório: {workspace}"}

    tool_context.state["workspace_path"] = str(workspace)

    arquivos = [
        str(p.relative_to(workspace))
        for p in workspace.rglob("*")
        if p.is_file()
        and not any(part in DIRETORIOS_PROIBIDOS for part in p.parts)
    ]

    return {
        "status": "ok",
        "workspace": str(workspace),
        "total_arquivos": len(arquivos),
        "arquivos": arquivos[:50],
    }
