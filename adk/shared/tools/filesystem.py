import os
import shutil
from datetime import datetime
from pathlib import Path

STAGING_DIR = Path("temp/staging")
OFFICIAL_DIR = Path("artifacts")


def _ensure_dirs():
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    OFFICIAL_DIR.mkdir(parents=True, exist_ok=True)


def _next_version(path: Path) -> Path:
    """Retorna o caminho versionado disponível ex: arquivo_v1.mmd, arquivo_v2.mmd"""
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    n = 1
    while True:
        versioned = parent / f"{stem}_v{n}{suffix}"
        if not versioned.exists():
            return versioned
        n += 1


def save_artifact(filename: str, content: str) -> dict:
    """
    Salva o artefato em staging com versionamento automático.

    - Se já existir um arquivo com o mesmo nome em staging: renomeia o atual para _v{n} antes de salvar.
    - Registra log da operação em temp/staging/save_log.txt.

    Args:
        filename: Nome do arquivo (ex: diagrama_HU-042_processo_compra.mmd)
        content:  Conteúdo textual do artefato

    Returns:
        dict com keys: status, path, versioned_backup (se houve), timestamp
    """
    try:
        _ensure_dirs()
        destination = STAGING_DIR / filename
        versioned_backup = None

        # Versionamento: se já existe, move o atual para _v{n} antes de salvar
        if destination.exists():
            backup_path = _next_version(destination)
            shutil.move(str(destination), str(backup_path))
            versioned_backup = str(backup_path)

        # Salva o novo artefato
        destination.write_text(content, encoding="utf-8")

        timestamp = datetime.now().isoformat()

        # Log da operação
        log_entry = (
            f"[{timestamp}] SAVE | file={filename}"
            + (f" | backup={versioned_backup}" if versioned_backup else "")
            + "\n"
        )
        log_path = STAGING_DIR / "save_log.txt"
        with log_path.open("a", encoding="utf-8") as log:
            log.write(log_entry)

        return {
            "status": "ok",
            "path": str(destination),
            "versioned_backup": versioned_backup,
            "timestamp": timestamp,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "filename": filename,
        }

def promote_artifact(filename: str) -> dict:
    """
    Move um artefato de /temp/staging/ para /artifacts/.
    """
    try:
        source = STAGING_DIR / filename
        if not source.exists():
            return {"status": "error", "error": f"Arquivo {filename} não encontrado em staging."}
        
        _ensure_dirs()
        destination = OFFICIAL_DIR / filename
        
        if destination.exists():
            backup = _next_version(destination)
            shutil.move(str(destination), str(backup))
        
        shutil.copy2(str(source), str(destination))
        
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] PROMOTE | file={filename} | from=staging | to=artifacts\n"
        log_path = STAGING_DIR / "save_log.txt"
        with log_path.open("a", encoding="utf-8") as log:
            log.write(log_entry)
        
        return {
            "status": "ok",
            "source": str(source),
            "destination": str(destination),
            "timestamp": timestamp,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
    
# --- MOCKS ---

def check_lock(filepath: str) -> dict:
    """Mock: verifica se o arquivo está bloqueado por outro agente."""
    return {"status": "ok", "locked": False, "filepath": filepath}


def release_lock(filepath: str) -> dict:
    """Mock: libera o lock do arquivo após escrita."""
    return {"status": "ok", "released": True, "filepath": filepath}


def list_versions(filepath: str) -> dict:
    """Mock: lista versões anteriores de um artefato."""
    return {"status": "ok", "versions": [], "filepath": filepath}