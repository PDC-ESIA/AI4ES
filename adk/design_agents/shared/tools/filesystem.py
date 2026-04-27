"""
filesystem.py
─────────────
Camada de persistência usada exclusivamente pelo Agente IO.
Responsabilidade: ler, salvar, promover e listar artefatos em disco.

Logging de operações delegado integralmente ao IOLogger (io_logger.py).
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

from .logger import IOLogger

STAGING_DIR  = Path("temp/staging")
OFFICIAL_DIR = Path("artifacts")

def _ensure_dirs() -> None:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    OFFICIAL_DIR.mkdir(parents=True, exist_ok=True)


def _next_version(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path.parent / f"{path.stem}_backup_{timestamp}{path.suffix}"

def read_file(filepath: str) -> dict:
    """
    Lê o conteúdo de um arquivo do filesystem.

    Args:
        filepath: caminho do arquivo a ser lido.

    Returns:
        dict com keys: status, content | error
    """
    try:
        path = Path(filepath)
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
        destination = STAGING_DIR / filename
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

def promote_artifact(filename: str) -> dict:
    """
    Move um artefato de staging para artifacts/.

    Regras:
        - Apenas arquivos .md são aceitos.
        - O nome deve conter 'relatorio'.
        - O conteúdo não pode ter status 'Em análise'.

    Returns:
        dict com keys: status, source, destination, timestamp | reason | error
    """
    try:
        source = STAGING_DIR / filename

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
        if "**Status:** Em análise" in content:
            return {
                "status": "blocked",
                "reason": "O relatório ainda está com status 'Em análise'. Altere para 'Aprovado' antes de promover.",
                "file": filename,
            }

        _ensure_dirs()
        destination = OFFICIAL_DIR / filename

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

def list_staging_files(filetype: str = "") -> dict:
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
            if f.name != "io_operations.log"
            and "_backup_" not in f.name
            and (not filetype or f.suffix == f".{filetype}")
        ]
        return {"status": "ok", "files": files, "staging_dir": str(STAGING_DIR)}

    except Exception as e:
        IOLogger.error("list_staging_files", str(e))
        return {"status": "error", "error": str(e)}

def check_active_blocks() -> dict:
    """
    Verifica se há Doubt_Artifacts com Status: Bloqueado em staging.

    Returns:
        dict com keys: status, has_blocks (bool), blocks (lista de dicts)
    """
    try:
        _ensure_dirs()
        blocks = [
            {
                "filename": f.name,
                "hu_id": (parts := f.stem.split("_"))[2] if len(parts) >= 3 else "desconhecido",
            }
            for f in sorted(STAGING_DIR.iterdir())
            if f.name.startswith("Doubt_Artifact_")
            and "_backup_" not in f.name
            and "**Status:** Bloqueado" in f.read_text(encoding="utf-8")
        ]
        return {"status": "ok", "has_blocks": len(blocks) > 0, "blocks": blocks}

    except Exception as e:
        IOLogger.error("check_active_blocks", str(e))
        return {"status": "error", "error": str(e)}

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