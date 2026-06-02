import pytest
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))
from secure_fs import SecureFileSystemTool, ALLOWED_UPLOAD_EXTENSIONS


# ══════════════════════════════════════════════════════
# FIXTURE
# ══════════════════════════════════════════════════════

@pytest.fixture
def mock_workspace(tmp_path):
    """
    Arrange: Simula a estrutura do requisito da imagem (P4).
    Cria as pastas /src e /tests com seus respectivos arquivos.
    """
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("print('hello')", encoding="utf-8")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_qa.py").touch()

    return tmp_path


@pytest.fixture
def fs(mock_workspace):
    """Instância padrão da tool com workspace temporário."""
    return SecureFileSystemTool(base_workspace=mock_workspace)


# ══════════════════════════════════════════════════════
# list_directory — testes originais + novos
# ══════════════════════════════════════════════════════

class TestListDirectory:
    def test_navegacao_segura_dentro_do_workspace(self, fs):
        """Verifica se o agente consegue ver a pasta 'src' legitimamente."""
        itens = fs.list_directory("src")
        assert "main.py" in itens
        assert len(itens) == 1

    def test_protecao_anti_traversal_relativo(self, fs):
        """Bloqueia tentativas de escapar com '../'."""
        with pytest.raises(PermissionError, match="ACCESS_DENIED"):
            fs.list_directory("../")

    def test_protecao_anti_traversal_caminho_absoluto(self, fs):
        """Bloqueia caminho absoluto malicioso apontando para a raiz '/'."""
        with pytest.raises(PermissionError, match="ACCESS_DENIED"):
            fs.list_directory(str(Path("/").resolve()))

    def test_protecao_anti_symlink(self, fs, mock_workspace, tmp_path):
        """Bloqueia symlinks que apontam para fora do workspace."""
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        link = mock_workspace / "escape_link"
        link.symlink_to(outside_dir)

        with pytest.raises(PermissionError, match="ACCESS_DENIED"):
            fs.list_directory("escape_link")

    def test_diretorio_inexistente_lanca_erro(self, fs):
        with pytest.raises(FileNotFoundError):
            fs.list_directory("nao_existe")

    def test_arquivo_como_diretorio_lanca_erro(self, fs):
        with pytest.raises(NotADirectoryError):
            fs.list_directory("src/main.py")


# ══════════════════════════════════════════════════════
# read_file
# ══════════════════════════════════════════════════════

class TestReadFile:
    def test_leitura_texto_basica(self, fs):
        """Lê o conteúdo de um arquivo de texto corretamente."""
        conteudo = fs.read_file("src/main.py")
        assert "print('hello')" in conteudo

    def test_leitura_modo_binario(self, fs, mock_workspace):
        """Lê um arquivo em modo binário e retorna bytes."""
        (mock_workspace / "src" / "dados.bin").write_bytes(b"\x00\x01\x02")
        resultado = fs.read_file("src/dados.bin", mode="binary")
        assert isinstance(resultado, bytes)
        assert resultado == b"\x00\x01\x02"

    def test_modo_invalido_lanca_erro(self, fs):
        with pytest.raises(ValueError, match="Modo inválido"):
            fs.read_file("src/main.py", mode="stream")

    def test_arquivo_inexistente_lanca_erro(self, fs):
        with pytest.raises(FileNotFoundError):
            fs.read_file("src/fantasma.py")

    def test_protecao_tamanho_maximo(self, mock_workspace):
        """Bloqueia leitura de arquivo que excede o limite configurado."""
        fs_limitado = SecureFileSystemTool(
            base_workspace=mock_workspace, max_read_bytes=5
        )
        # main.py tem mais de 5 bytes
        with pytest.raises(ValueError, match="Arquivo muito grande"):
            fs_limitado.read_file("src/main.py")

    def test_protecao_anti_traversal(self, fs):
        with pytest.raises(PermissionError, match="ACCESS_DENIED"):
            fs.read_file("../secrets.txt")


# ══════════════════════════════════════════════════════
# write_file
# ══════════════════════════════════════════════════════

