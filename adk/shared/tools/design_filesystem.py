"""
design_filesystem.py
─────────────
Camada de persistência usada exclusivamente pelo Agente IO.
Responsabilidade: ler, salvar, promover e listar artefatos em disco.

Logging de operações delegado integralmente ao IOLogger (design_logger.py).
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from .design_logger import IOLogger

def _find_root(start_path: Path, target: str = "adk") -> Path:
    for parent in start_path.parents:
        if parent.name == target:
            return parent
    return start_path.parents[4]  # Fallback seguro (Atualizar se necessário)

CURRENT_DIR = _find_root(Path(__file__).resolve())
STAGING_DIR = CURRENT_DIR / "temp" / "staging"
OFFICIAL_DIR = CURRENT_DIR / "artifacts"
LOG_FILENAME = "io_operations.log"
STATUS_IN_REVIEW = "**Status:** Em análise"
STATUS_BLOCKED = "**Status:** Bloqueado"
BACKUP_PREFIX = "_backup_"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers Privados
# ──────────────────────────────────────────────────────────────────────────────

def _ensure_dirs() -> None:
    """Garante que a estrutura de diretórios necessária exista."""
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    OFFICIAL_DIR.mkdir(parents=True, exist_ok=True)


def _is_safe_path(path: Path) -> bool:
    """
    Proteção contra Path Traversal.
    Verifica se o caminho resolvido permanece dentro da raiz do projeto.
    """
    try:
        resolved_path = path.resolve()
        return resolved_path.is_relative_to(CURRENT_DIR.resolve())
    except (ValueError, RuntimeError):
        return False


def _next_version(path: Path) -> Path:
    """Gera um caminho para backup com timestamp único."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path.parent / f"{path.stem}{BACKUP_PREFIX}{timestamp}{path.suffix}"

# ──────────────────────────────────────────────────────────────────────────────
# Funções Públicas (Ferramentas do Agente)
# ──────────────────────────────────────────────────────────────────────────────

def read_file(filepath: str) -> Dict[str, Any]:
    """Lê o conteúdo de um arquivo qualquer do filesystem do projeto.

    Use quando o IO Agent precisa devolver o conteúdo de um artefato
    salvo em staging ou artifacts a outro agente que solicita. Tem
    proteção contra path traversal: rejeita caminhos fora da raiz do
    projeto.

    Args:
        filepath: Caminho do arquivo a ser lido. Pode ser relativo ou
            absoluto, mas o caminho resolvido deve estar dentro da raiz
            do projeto.

    Returns:
        dict com chaves: `status` ("ok" | "error"), `content` (str
        UTF-8 em sucesso), `error` (str descritivo em falha — acesso
        negado, arquivo inexistente, erro de I/O).
    """
    try:
        path = Path(filepath).resolve()
        
        if not _is_safe_path(path):
            return {"status": "error", "error": "Acesso negado: o caminho solicitado está fora do diretório do projeto."}

        if not path.exists():
            return {"status": "error", "error": f"Arquivo {filepath} não encontrado."}

        content = path.read_text(encoding="utf-8")
        IOLogger.read(path.name)
        return {"status": "ok", "content": content}

    except Exception as e:
        IOLogger.error("read_file", str(e))
        return {"status": "error", "error": str(e)}

