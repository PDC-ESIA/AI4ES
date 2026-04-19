import os
import shutil
from datetime import datetime
from pathlib import Path

STAGING_DIR = Path("temp/staging")
OFFICIAL_DIR = Path("artifacts")

# LOG_DETAIL: controla o nível de detalhe do log de operações.
# - "DEFAULT": apenas SAVE e PROMOTE são registrados (comportamento original).
# - "HIGH":    READ também é registrado, útil para rastrear quais agentes
#              leram quais arquivos e em que momento.
LOG_DETAIL = "HIGH"

def _ensure_dirs():
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    OFFICIAL_DIR.mkdir(parents=True, exist_ok=True)

def _next_version(path: Path) -> Path:
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return parent / f"{stem}_backup_{timestamp}{suffix}"

def _write_log(entry: str):
    """Escreve uma entrada no log de operações."""
    log_path = STAGING_DIR / "io_operations.log"
    with log_path.open("a", encoding="utf-8") as log:
        log.write(entry)

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

        if LOG_DETAIL == "HIGH":
            _ensure_dirs()
            timestamp = datetime.now().isoformat()
            log_entry = f"[{timestamp}] READ  | file={path.name}\n"
            _write_log(log_entry)

        return {"status": "ok", "content": content}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def save_artifact(filename: str, content: str) -> dict:
    """
    Salva o artefato em staging com versionamento automático.

    - Se já existir um arquivo com o mesmo nome em staging: renomeia o atual para _backup_ antes de salvar.
    - Registra log da operação em temp/staging/io_operations.log.

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

        if destination.exists():
            backup_path = _next_version(destination)
            shutil.move(str(destination), str(backup_path))
            versioned_backup = str(backup_path)

        destination.write_text(content, encoding="utf-8")

        timestamp = datetime.now().isoformat()
        log_entry = (
            f"[{timestamp}] SAVE  | file={filename}"
            + (f" | backup={versioned_backup}" if versioned_backup else "")
            + "\n"
        )
        _write_log(log_entry)

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
    O único artefato que pode ser promovido é o relatorio<HUs>.md
    Apenas arquivos .md são aceitos — diagramas .mmd e análises técnicas ficam somente em staging.
    Bloqueia promoção se status ainda for 'Em análise'.
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
            backup = _next_version(destination)
            shutil.move(str(destination), str(backup))

        shutil.copy2(str(source), str(destination))

        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] PROMOTE | file={filename} | from=staging | to=artifacts\n"
        _write_log(log_entry)

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
            if f.name == "io_operations.log":
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

def check_active_blocks() -> dict:
    """
    Verifica se há Doubt_Artifacts com Status Bloqueado em staging.

    Returns:
        dict com keys: status, has_blocks (bool), blocks (lista de dicts com filename e hu_id)
    """
    try:
        _ensure_dirs()
        blocks = []
        for f in sorted(STAGING_DIR.iterdir()):
            if not f.name.startswith("Doubt_Artifact_"):
                continue
            if "_backup_" in f.name:
                continue
            content = f.read_text(encoding="utf-8")
            if "**Status:** Bloqueado" in content:
                parts = f.stem.split("_")
                hu_id = parts[2] if len(parts) >= 3 else "desconhecido"
                blocks.append({
                    "filename": f.name,
                    "hu_id": hu_id,
                })

        return {
            "status": "ok",
            "has_blocks": len(blocks) > 0,
            "blocks": blocks,
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