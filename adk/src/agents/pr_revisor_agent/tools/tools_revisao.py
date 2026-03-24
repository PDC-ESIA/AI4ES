import logging
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, ValidationError
from google.adk.tools import FunctionTool

# -------------------------------------------------------------------
# SCHEMAS DO PYDANTIC (Validação de Entrada)
# -------------------------------------------------------------------
class RelatorioSchema(BaseModel):
    conteudo: str = Field(..., description="Conteúdo em Markdown do relatório de revisão")
    nome_arquivo: str = Field(default="doubt_artifact_revisao.md", description="Nome do arquivo de saída")

    @field_validator('nome_arquivo')
    def validar_extensao(cls, v):
        """Garante que o agente só crie relatórios no formato Markdown"""
        if not v.endswith('.md'):
            raise ValueError("O relatório de revisão DEVE obrigatoriamente ser um arquivo Markdown (.md)")
        return v

# -------------------------------------------------------------------
# FERRAMENTAS (TOOLS)
# -------------------------------------------------------------------
def tool_ler_diff(branch_alvo: str = "main") -> dict:
    """Ferramenta usada para extrair as diferenças de código (diff) via Git.
    
    Args:
        branch_alvo (str): A branch com a qual o código atual será comparado.
        
    Returns:
        dict: Contém o status da operação, o diff gerado e possíveis erros.
    """
    comando = ['git', 'diff', branch_alvo]
    
    resposta = subprocess.run(
        comando, 
        capture_output=True, 
        text=True,
        encoding="utf-8"
    )

    if resposta.returncode != 0:
        return {
            "sucesso": False,
            "erro": f"Falha no git diff: {resposta.stderr}",
            "diff": None
        }
    
    if not resposta.stdout.strip():
        return {
            "sucesso": False,
            "erro": f"Nenhuma alteração encontrada em relação à branch '{branch_alvo}'.",
            "diff": None
        }

    return {
        "sucesso": True,
        "erro": None,
        "diff": resposta.stdout
    }

def tool_salvar_relatorio(conteudo: str, nome_arquivo: str = "doubt_artifact_revisao.md") -> dict:
    """Ferramenta para salvar o veredito e o Doubt Artifact da revisão no disco.
    
    Args:
        conteudo (str): O texto do relatório gerado pelo agente.
        nome_arquivo (str): O nome do arquivo a ser salvo (padrão: doubt_artifact_revisao.md).
        
    Returns:
        dict: Contém status da operação, caminho absoluto do arquivo criado e erros.
    """
    
    try:
        dados_validados = RelatorioSchema(conteudo=conteudo, nome_arquivo=nome_arquivo)
    except ValidationError as e:
        return {
            "sucesso": False,
            "erro": f"Agente forneceu parâmetros inválidos: {e}",
            "caminho": None
        }

    path = Path(dados_validados.nome_arquivo)

    if path.is_absolute() or ".." in path.parts:
        return {
            "sucesso": False,
            "erro": "O caminho do arquivo deve ser relativo ao diretório atual e não pode subir níveis (..).",
            "caminho": str(path)
        }

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dados_validados.conteudo, encoding="utf-8")

        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(path.resolve()),
            "bytes_escritos": len(dados_validados.conteudo.encode("utf-8"))
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": f"Erro inesperado ao salvar o relatório de revisão: {e}",
            "caminho": str(path)
        }

# -------------------------------------------------------------------
# EXPORTANDO PARA O AGENTE ADK
# -------------------------------------------------------------------
tool_ler_diff_adk = FunctionTool(tool_ler_diff)
tool_salvar_relatorio_adk = FunctionTool(tool_salvar_relatorio)