class TestWriteFile:
    def test_escrita_basica_texto(self, fs, mock_workspace):
        """Cria um novo arquivo de texto no workspace."""
        fs.write_file("src/output.txt", "resultado do agente")
        assert (mock_workspace / "src" / "output.txt").read_text() == "resultado do agente"

    def test_escrita_binaria(self, fs, mock_workspace):
        """Cria um arquivo binário no workspace."""
        fs.write_file("src/dados.bin", b"\xff\xfe")
        assert (mock_workspace / "src" / "dados.bin").read_bytes() == b"\xff\xfe"

    def test_overwrite_falso_bloqueia_sobrescrita(self, fs):
        """Não sobrescreve arquivo existente por padrão."""
        fs.write_file("src/novo.txt", "v1")
        with pytest.raises(FileExistsError):
            fs.write_file("src/novo.txt", "v2", overwrite=False)

    def test_overwrite_verdadeiro_permite_sobrescrita(self, fs, mock_workspace):
        """Com overwrite=True, substitui o conteúdo do arquivo."""
        fs.write_file("src/novo.txt", "v1")
        fs.write_file("src/novo.txt", "v2", overwrite=True)
        assert (mock_workspace / "src" / "novo.txt").read_text() == "v2"

    def test_cria_subdiretorios_automaticamente(self, fs, mock_workspace):
        """Cria diretórios intermediários se não existirem."""
        fs.write_file("nova_pasta/sub/arquivo.txt", "oi")
        assert (mock_workspace / "nova_pasta" / "sub" / "arquivo.txt").exists()

    def test_protecao_anti_traversal(self, fs):
        with pytest.raises(PermissionError, match="ACCESS_DENIED"):
            fs.write_file("../../exploit.txt", "pwned")


# ══════════════════════════════════════════════════════
# delete_file
# ══════════════════════════════════════════════════════

class TestDeleteFile:
    def test_deleta_arquivo_existente(self, fs, mock_workspace):
        """Remove um arquivo dentro do workspace corretamente."""
        arquivo = mock_workspace / "src" / "temp.txt"
        arquivo.write_text("temporario")
        fs.delete_file("src/temp.txt")
        assert not arquivo.exists()

    def test_arquivo_inexistente_lanca_erro(self, fs):
        with pytest.raises(FileNotFoundError):
            fs.delete_file("src/nao_existe.txt")

    def test_diretorio_lanca_erro(self, fs):
        with pytest.raises(IsADirectoryError):
            fs.delete_file("src")

    def test_protecao_anti_traversal(self, fs):
        with pytest.raises(PermissionError, match="ACCESS_DENIED"):
            fs.delete_file("../../importante.txt")


# ══════════════════════════════════════════════════════
# move_file
# ══════════════════════════════════════════════════════

