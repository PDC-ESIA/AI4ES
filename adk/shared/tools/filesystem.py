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
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return parent / f"{stem}_backup_{timestamp}{suffix}"

def read_file(filepath: str) -> dict:
    """
    Lê o conteúdo de um arquivo do filesystem.

    Args:
        filepath: caminho do arquivo a ser lido

    Returns:
        dict com keys: status, content
    """
    try:
        path = Path(filepath)
        if not path.exists():
            return {"status": "error", "error": f"Arquivo {filepath} não encontrado."}
        content = path.read_text(encoding="utf-8")
        return {"status": "ok", "content": content}
    except Exception as e:
        return {"status": "error", "error": str(e)}

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
    Move um artefato de .../temp/staging/ para .../artifacts/.
    Apenas arquivos .md são aceitos — diagramas .mmd ficam somente em staging.
    Bloqueia promoção se status ainda for 'Em análise'.
    """
    try:
        source = STAGING_DIR / filename
        if not source.exists():
            return {"status": "error", "error": f"Arquivo {filename} não encontrado em staging."}

        # Somente relatórios .md podem ser promovidos
        if source.suffix != ".md":
            return {
                "status": "blocked",
                "reason": f"Apenas relatórios .md podem ser promovidos para artifacts. Diagramas .mmd permanecem em staging.",
                "file": filename,
            }

        # Bloqueia se status ainda pendente
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

def list_staging_files(filetype: str = "") -> dict:
    """
    Lista os arquivos disponíveis em staging, opcionalmente filtrados por tipo.
    Retorna apenas a versão mais recente de cada arquivo (ignora backups).

    Args:
        filetype: extensão para filtrar (ex: "mmd", "md"). Se vazio, lista todos.

    Returns:
        dict com keys: status, files (lista de nomes), staging_dir
    """
    try:
        _ensure_dirs()
        files = []
        for f in sorted(STAGING_DIR.iterdir()):
            if f.name == "save_log.txt":
                continue
            if "_backup_" in f.name:
                continue
            if filetype and f.suffix != f".{filetype}":
                continue
            files.append(f.name)

        return {
            "status": "ok",
            "files": files,
            "staging_dir": str(STAGING_DIR),
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