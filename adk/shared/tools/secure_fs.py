#Ferramenta criada para navegacao segura e protecao anti-transversal

import os
import shutil
from pathlib import Path

# Tamanho máximo padrão para leitura de arquivos texto: 10 MB
DEFAULT_MAX_READ_BYTES = 10 * 1024 * 1024

# Tamanho máximo padrão para upload de arquivos: 50 MB
DEFAULT_MAX_UPLOAD_BYTES = 50 * 1024 * 1024

# Extensões permitidas para upload (whitelist)
ALLOWED_UPLOAD_EXTENSIONS = {
    ".txt", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
    ".md", ".csv", ".html", ".css", ".pdf", ".png", ".jpg",
    ".jpeg", ".gif", ".webp", ".zip",
}


class SecureFileSystemTool:
    def __init__(
        self,
        base_workspace: str | Path,
        max_read_bytes: int = DEFAULT_MAX_READ_BYTES,
        max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
    ):
        """
        Inicializa a ferramenta definindo a 'jaula' de segurança.
        Nenhum agente poderá acessar arquivos fora de 'base_workspace'.

        Args:
            base_workspace:    Diretório raiz do workspace do agente.
            max_read_bytes:    Limite de bytes para leitura de texto (padrão: 10 MB).
            max_upload_bytes:  Limite de bytes para upload de arquivos (padrão: 50 MB).
        """
        self.base_workspace = Path(base_workspace).resolve()
        self.max_read_bytes = max_read_bytes
        self.max_upload_bytes = max_upload_bytes

        # Garante que a pasta de uploads existe dentro do workspace
        self.uploads_dir = self.base_workspace / "uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────────
    # MÉTODO INTERNO: validação central de caminhos
    # ──────────────────────────────────────────────

    def _validate_path(self, target_path: str) -> Path:
        """
        Resolve e valida um caminho, garantindo que:
          1. Nenhum componente do caminho é um symlink (anti-symlink escape).
          2. Está dentro do workspace (anti-traversal).

        A checagem de symlink é feita ANTES do resolve(), percorrendo cada
        componente do caminho ainda não-resolvido. Isso garante que um link
        simbólico dentro do workspace apontando para fora seja detectado
        mesmo que, após o resolve(), o destino final ainda estivesse dentro
        do workspace por coincidência.

        Returns:
            Path absoluto e validado.

        Raises:
            PermissionError: Se o caminho violar qualquer proteção.
        """
        # 1. PROTEÇÃO ANTI-SYMLINK
        #    Percorre cada parte do caminho não-resolvido e rejeita symlinks.
        raw_path = self.base_workspace / target_path
        check = self.base_workspace
        for part in Path(target_path).parts:
            check = check / part
            if check.is_symlink():
                raise PermissionError(
                    f"ACCESS_DENIED: Symlinks não são permitidos: '{target_path}'."
                )

        # 2. Resolve o caminho agora que sabemos que não há symlinks
        requested_path = raw_path.resolve()

        # 3. PROTEÇÃO ANTI-TRAVERSAL
        if not requested_path.is_relative_to(self.base_workspace):
            raise PermissionError(
                f"ACCESS_DENIED: Tentativa de Path Traversal bloqueada para '{target_path}'."
            )

        return requested_path

    # ──────────────────────────────────────────────
    # list_directory
    # ──────────────────────────────────────────────

    def list_directory(self, target_path: str = ".") -> list[str]:
        """
        Lista os arquivos de um diretório de forma segura.
        Bloqueia Path Traversal e symlinks.

        Args:
            target_path: Caminho relativo ao workspace (padrão: raiz do workspace).

        Returns:
            Lista de nomes dos itens no diretório.
        """
        requested_path = self._validate_path(target_path)

        if not requested_path.exists():
            raise FileNotFoundError(f"Caminho não encontrado: '{target_path}'.")

        if not requested_path.is_dir():
            raise NotADirectoryError(f"O alvo não é um diretório: '{target_path}'.")

        return [item.name for item in requested_path.iterdir()]

    # ──────────────────────────────────────────────
    # read_file
    # ──────────────────────────────────────────────

    def read_file(self, target_path: str, mode: str = "text") -> str | bytes:
        """
        Lê o conteúdo de um arquivo local de forma segura.

        Args:
            target_path: Caminho relativo ao workspace.
            mode:        'text' para UTF-8 (padrão) ou 'binary' para bytes brutos.

        Returns:
            Conteúdo do arquivo como str (text) ou bytes (binary).

        Raises:
            ValueError:      Se o arquivo exceder o limite de tamanho ou o modo for inválido.
            FileNotFoundError: Se o arquivo não existir.
            PermissionError: Se o caminho violar as proteções de segurança.
        """
        if mode not in ("text", "binary"):
            raise ValueError(f"Modo inválido: '{mode}'. Use 'text' ou 'binary'.")

        requested_path = self._validate_path(target_path)

        if not requested_path.exists() or not requested_path.is_file():
            raise FileNotFoundError(
                f"Arquivo não encontrado ou é um diretório: '{target_path}'."
            )

        # PROTEÇÃO CONTRA ARQUIVOS GIGANTES
        file_size = requested_path.stat().st_size
        if file_size > self.max_read_bytes:
            raise ValueError(
                f"Arquivo muito grande: {file_size} bytes "
                f"(limite: {self.max_read_bytes} bytes)."
            )

        if mode == "binary":
            with open(requested_path, "rb") as f:
                return f.read()

        with open(requested_path, "r", encoding="utf-8") as f:
            return f.read()

    # ──────────────────────────────────────────────
    # write_file
    # ──────────────────────────────────────────────

    def write_file(
        self,
        target_path: str,
        content: str | bytes,
        overwrite: bool = False,
    ) -> str:
        """
        Escreve conteúdo em um arquivo dentro do workspace de forma segura.

        Args:
            target_path: Caminho relativo ao workspace.
            content:     Conteúdo a escrever (str para texto, bytes para binário).
            overwrite:   Se False (padrão), lança erro caso o arquivo já exista.

        Returns:
            Caminho absoluto do arquivo criado/atualizado.

        Raises:
            FileExistsError: Se o arquivo já existir e overwrite=False.
            PermissionError: Se o caminho violar as proteções de segurança.
        """
        requested_path = self._validate_path(target_path)

        if requested_path.exists() and not overwrite:
            raise FileExistsError(
                f"Arquivo já existe: '{target_path}'. "
                "Use overwrite=True para substituir."
            )

        # Cria os diretórios intermediários se necessário
        requested_path.parent.mkdir(parents=True, exist_ok=True)

        mode = "wb" if isinstance(content, bytes) else "w"
        encoding = None if isinstance(content, bytes) else "utf-8"

        with open(requested_path, mode, encoding=encoding) as f:
            f.write(content)

        return str(requested_path)

    # ──────────────────────────────────────────────
    # delete_file
    # ──────────────────────────────────────────────

    def delete_file(self, target_path: str) -> str:
        """
        Remove um arquivo do workspace de forma segura.

        Returns:
            Mensagem de confirmação.
        """
        requested_path = self._validate_path(target_path)

        if not requested_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: '{target_path}'.")

        if not requested_path.is_file():
            raise IsADirectoryError(
                f"'{target_path}' é um diretório. Use delete_directory para removê-lo."
            )

        requested_path.unlink()
        return f"Arquivo '{target_path}' removido com sucesso."

    # ──────────────────────────────────────────────
    # move_file
    # ──────────────────────────────────────────────

    def move_file(
        self,
        source_path: str,
        destination_path: str,
        overwrite: bool = False,
    ) -> str:
        """
        Move (ou renomeia) um arquivo dentro do workspace de forma segura.
        Tanto a origem quanto o destino são validados contra traversal e symlinks.

        Args:
            source_path:      Caminho relativo ao workspace do arquivo a mover.
            destination_path: Caminho relativo ao workspace do destino.
            overwrite:        Se False (padrão), lança erro se o destino já existir.

        Returns:
            Caminho relativo ao workspace do arquivo no novo local.

        Raises:
            FileNotFoundError: Se o arquivo de origem não existir.
            FileExistsError:   Se o destino já existir e overwrite=False.
            IsADirectoryError: Se a origem for um diretório (use move_directory).
            PermissionError:   Se qualquer caminho violar as proteções de segurança.
        """
        src = self._validate_path(source_path)
        dst = self._validate_path(destination_path)

        # Valida a origem
        if not src.exists():
            raise FileNotFoundError(f"Arquivo de origem não encontrado: '{source_path}'.")

        if not src.is_file():
            raise IsADirectoryError(
                f"'{source_path}' é um diretório. Use move_directory para movê-lo."
            )

        # Valida o destino
        if dst.exists() and not overwrite:
            raise FileExistsError(
                f"Destino já existe: '{destination_path}'. "
                "Use overwrite=True para substituir."
            )

        # Cria os diretórios intermediários do destino se necessário
        dst.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(src), str(dst))

        return str(dst.relative_to(self.base_workspace))

    # ──────────────────────────────────────────────
    # upload_file  ← NOVO: recebe bytes vindos do chat
    # ──────────────────────────────────────────────

    def upload_file(
        self,
        filename: str,
        file_bytes: bytes,
        subdirectory: str = "uploads",
    ) -> str:
        """
        Recebe o conteúdo de um arquivo enviado pelo usuário (ex: via chat)
        e o salva com segurança dentro do workspace.

        Fluxo esperado no backend:
            raw_bytes = await request.body()          # bytes do upload HTTP/multipart
            path = fs_tool.upload_file("foto.png", raw_bytes)

        Proteções aplicadas:
          - Extensão validada contra whitelist.
          - Tamanho limitado a max_upload_bytes.
          - Nome do arquivo sanitizado (sem separadores de path).
          - Salvo sempre dentro do workspace/subdirectory.

        Args:
            filename:     Nome original do arquivo (ex: "relatorio.pdf").
            file_bytes:   Conteúdo bruto do arquivo.
            subdirectory: Subpasta dentro do workspace onde salvar (padrão: 'uploads').

        Returns:
            Caminho relativo ao workspace onde o arquivo foi salvo.

        Raises:
            ValueError:     Se a extensão não for permitida ou o arquivo for grande demais.
            PermissionError: Se o subdirectory tentar escapar do workspace.
        """
        # 1. Sanitiza o nome: remove qualquer separador de caminho
        safe_name = Path(filename).name  # descarta qualquer "../../" no nome
        if not safe_name:
            raise ValueError("Nome de arquivo inválido.")

        # 2. Valida a extensão
        extension = Path(safe_name).suffix.lower()
        if extension not in ALLOWED_UPLOAD_EXTENSIONS:
            raise ValueError(
                f"Extensão '{extension}' não permitida. "
                f"Permitidas: {sorted(ALLOWED_UPLOAD_EXTENSIONS)}"
            )

        # 3. Valida o tamanho
        if len(file_bytes) > self.max_upload_bytes:
            raise ValueError(
                f"Arquivo muito grande: {len(file_bytes)} bytes "
                f"(limite: {self.max_upload_bytes} bytes)."
            )

        # 4. Valida e cria o subdiretório de destino
        dest_dir = self._validate_path(subdirectory)
        dest_dir.mkdir(parents=True, exist_ok=True)

        # 5. Salva o arquivo
        dest_path = dest_dir / safe_name
        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        # Retorna o caminho relativo ao workspace (conveniente para o agente referenciar)
        return str(dest_path.relative_to(self.base_workspace))