class TestMoveFile:
    def test_move_basico(self, fs, mock_workspace):
        """Move um arquivo de uma pasta para outra dentro do workspace."""
        fs.move_file("src/main.py", "tests/main.py")
        assert not (mock_workspace / "src" / "main.py").exists()
        assert (mock_workspace / "tests" / "main.py").exists()

    def test_renomear_arquivo(self, fs, mock_workspace):
        """Renomeia um arquivo dentro da mesma pasta."""
        fs.move_file("src/main.py", "src/app.py")
        assert not (mock_workspace / "src" / "main.py").exists()
        assert (mock_workspace / "src" / "app.py").exists()

    def test_conteudo_preservado_apos_mover(self, fs, mock_workspace):
        """O conteúdo do arquivo não é alterado durante a movimentação."""
        conteudo = fs.read_file("src/main.py")
        fs.move_file("src/main.py", "tests/main.py")
        assert fs.read_file("tests/main.py") == conteudo

    def test_cria_subdiretorios_do_destino(self, fs, mock_workspace):
        """Cria diretórios intermediários do destino se não existirem."""
        fs.move_file("src/main.py", "nova_pasta/sub/main.py")
        assert (mock_workspace / "nova_pasta" / "sub" / "main.py").exists()

    def test_overwrite_falso_bloqueia_sobrescrita(self, fs):
        """Não sobrescreve arquivo existente no destino por padrão."""
        (fs.base_workspace / "tests" / "main.py").write_text("original")
        with pytest.raises(FileExistsError):
            fs.move_file("src/main.py", "tests/main.py", overwrite=False)

    def test_overwrite_verdadeiro_substitui_destino(self, fs, mock_workspace):
        """Com overwrite=True, substitui o arquivo no destino."""
        (mock_workspace / "tests" / "main.py").write_text("antigo")
        fs.move_file("src/main.py", "tests/main.py", overwrite=True)
        assert fs.read_file("tests/main.py") == "print('hello')"

    def test_origem_inexistente_lanca_erro(self, fs):
        with pytest.raises(FileNotFoundError):
            fs.move_file("src/fantasma.py", "tests/fantasma.py")

    def test_origem_diretorio_lanca_erro(self, fs):
        with pytest.raises(IsADirectoryError):
            fs.move_file("src", "tests/src")

    def test_retorna_caminho_relativo_do_destino(self, fs):
        """Retorna o caminho relativo ao workspace, não o absoluto."""
        resultado = fs.move_file("src/main.py", "tests/main.py")
        assert resultado == "tests/main.py"

    def test_protecao_anti_traversal_origem(self, fs):
        with pytest.raises(PermissionError, match="ACCESS_DENIED"):
            fs.move_file("../../secrets.txt", "src/secrets.txt")

    def test_protecao_anti_traversal_destino(self, fs):
        with pytest.raises(PermissionError, match="ACCESS_DENIED"):
            fs.move_file("src/main.py", "../../exploit.py")


# ══════════════════════════════════════════════════════
# upload_file
# ══════════════════════════════════════════════════════

class TestUploadFile:
    def test_upload_basico(self, fs, mock_workspace):
        """Salva um arquivo enviado pelo usuário na pasta uploads."""
        caminho = fs.upload_file("relatorio.pdf", b"%PDF-1.4 conteudo")
        assert caminho == "uploads/relatorio.pdf"
        assert (mock_workspace / "uploads" / "relatorio.pdf").exists()

    def test_upload_cria_pasta_uploads_automaticamente(self, mock_workspace):
        """A pasta uploads é criada automaticamente ao instanciar a tool."""
        fs_novo = SecureFileSystemTool(base_workspace=mock_workspace)
        assert (mock_workspace / "uploads").is_dir()

    def test_upload_extensao_nao_permitida(self, fs):
        """Bloqueia uploads de extensões fora da whitelist."""
        with pytest.raises(ValueError, match="Extensão"):
            fs.upload_file("virus.exe", b"MZ malware")

    def test_upload_tamanho_excedido(self, mock_workspace):
        """Bloqueia uploads maiores que o limite configurado."""
        fs_limitado = SecureFileSystemTool(
            base_workspace=mock_workspace, max_upload_bytes=10
        )
        with pytest.raises(ValueError, match="Arquivo muito grande"):
            fs_limitado.upload_file("grande.txt", b"x" * 11)

    def test_upload_sanitiza_nome_malicioso(self, fs, mock_workspace):
        """Remove separadores de path do nome do arquivo enviado."""
        # Ataque: tentar salvar fora da pasta de uploads via nome
        caminho = fs.upload_file("../../escape.txt", b"conteudo")
        # Deve ter sido sanitizado para só o nome base
        assert (mock_workspace / "uploads" / "escape.txt").exists()

    def test_upload_em_subdirectory_customizado(self, fs, mock_workspace):
        """Permite salvar em um subdiretório específico dentro do workspace."""
        caminho = fs.upload_file("foto.png", b"\x89PNG", subdirectory="imagens")
        assert caminho == "imagens/foto.png"
        assert (mock_workspace / "imagens" / "foto.png").exists()

    def test_upload_subdirectory_traversal_bloqueado(self, fs):
        """Bloqueia subdirectory que tenta escapar do workspace."""
        with pytest.raises(PermissionError, match="ACCESS_DENIED"):
            fs.upload_file("arquivo.txt", b"x", subdirectory="../fora")