import pytest
from pathlib import Path
from pydantic import ValidationError

# Supondo que o código das suas tools está em um arquivo chamado `filesystem_tools.py`
from shared.tools.filesystem import (
    RelatorioSchema, tool_criar_arquivo, tool_salvar_relatorio, 
    tool_acessar_workspace, _resolver_workspace, _validar_caminho_dentro_do_workspace
)

# --- Mock do ToolContext para os testes ---
class MockToolContext:
    def __init__(self):
        self.state = {}

@pytest.fixture
def tool_context():
    return MockToolContext()

@pytest.fixture
def workspace_temp(tmp_path):
    """Cria um workspace temporário e alguns arquivos mockados."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("secret")
    return tmp_path

# --- Testes do Schema ---

def test_relatorio_schema_extensao_valida():
    schema = RelatorioSchema(conteudo="# Teste", nome_arquivo="relatorio.md")
    assert schema.nome_arquivo == "relatorio.md"

def test_relatorio_schema_extensao_invalida():
    with pytest.raises(ValidationError):
        RelatorioSchema(conteudo="# Teste", nome_arquivo="relatorio.txt")

# --- Testes das Funções Internas de Segurança ---

def test_resolver_workspace(tool_context, workspace_temp):
    assert _resolver_workspace(tool_context) is None
    
    tool_context.state["workspace_path"] = str(workspace_temp)
    resolvido = _resolver_workspace(tool_context)
    assert resolvido == workspace_temp.resolve()

def test_validar_caminho_dentro_do_workspace(workspace_temp):
    # Caminho válido
    destino, erro = _validar_caminho_dentro_do_workspace("src/novo.py", workspace_temp)
    assert erro is None
    assert destino == (workspace_temp / "src/novo.py").resolve()

    # Tentativa de Path Traversal (sair do workspace)
    destino, erro = _validar_caminho_dentro_do_workspace("../fora.py", workspace_temp)
    assert erro is not None
    assert "fora do workspace" in erro

    # Tentativa de escrever em diretório proibido
    destino, erro = _validar_caminho_dentro_do_workspace(".git/hack.py", workspace_temp)
    assert erro is not None
    assert "diretório protegido" in erro

# --- Testes da Tool: Acessar Workspace ---

def test_tool_acessar_workspace_sucesso(tool_context, workspace_temp):
    resultado = tool_acessar_workspace(str(workspace_temp), tool_context)
    
    assert resultado["status"] == "ok"
    assert tool_context.state["workspace_path"] == str(workspace_temp.resolve())
    # Deve encontrar main.py, mas NÃO deve listar o config dentro de .git
    assert any("main.py" in f for f in resultado["arquivos"])
    assert not any(".git" in f for f in resultado["arquivos"])

def test_tool_acessar_workspace_nao_encontrado(tool_context):
    resultado = tool_acessar_workspace("/caminho/fake/que/nao/existe", tool_context)
    assert resultado["status"] == "erro"
    assert "não encontrado" in resultado["mensagem"]

# --- Testes da Tool: Criar Arquivo ---

def test_tool_criar_arquivo_sucesso(tool_context, workspace_temp):
    tool_context.state["workspace_path"] = str(workspace_temp)
    
    resultado = tool_criar_arquivo("novo_script.py", "print('teste')", tool_context)
    
    assert resultado["sucesso"] is True
    assert resultado["erro"] is None
    assert (workspace_temp / "novo_script.py").exists()
    assert (workspace_temp / "novo_script.py").read_text(encoding="utf-8") == "print('teste')"

def test_tool_criar_arquivo_extensao_proibida(tool_context, workspace_temp):
    tool_context.state["workspace_path"] = str(workspace_temp)
    
    resultado = tool_criar_arquivo("script.exe", "virus", tool_context)
    assert resultado["sucesso"] is False
    assert "Extensão '.exe' não permitida" in resultado["erro"]
    assert not (workspace_temp / "script.exe").exists()

def test_tool_criar_arquivo_sem_workspace_inicializado(tool_context):
    # Sem setar o state["workspace_path"]
    resultado = tool_criar_arquivo("teste.py", "print('a')", tool_context)
    assert resultado["sucesso"] is False
    assert "Workspace não inicializado" in resultado["erro"]

# --- Testes da Tool: Salvar Relatório ---

def test_tool_salvar_relatorio_sucesso(tool_context, workspace_temp):
    tool_context.state["workspace_path"] = str(workspace_temp)
    
    resultado = tool_salvar_relatorio("# Título", tool_context, "meu_relatorio.md")
    
    assert resultado["sucesso"] is True
    assert resultado["erro"] is None
    assert (workspace_temp / "meu_relatorio.md").exists()

def test_tool_salvar_relatorio_extensao_invalida(tool_context, workspace_temp):
    tool_context.state["workspace_path"] = str(workspace_temp)
    
    # Tentando salvar como .txt (schema exige .md)
    resultado = tool_salvar_relatorio("texto", tool_context, "relatorio.txt")
    
    assert resultado["sucesso"] is False
    assert "Parâmetros inválidos" in resultado["erro"]