def save_artifact(filename: str, content: str) -> dict:
    """Persiste um artefato em staging com versionamento automático por backup.

    Use sempre que qualquer agente solicitar gravação de um artefato
    em staging (.mmd, .md, Doubt_Artifacts). Se já existir um arquivo
    com o mesmo nome em staging, o atual é renomeado para
    `<nome>_backup_<timestamp>.<ext>` antes da nova gravação — nunca
    sobrescreve sem backup.

    Doubt_Artifacts (nome iniciando com `Doubt_Artifact_`) são
    bloqueantes e devem ser gravados imediatamente, antes de qualquer
    outra operação pendente.

    Args:
        filename: Nome do arquivo (ex:
            `diagrama_HU-042_processo_compra.mmd`). Será gravado em
            `temp/staging/<filename>`.
        content: Conteúdo textual completo do artefato.

    Returns:
        dict com chaves: `status` ("ok" | "error"), `path` (str do
        path final em sucesso), `versioned_backup` (str do path do
        backup criado, se houve; None caso contrário), `timestamp`
        (ISO 8601). Em erro: `status="error"`, `error`, `filename`.
    """
    try:
        _ensure_dirs()
        destination = (STAGING_DIR / filename).resolve()
        
        if not _is_safe_path(destination):
            raise PermissionError("Segurança: Tentativa de escrita fora da área permitida.")

        versioned_backup = None

        if destination.exists():
            backup_path = _next_version(destination)
            shutil.move(str(destination), str(backup_path))
            versioned_backup = str(backup_path)

        destination.write_text(content, encoding="utf-8")
        timestamp = datetime.now().isoformat()

        IOLogger.save(filename, backup=versioned_backup)

        return {
            "status": "ok",
            "path": str(destination),
            "versioned_backup": versioned_backup,
            "timestamp": timestamp,
        }
    except Exception as e:
        IOLogger.error("save_artifact", str(e))
        return {"status": "error", "error": str(e), "filename": filename}


def promote_artifact(filename: str) -> Dict[str, Any]:
    """Promove um relatório de staging para artifacts/ (versão oficial).

    Use somente sob confirmação explícita do supervisor. Apenas
    arquivos `.md` cujo nome contém "relatorio" e que NÃO contêm o
    marcador "**Status:** Em análise" são aceitos. Diagramas `.mmd`
    e relatórios em análise permanecem em staging.

    Se já existir uma versão oficial com o mesmo nome em artifacts/,
    a antiga é renomeada para backup com timestamp antes da nova
    cópia.

    Args:
        filename: Nome do arquivo em staging a promover.

    Returns:
        dict com chaves: `status` ("ok" | "blocked" | "error"),
        `source`, `destination`, `timestamp` em sucesso; `reason` e
        `file` em "blocked"; `error` em "error".
    """
    try:
        source = (STAGING_DIR / filename).resolve()

        if not source.exists():
            return {"status": "error", "error": f"Arquivo {filename} não encontrado em staging."}

        if source.suffix != ".md":
            return {
                "status": "blocked",
                "reason": "Apenas relatórios .md podem ser promovidos para artifacts. Diagramas .mmd permanecem em staging.",
                "file": filename,
            }

        if "relatorio" not in filename:
            return {
                "status": "blocked",
                "reason": "Apenas relatórios .md podem ser promovidos para artifacts. A analise tecnica permanece em staging.",
                "file": filename,
            }

        content = source.read_text(encoding="utf-8")
        if STATUS_IN_REVIEW in content:
            return {
                "status": "blocked",
                "reason": f"O relatório ainda possui o marcador '{STATUS_IN_REVIEW}'. Aprovação manual necessária.",
                "file": filename,
            }

        _ensure_dirs()
        destination = (OFFICIAL_DIR / filename).resolve()

        if destination.exists():
            shutil.move(str(destination), str(_next_version(destination)))

        shutil.copy2(str(source), str(destination))
        timestamp = datetime.now().isoformat()

        IOLogger.promote(filename)

        return {
            "status": "ok",
            "source": str(source),
            "destination": str(destination),
            "timestamp": timestamp,
        }

    except Exception as e:
        IOLogger.error("promote_artifact", str(e))
        return {"status": "error", "error": str(e)}


