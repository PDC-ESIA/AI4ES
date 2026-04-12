"""
test_tool_criar_arquivo.py
==========================
Testes unitários para a tool_criar_arquivo.
 
Execute com:
    pytest test_tool_criar_arquivo.py -v
"""
 
import sys
import types
from pathlib import Path
 
import pytest
 
sys.path.insert(0, str(Path(__file__).parent))
from shared.tools.filesystem import tool_criar_arquivo
 
 
# ===========================================================================
# Fixtures
# ===========================================================================
 
@pytest.fixture
def diretorio(tmp_path, monkeypatch):
    """CWD + AGENT_WORKSPACE apontando para o mesmo diretório temporário."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENT_WORKSPACE", str(tmp_path))
    return tmp_path
 
 
# ===========================================================================
# Testes: fluxo feliz
# ===========================================================================
 
class TestCriarArquivoSucesso:
 
    def test_cria_arquivo_python(self, diretorio):
        """Cria um arquivo .py com conteúdo correto."""
        result = tool_criar_arquivo("modulo.py", "def hello(): pass\n")
        assert result["sucesso"] is True
        assert Path("modulo.py").read_text() == "def hello(): pass\n"
 
    def test_cria_arquivo_markdown(self, diretorio):
        """Cria um arquivo .md."""
        result = tool_criar_arquivo("README.md", "# Título\n")
        assert result["sucesso"] is True
        assert Path("README.md").exists()
 
    def test_cria_arquivo_json(self, diretorio):
        """Cria um arquivo .json."""
        conteudo = '{"chave": "valor"}'
        result = tool_criar_arquivo("config.json", conteudo)
        assert result["sucesso"] is True
        assert Path("config.json").read_text() == conteudo
 
    def test_cria_subdiretorio_automaticamente(self, diretorio):
        """Cria diretórios intermediários se não existirem."""
        result = tool_criar_arquivo("src/utils/helpers.py", "# helpers\n")
        assert result["sucesso"] is True
        assert Path("src/utils/helpers.py").exists()
 
    def test_retorna_caminho_absoluto(self, diretorio):
        """O campo 'caminho' no retorno deve ser o path absoluto."""
        result = tool_criar_arquivo("app.py", "pass\n")
        assert result["sucesso"] is True
        assert Path(result["caminho"]).is_absolute()
 
    def test_retorna_bytes_escritos(self, diretorio):
        """O campo 'bytes_escritos' deve refletir o tamanho do conteúdo."""
        conteudo = "print('olá')\n"
        result = tool_criar_arquivo("script.py", conteudo)
        assert result["sucesso"] is True
        assert result["bytes_escritos"] == len(conteudo.encode("utf-8"))
 
    def test_sobrescreve_arquivo_existente(self, diretorio):
        """Sobrescreve arquivo já existente com novo conteúdo."""
        tool_criar_arquivo("arquivo.py", "versão 1\n")
        result = tool_criar_arquivo("arquivo.py", "versão 2\n")
        assert result["sucesso"] is True
        assert Path("arquivo.py").read_text() == "versão 2\n"
 
    def test_cria_arquivo_vazio(self, diretorio):
        """Permite criar arquivo com conteúdo vazio."""
        result = tool_criar_arquivo("vazio.py", "")
        assert result["sucesso"] is True
        assert Path("vazio.py").read_text() == ""
 
    def test_retorna_chaves_corretas_sucesso(self, diretorio):
        """Verifica contrato do dict em caso de sucesso."""
        result = tool_criar_arquivo("x.py", "pass\n")
        assert {"sucesso", "caminho", "bytes_escritos", "erro"}.issubset(result)
        assert result["erro"] is None
 
 
# ===========================================================================
# Testes: validações de segurança
# ===========================================================================
 
class TestCriarArquivoSeguranca:
 
    def test_extensao_nao_permitida_falha(self, diretorio):
        """Extensão fora da whitelist deve ser rejeitada."""
        result = tool_criar_arquivo("script.sh", "rm -rf /\n")
        assert result["sucesso"] is False
        assert "Extensão" in result["erro"]
 
    def test_extensao_exe_bloqueada(self, diretorio):
        """Arquivos executáveis devem ser bloqueados."""
        result = tool_criar_arquivo("malware.exe", "conteudo")
        assert result["sucesso"] is False
 
    def test_diretorio_git_bloqueado(self, diretorio):
        """Escrita dentro de .git deve ser bloqueada."""
        result = tool_criar_arquivo(".git/config", "conteudo malicioso")
        assert result["sucesso"] is False
        assert "protegido" in result["erro"]
 
    def test_diretorio_venv_bloqueado(self, diretorio):
        """Escrita dentro de .venv deve ser bloqueada."""
        result = tool_criar_arquivo(".venv/lib/hack.py", "pass")
        assert result["sucesso"] is False
 
    def test_diretorio_node_modules_bloqueado(self, diretorio):
        """Escrita dentro de node_modules deve ser bloqueada."""
        result = tool_criar_arquivo("node_modules/pkg/index.js", "")
        assert result["sucesso"] is False
 
    def test_caminho_vazio_falha(self, diretorio):
        """Caminho vazio deve ser rejeitado."""
        result = tool_criar_arquivo("", "conteudo")
        assert result["sucesso"] is False
        assert "vazio" in result["erro"].lower()
 
    def test_caminho_so_espacos_falha(self, diretorio):
        """Caminho só com espaços deve ser rejeitado."""
        result = tool_criar_arquivo("   ", "conteudo")
        assert result["sucesso"] is False
 
    def test_retorna_chaves_corretas_falha(self, diretorio):
        """Verifica contrato do dict em caso de falha."""
        result = tool_criar_arquivo("script.sh", "conteudo")
        assert {"sucesso", "erro", "caminho"}.issubset(result)
        assert result["sucesso"] is False

    def test_path_com_ponto_ponto_rejeitado(self, diretorio):
        result = tool_criar_arquivo("../fora.py", "x")
        assert result["sucesso"] is False
        assert ".." in result["erro"] or "workspace" in result["erro"].lower()


class TestWorkspaceEnv:
    def test_sem_agent_workspace_falha(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("AGENT_WORKSPACE", raising=False)
        result = tool_criar_arquivo("x.py", "pass\n")
        assert result["sucesso"] is False
        assert "AGENT_WORKSPACE" in result["erro"]

    def test_agent_workspace_redireciona_gravacao(self, tmp_path, monkeypatch):
        ws = tmp_path / "out"
        ws.mkdir()
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("AGENT_WORKSPACE", str(ws))
        result = tool_criar_arquivo("rel/a.py", "pass\n")
        assert result["sucesso"] is True
        assert (ws / "rel" / "a.py").read_text() == "pass\n"
        assert Path(result["caminho"]) == (ws / "rel" / "a.py").resolve()
 