"""
design_filesystem.py
─────────────
Camada de persistência usada exclusivamente pelo Agente IO.
Responsabilidade: ler, salvar, promover e listar artefatos em disco.

Logging de operações delegado integralmente ao IOLogger (design_logger.py).
"""

from pydantic import fields
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
PROTOTYPE_DIR = STAGING_DIR / "prototype"
LOG_FILENAME = "io_operations.log"
STATUS_IN_REVIEW = "**Status:** Em análise"
STATUS_BLOCKED = "**Status:** Bloqueado"
BACKUP_PREFIX = "_backup_"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers Privados
# ──────────────────────────────────────────────────────────────────────────────

def _ensure_dirs() -> None:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    OFFICIAL_DIR.mkdir(parents=True, exist_ok=True)
    PROTOTYPE_DIR.mkdir(parents=True, exist_ok=True)


def _is_safe_path(path: Path) -> bool:
    try:
        resolved_path = path.resolve()
        return resolved_path.is_relative_to(CURRENT_DIR.resolve())
    except (ValueError, RuntimeError):
        return False


def _next_version(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path.parent / f"{path.stem}{BACKUP_PREFIX}{timestamp}{path.suffix}"

# ──────────────────────────────────────────────────────────────────────────────
# Funções Públicas (Ferramentas do Agente)
# ──────────────────────────────────────────────────────────────────────────────

def read_file(filepath: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Lê o conteúdo de um arquivo do filesystem.

    Args:
        filepath: caminho do arquivo a ser lido.
        caller:   nome do agente solicitante (para rastreabilidade no log).

    Returns:
        dict com keys: status, content | error
    """
    try:
        path = Path(filepath).resolve()

        if not path.exists():
            if filepath.endswith(".html") or filepath.endswith(".css"):
                alt_path = (PROTOTYPE_DIR / Path(filepath).name).resolve()
                if alt_path.exists():
                    path = alt_path

        if not _is_safe_path(path):
            return {"status": "error", "error": "Acesso negado: o caminho solicitado está fora do diretório do projeto."}

        if not path.exists():
            return {"status": "error", "error": f"Arquivo {filepath} não encontrado."}

        content = path.read_text(encoding="utf-8")
        IOLogger.read(path.name, caller=caller)
        return {"status": "ok", "content": content}

    except Exception as e:
        IOLogger.error("read_file", str(e), caller=caller)
        return {"status": "error", "error": str(e)}

def read_analysis_sections(filepath: str, sections: list[int], caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Lê apenas seções específicas de um arquivo de análise técnica (Markdown).
    Isso reduz a quantidade de tokens processados pelo LLM ao filtrar seções irrelevantes.

    Args:
        filepath: caminho do arquivo a ser lido.
        sections: lista de inteiros das seções desejadas (ex: [1, 4, 6]).
        caller:   nome do agente solicitante (para rastreabilidade no log).

    Returns:
        dict com keys: status, content | error
    """
    try:
        import re
        path = Path(filepath).resolve()

        if not path.exists():
            if filepath.endswith(".html") or filepath.endswith(".css"):
                alt_path = (PROTOTYPE_DIR / Path(filepath).name).resolve()
                if alt_path.exists():
                    path = alt_path

        if not _is_safe_path(path):
            return {"status": "error", "error": "Acesso negado: o caminho solicitado está fora do diretório do projeto."}

        if not path.exists():
            return {"status": "error", "error": f"Arquivo {filepath} não encontrado."}

        content = path.read_text(encoding="utf-8")
        
        # O arquivo de análise usa '---' para separar seções primárias
        parts = re.split(r'\n---\n', content)
        
        extracted = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            first_line = part.split('\n')[0].strip()
            match = re.match(r'^(\d+)\.', first_line)
            
            if match:
                sec_num = int(match.group(1))
                if sec_num in sections:
                    extracted.append(part)
                
        IOLogger.read(path.name + f" [sections:{sections}]", caller=caller)

        if not extracted:
            return {"status": "warning", "content": content, "msg": "Não foi possível extrair as seções solicitadas. Retornando arquivo completo."}
            
        return {"status": "ok", "content": "\n\n---\n\n".join(extracted)}

    except Exception as e:
        IOLogger.error("read_analysis_sections", str(e), caller=caller)
        return {"status": "error", "error": str(e)}

def read_multiple_files(filepaths: list[str], caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Lê o conteúdo de múltiplos arquivos simultaneamente em batch.
    Isso otimiza o LLM evitando múltiplas chamadas consecutivas para a mesma ação.

    Args:
        filepaths: lista de caminhos dos arquivos a serem lidos (ex: ["file1.mmd", "file2.mmd"]).
        caller:   nome do agente solicitante (para rastreabilidade no log).

    Returns:
        dict com keys: status, contents (dict mapeando filepath -> {status, content | error})
    """
    try:
        contents = {}
        for filepath in filepaths:
            path = Path(filepath).resolve()

            if not path.exists():
                if filepath.endswith(".html") or filepath.endswith(".css"):
                    alt_path = (PROTOTYPE_DIR / Path(filepath).name).resolve()
                    if alt_path.exists():
                        path = alt_path

            if not _is_safe_path(path):
                contents[filepath] = {"status": "error", "error": "Acesso negado fora do diretório."}
                continue

            if not path.exists():
                contents[filepath] = {"status": "error", "error": "Arquivo não encontrado."}
                continue    

            content = path.read_text(encoding="utf-8")
            contents[filepath] = {"status": "ok", "content": content}

        # Identifica tipos de arquivos únicos para o log
        file_types = {Path(f).suffix.lstrip('.').lower() for f in filepaths if '.' in f}
        str_file_types = ", ".join(file_types) if file_types else "sem extensão"
            
        IOLogger.read(f"[batch: {len(filepaths)} files | types: {str_file_types}]", caller=caller)
        return {"status": "ok", "contents": contents}

    except Exception as e:
        IOLogger.error("read_multiple_files", str(e), caller=caller)
        return {"status": "error", "error": str(e)}

def save_artifact(filename: str, content: str, caller: str | None = "unknown") -> dict:
    """
    Salva o artefato em staging com versionamento automático.

    Args:
        filename: Nome do arquivo.
        content:  Conteúdo textual do artefato.
        caller:   nome do agente solicitante (para rastreabilidade no log).

    Returns:
        dict com keys: status, path, versioned_backup (se houve), timestamp
    """
    try:
        _ensure_dirs()

        clean_filename = filename.replace("prototype/", "").replace("staging/", "")

        target_dir = STAGING_DIR
        if clean_filename.endswith(".html") or clean_filename == "global.css":
            target_dir = PROTOTYPE_DIR

        destination = (target_dir / clean_filename).resolve()

        if not _is_safe_path(destination):
            raise PermissionError("Segurança: Tentativa de escrita fora da área permitida.")

        destination.parent.mkdir(parents=True, exist_ok=True)

        versioned_backup = None
        if destination.exists():
            backup_path = _next_version(destination)
            shutil.move(str(destination), str(backup_path))
            versioned_backup = str(backup_path)

        destination.write_text(content, encoding="utf-8")
        timestamp = datetime.now().isoformat()
        if not versioned_backup:
            versioned_backup = ""

        IOLogger.save(filename, caller=caller, backup=versioned_backup)

        return {
            "status": "ok",
            "path": str(destination),
            "versioned_backup": versioned_backup,
            "timestamp": timestamp,
        }
    except Exception as e:
        IOLogger.error("save_artifact", str(e), caller=caller)
        return {"status": "error", "error": str(e), "filename": filename}

def promote_artifact(filename: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Move um artefato de staging para artifacts/.

    Args:
        filename: Nome do arquivo a ser promovido.
        caller:   nome do agente solicitante (para rastreabilidade no log).

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

        IOLogger.promote(filename, caller=caller)

        return {
            "status": "ok",
            "source": str(source),
            "destination": str(destination),
            "timestamp": timestamp,
        }

    except Exception as e:
        IOLogger.error("promote_artifact", str(e), caller=caller)
        return {"status": "error", "error": str(e)}

def list_staging_files(filetype: str = "", caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Lista arquivos em staging, ignorando backups e o log de operações.

    Args:
        filetype: extensão para filtrar (ex: "mmd", "md"). Se vazio, lista todos.
        caller:   nome do agente solicitante (para rastreabilidade no log).

    Returns:
        dict com keys: status, files, staging_dir | error
    """
    try:
        _ensure_dirs()

        files = [
            f.name
            for f in sorted(STAGING_DIR.iterdir())
            if f.is_file()
            and f.name != LOG_FILENAME
            and BACKUP_PREFIX not in f.name
            and (not filetype or f.suffix == f".{filetype}")
        ]

        if not filetype or filetype in ["html", "css"]:
            proto_files = [
                f.name
                for f in sorted(PROTOTYPE_DIR.iterdir())
                if f.is_file()
                and BACKUP_PREFIX not in f.name
                and (not filetype or f.suffix == f".{filetype}")
            ]
            files.extend(proto_files)

        IOLogger.read(f"[list:{filetype or 'all'}]", caller=caller)
        return {"status": "ok", "files": sorted(list(set(files))), "staging_dir": str(STAGING_DIR)}

    except Exception as e:
        IOLogger.error("list_staging_files", str(e), caller=caller)
        return {"status": "error", "error": str(e)}

def copy_file(source_path: str, destination_filename: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Copia um arquivo existente para um novo local em staging/prototype.

    Args:
        source_path:          Caminho completo do arquivo de origem.
        destination_filename: Nome do arquivo de destino.
        caller:               nome do agente solicitante (para rastreabilidade no log).

    Returns:
        dict com status e detalhes da operação.
    """
    try:
        _ensure_dirs()
        src = (CURRENT_DIR / source_path).resolve()

        if not src.exists():
            return {"status": "error", "error": f"Arquivo de origem {source_path} não encontrado."}

        clean_filename = destination_filename.replace("prototype/", "").replace("staging/", "")
        target_dir = STAGING_DIR
        if clean_filename.endswith(".html") or clean_filename == "global.css":
            target_dir = PROTOTYPE_DIR

        dest = (target_dir / clean_filename).resolve()

        if not _is_safe_path(dest):
            raise PermissionError("Segurança: Tentativa de escrita fora da área permitida.")

        shutil.copy2(str(src), str(dest))
        IOLogger.copy(source_path, dest, caller=caller)

        return {
            "status": "ok",
            "source": str(src),
            "destination": str(dest),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        IOLogger.error("copy_file", str(e), caller=caller)
        return {"status": "error", "error": str(e)}

def check_active_blocks(caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Verifica se há Doubt_Artifacts com Status: Bloqueado em staging.

    Args:
        caller: nome do agente solicitante (para rastreabilidade no log).

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

        IOLogger.read("[check_active_blocks]", caller=caller)
        return {"status": "ok", "has_blocks": len(blocks) > 0, "blocks": blocks}

    except Exception as e:
        IOLogger.error("check_active_blocks", str(e), caller=caller)
        return {"status": "error", "error": str(e)}

def clear_staging_folder(caller: str | None = "unknown") -> bool:
    """
    Remove todos os arquivos do diretório de staging e seus subdiretórios,
    preservando a estrutura de pastas.

    Args:
        caller: nome do agente solicitante (para rastreabilidade no log).

    Returns:
        bool: True se todos os arquivos foram removidos com sucesso, False caso contrário.
    """
    try:
        _ensure_dirs()

        def _clear_recursive(directory: Path):
            if not _is_safe_path(directory):
                return
            for item in directory.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    _clear_recursive(item)

        _clear_recursive(STAGING_DIR)
        IOLogger.erase(str(STAGING_DIR), caller=caller)
        return True
    except Exception as e:
        IOLogger.error("ERASE", f"dir={STAGING_DIR} | error={str(e)}", caller=caller)
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