def list_staging_files(filetype: str = "") -> Dict[str, Any]:
    """Lista os arquivos atualmente em staging, ignorando backups e logs.

    Use para inventariar artefatos disponíveis em staging antes de
    decidir leituras, promoções ou alertas de bloqueio. Backups
    (arquivos contendo `_backup_`) e o `io_operations.log` são
    sempre filtrados.

    Args:
        filetype: Extensão para filtrar sem o ponto (ex: "mmd", "md").
            Vazio retorna todos os arquivos visíveis.

    Returns:
        dict com chaves: `status` ("ok" | "error"), `files` (list[str]
        com nomes ordenados alfabeticamente em sucesso), `staging_dir`
        (path absoluto da pasta), `error` em falha.
    """
    try:
        _ensure_dirs()
        files = [
            f.name
            for f in sorted(STAGING_DIR.iterdir())
            if f.name != LOG_FILENAME
            and BACKUP_PREFIX not in f.name
            and (not filetype or f.suffix == f".{filetype}")
        ]
        return {"status": "ok", "files": files, "staging_dir": str(STAGING_DIR)}

    except Exception as e:
        IOLogger.error("list_staging_files", str(e))
        return {"status": "error", "error": str(e)}


def check_active_blocks() -> Dict[str, Any]:
    """Verifica se há Doubt_Artifacts com Status Bloqueado em staging.

    Use sempre que o orquestrador precisar decidir se pode avançar
    para a próxima etapa do pipeline. Cada Doubt_Artifact em staging
    é inspecionado pelo marcador "**Status:** Bloqueado"; o HU ID é
    extraído do nome (terceiro segmento separado por `_`).

    Returns:
        dict com chaves: `status` ("ok" | "error"), `has_blocks`
        (bool — True se algum artefato está bloqueado), `blocks`
        (list[dict] com `filename` e `hu_id` para cada bloqueio).
        Em falha: `status="error"`, `error`.
    """
    try:
        _ensure_dirs()
        blocks = []
        for f in sorted(STAGING_DIR.iterdir()):
            if f.name.startswith("Doubt_Artifact_") and BACKUP_PREFIX not in f.name:
                content = f.read_text(encoding="utf-8")
                if STATUS_BLOCKED in content:
                    parts = f.stem.split("_")
                    hu_id = parts[2] if len(parts) >= 3 else "desconhecido"
                    blocks.append({"filename": f.name, "hu_id": hu_id})
        
        return {"status": "ok", "has_blocks": len(blocks) > 0, "blocks": blocks}

    except Exception as e:
        IOLogger.error("check_active_blocks", str(e))
        return {"status": "error", "error": str(e)}

def clear_staging_folder() -> bool:
    """Remove todos os arquivos do diretório de staging, preservando subdiretórios.

    ATENÇÃO: operação destrutiva. Use APENAS no início de uma nova
    sessão, quando explicitamente solicitado pelo orquestrador. Nunca
    execute por iniciativa própria ou durante o fluxo normal de
    operações. A proteção interna verifica que o diretório está sob
    a raiz do projeto antes de apagar.

    Returns:
        bool: True se todos os arquivos foram removidos com sucesso,
        False em caso de erro (ex: tentativa fora do diretório seguro,
        falha de I/O). Erros são registrados via IOLogger.
    """
    path: Path = STAGING_DIR
    try:
        if not _is_safe_path(path):
            raise PermissionError(f"Segurança: Tentativa de apagar fora de {CURRENT_DIR}")

        _ensure_dirs()
        for file in path.iterdir():
            if file.is_file():
                file.unlink()

        IOLogger.erase(str(path))
        return True
    except Exception as e:
        IOLogger.error("ERASE", f"dir={path} | error={str(e)}")
        return False

# ──────────────────────────────────────────────────────────────────────────────
# Mocks
# ──────────────────────────────────────────────────────────────────────────────

def check_lock(filepath: str) -> dict:
    """Mock: verifica se o arquivo está bloqueado por outro agente."""
    return {"status": "ok", "locked": False, "filepath": filepath}


def release_lock(filepath: str) -> dict:
    """Mock: libera o lock do arquivo após escrita."""
    return {"status": "ok", "released": True, "filepath": filepath}


def list_versions(filepath: str) -> dict:
    """Mock: lista versões anteriores de um artefato."""
    return {"status": "ok", "versions": [], "filepath": filepath}
