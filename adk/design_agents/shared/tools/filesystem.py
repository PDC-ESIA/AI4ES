"""
filesystem.py
─────────────
Camada de persistência usada exclusivamente pelo Agente IO.
Responsabilidade: ler, salvar, promover e listar artefatos em disco.

Logging de operações delegado integralmente ao IOLogger (io_logger.py).
"""

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from .logger import IOLogger

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
    """
    Lê o conteúdo de um arquivo do filesystem.

    Args:
        filepath: caminho do arquivo a ser lido.

    Returns:
        dict com keys: status, content | error
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
    """
    Salva o artefato em staging com versionamento automático.

    - Se já existir um arquivo com o mesmo nome: renomeia o atual para _backup_ antes de salvar.

    Args:
        filename: Nome do arquivo (ex: diagrama_HU-042_processo_compra.mmd)
        content:  Conteúdo textual do artefato.

    Returns:
        dict com keys: status, path, versioned_backup (se houve), timestamp
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
    """
    Move um artefato de staging para artifacts/.

    Regras:
        - Apenas arquivos .md são aceitos.
        - O nome deve conter 'relatorio'.
        - O conteúdo não pode ter status 'Em análise'.

    Args:
        filename: Nome do arquivo a ser promovido

    Returns:
        dict com keys: status, source, destination, timestamp | reason | error
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
    """
    Lista arquivos em staging, ignorando backups e o log de operações.

    Args:
        filetype: extensão para filtrar (ex: "mmd", "md"). Se vazio, lista todos.

    Returns:
        dict com keys: status, files, staging_dir | error
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
    """
    Verifica se há Doubt_Artifacts com Status: Bloqueado em staging.

    Returns:
        dict com keys: status, has_blocks (bool), blocks (lista de dicts)
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
    """
    Remove todos os arquivos do diretório de staging, preservando subdiretórios.
    Segurança: só apaga se o diretório estiver dentro de CURRENT_DIR.

    Returns:
        bool: True se todos os arquivos foram removidos com sucesso, False caso contrário
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
