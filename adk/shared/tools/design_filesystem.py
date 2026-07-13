"""
design_filesystem.py
─────────────
Camada de persistência usada exclusivamente pelo Agente IO.
Responsabilidade: ler, salvar, promover e listar artefatos em disco.

Logging de operações delegado integralmente ao IOLogger (design_logger.py).
"""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from .design_logger import IOLogger

def _find_root(start_path: Path, target: str = "adk") -> Path:
    for parent in start_path.parents:
        if parent.name == target:
            return parent
    return start_path.parents[4]  # Fallback seguro (Atualizar se necessário)

ADK_DIR = _find_root(Path(__file__).resolve())
DESIGN_DIR = ADK_DIR / "workspace_output" / "design"

ANALYSIS_DIR = DESIGN_DIR / "analysis"
DIAGRAMS_DIR = DESIGN_DIR / "diagrams"
PROTOTYPE_DIR = DESIGN_DIR / "prototypes"
REPORT_DIR = DESIGN_DIR / "reports"
DOUBT_DIR = DESIGN_DIR / "doubts"
OFFICIAL_DIR = DESIGN_DIR / "entrega_final" # Sujeito a mudanças
LOCKS_DIR = DESIGN_DIR / ".locks"

TEMPLATE_DIR = ADK_DIR / "shared" / "templates"
LOG_FILENAME = "io_operations.log"
STATUS_IN_REVIEW = "**Status:** Em análise"
STATUS_BLOCKED = "**Status:** Bloqueado"
BACKUP_PREFIX = "_backup_"
_SECTION_SEPARATOR = "\n<<<FIM_SECAO>>>\n"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers Privados
# ──────────────────────────────────────────────────────────────────────────────

def _ensure_dirs() -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)
    PROTOTYPE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    DOUBT_DIR.mkdir(parents=True, exist_ok=True)
    OFFICIAL_DIR.mkdir(parents=True, exist_ok=True)
    LOCKS_DIR.mkdir(parents=True, exist_ok=True)


def _is_safe_path(path: Path) -> bool:
    try:
        resolved_path = path.resolve()
        return resolved_path.is_relative_to(ADK_DIR.resolve())
    except (ValueError, RuntimeError):
        return False


def _next_version(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path.parent / f"{path.stem}{BACKUP_PREFIX}{timestamp}{path.suffix}"


# Ordem de busca usada quando o agente não especifica uma pasta.
# read_file e read_multiple_files percorrem essa lista e retornam o primeiro match.
_SEARCH_ORDER: list[Path] = [ANALYSIS_DIR, DIAGRAMS_DIR, PROTOTYPE_DIR]

# Mapa de aliases simbólicos → diretório canônico.
# Chaves sempre em minúsculas; a normalização é feita em _resolve_folder_alias.
_FOLDER_ALIASES: Dict[str, Path] = {
    # ANALYSIS
    "analysis":         ANALYSIS_DIR,
    "analysis_dir":     ANALYSIS_DIR,
    "analysis_folder":  ANALYSIS_DIR,
    # DIAGRAMS
    "diagrams":         DIAGRAMS_DIR,
    "diagrams_dir":     DIAGRAMS_DIR,
    "diagrams_folder":  DIAGRAMS_DIR,
    # PROTOTYPE
    "prototype":        PROTOTYPE_DIR,
    "prototype_dir":    PROTOTYPE_DIR,
    "prototype_folder": PROTOTYPE_DIR,
    # REPORT
    "report":           REPORT_DIR,
    "report_dir":       REPORT_DIR,
    "report_folder":    REPORT_DIR,
    # DOUBT
    "doubt":            DOUBT_DIR,
    "doubt_dir":        DOUBT_DIR,
    "doubt_folder":     DOUBT_DIR,
    # templates
    "template":         TEMPLATE_DIR,
    "template_dir":     TEMPLATE_DIR,
    "template_folder":  TEMPLATE_DIR,
}

# Nomes exibidos nas mensagens de erro — apenas os canônicos, legível para o agente.
_FOLDER_ALIAS_DISPLAY = (
    "ANALYSIS, ANALYSIS_DIR, ANALYSIS_FOLDER, "
    "DIAGRAMS, DIAGRAMS_DIR, DIAGRAMS_FOLDER, "
    "PROTOTYPE, PROTOTYPE_DIR, PROTOTYPE_FOLDER, "
    "REPORT, REPORT_DIR, REPORT_FOLDER, "
    "DOUBT, DOUBT_DIR, DOUBT_FOLDER, "
    "TEMPLATE_DIR, TEMPLATE_FOLDER"
)


def _resolve_folder_alias(token: str) -> "tuple[Path | None, str | None]":
    """
    Converte um token simbólico de pasta no Path absoluto correspondente.

    Retorna (Path, None) se o alias for reconhecido, ou (None, mensagem_de_erro)
    se o token não estiver no mapa.  Token vazio retorna (None, None) — sem erro,
    sem pasta; o chamador usa a lógica padrão (busca em _SEARCH_ORDER ou STAGING_DIR).
    """
    if not token:
        return None, None
    resolved = _FOLDER_ALIASES.get(token.lower().strip())
    if resolved is not None:
        return resolved, None
    error = (
        f"Pasta '{token}' não reconhecida. "
        f"Pastas disponíveis: {_FOLDER_ALIAS_DISPLAY}."
    )
    return None, error


def _split_folder_and_name(raw: str) -> "tuple[str, str]":
    """
    Separa um token de pasta de um nome de arquivo em `raw`.

    Exemplos:
        "REPORT/relatorio.md"    → ("REPORT",    "relatorio.md")
        "relatorio.md"           → ("",           "relatorio.md")
        "PROTOTYPE/"             → ("PROTOTYPE",  "")
    """
    normalized = raw.strip().replace("\\", "/")
    if "/" not in normalized:
        return "", normalized
    prefix, rest = normalized.split("/", 1)
    return prefix, rest.strip("/")


def _resolve_path_arg(raw: str) -> "tuple[Path | None, str, str | None]":
    """
    Ponto único de resolução para qualquer argumento de caminho vindo do agente.

    Aceita:
        "relatorio.md"              → busca em _SEARCH_ORDER, ou STAGING_DIR como destino
        "ANALYSIS/relatorio.md"     → ANALYSIS_DIR,  "relatorio.md",   sem erro
        "PROTOTYPE/login.html"      → PROTOTYPE_DIR, "login.html",     sem erro
        "spec/algo.md"              → None,           "algo.md",       mensagem de erro

    Retorna:
        (resolved_dir, clean_filename, error_msg)

        resolved_dir   — Path do diretório ou None (sem alias explícito).
        clean_filename — nome do arquivo sem prefixo de pasta.
        error_msg      — None se ok; string se o prefixo não foi reconhecido.
    """
    folder_token, filename = _split_folder_and_name(raw)
    resolved_dir, error = _resolve_folder_alias(folder_token)
    return resolved_dir, filename, error


def _find_existing_file(filename: str) -> "Path | None":
    """
    Procura `filename` em _SEARCH_ORDER e retorna o primeiro Path que existe.
    Retorna None se não encontrado em nenhuma pasta conhecida.
    """
    for directory in _SEARCH_ORDER:
        candidate = (directory / filename).resolve()
        if _is_safe_path(candidate) and candidate.exists():
            return candidate
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Helpers Privados — Lock de Escrita
# ──────────────────────────────────────────────────────────────────────────────
#
# O lock é indexado pelo NOME do arquivo (alias de pasta é ignorado): o mesmo
# nome resolve sempre para o mesmo lock, independente de como o especialista
# referenciou a pasta. Locks vivem em LOCKS_DIR como arquivos JSON criados
# atomicamente (O_CREAT | O_EXCL) — dois especialistas nunca obtêm o mesmo lock.
# Leituras nunca consultam locks; apenas operações de escrita são controladas.


def _lock_path(filename: str) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    return LOCKS_DIR / f"{safe_name}.lock"


def _read_lock(lock_file: Path) -> "Dict[str, Any] | None":
    """Retorna os metadados do lock ou None se o arquivo estiver livre."""
    try:
        return json.loads(lock_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError):
        # Lock ilegível: trata como ocupado por dono desconhecido (conservador).
        return {"owner": "desconhecido", "acquired_at": ""}


def _check_write_permission(filename: str, caller: str | None) -> "Dict[str, Any] | None":
    """
    Valida se `caller` possui permissão de escrita (lock) sobre `filename`.

    Retorna None quando autorizado, ou um dict de erro pronto para ser
    devolvido ao agente quando a escrita deve ser bloqueada.
    """
    lock_info = _read_lock(_lock_path(filename))
    if lock_info is None:
        return {
            "status": "blocked",
            "error": (
                f"Escrita bloqueada: nenhum lock ativo para '{filename}'. "
                "Adquira permissão de escrita com acquire_lock (informando seu nome em caller) "
                "antes de modificar o arquivo e libere-o com release_lock ao terminar."
            ),
            "filename": filename,
        }
    owner = lock_info.get("owner", "desconhecido")
    if owner != (caller or ""):
        return {
            "status": "blocked",
            "error": (
                f"Escrita bloqueada: o arquivo '{filename}' está com lock de '{owner}'. "
                f"Somente '{owner}' pode modificá-lo até liberar o lock via release_lock."
            ),
            "filename": filename,
            "locked_by": owner,
        }
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Funções Públicas (Ferramentas do Agente)
# ──────────────────────────────────────────────────────────────────────────────

def read_file(filepath: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Lê e retorna o conteúdo completo de um arquivo.

    O agente pode informar apenas o nome do arquivo ou prefixá-lo com um alias
    de pasta. Quando nenhum alias é fornecido, o sistema busca automaticamente
    em ANALYSIS → DIAGRAMS → PROTOTYPE e retorna o primeiro arquivo encontrado.

    Args:
        filepath: Nome do arquivo, com ou sem alias de pasta.
                  Exemplos: "relatorio_HU-001.md"
                            "STAGING/relatorio_HU-001.md"
                            "PROTOTYPE/login.html"
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).

    Returns:
        dict com chaves: `status` ("ok" | "error"), `content` (str
        UTF-8 em sucesso), `error` (str descritivo em falha — acesso
        negado, arquivo inexistente, erro de I/O).
    """
    try:
        resolved_dir, filename, error = _resolve_path_arg(filepath)
        if error:
            return {"status": "error", "error": error}

        if resolved_dir is not None:
            # Alias explícito: olha só na pasta indicada
            path = (resolved_dir / filename).resolve()
            if not _is_safe_path(path):
                return {"status": "error", "error": "Acesso negado: caminho fora do projeto."}
            if not path.exists():
                return {"status": "error", "error": f"Arquivo '{filename}' não encontrado em {resolved_dir.name}."}
        else:
            # Sem alias: busca em todas as pastas conhecidas
            path = _find_existing_file(filename)
            if path is None:
                return {"status": "error", "error": f"Arquivo '{filename}' não encontrado em nenhuma pasta conhecida ({_FOLDER_ALIAS_DISPLAY})."}

        content = path.read_text(encoding="utf-8")
        IOLogger.read(path.name, caller=caller)
        return {"status": "ok", "content": content}

    except Exception as e:
        IOLogger.error("read_file", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


def read_analysis_sections(filepath: str, sections: list[int], caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Lê seções específicas de um arquivo analise_tecnica_.md.

    O agente pode informar apenas o nome do arquivo ou prefixá-lo com um alias
    de pasta. Sem alias, busca automaticamente em ANALYSIS.

    Args:
        filepath: Nome do arquivo, com ou sem alias de pasta.
                  Exemplo: "analise_tecnica_HU-001.md"
                           "ANALYSIS/analise_tecnica_HU-001.md"
        sections: Lista de números das seções desejadas. Exemplo: [4, 8]
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).

    Returns:
        Sucesso:  {"status": "ok",      "content": "<seções concatenadas>"}
        Aviso:    {"status": "warning", "content": "<arquivo completo>",
                   "msg": "Não foi possível extrair as seções. Retornando arquivo completo."}
        Falha:    {"status": "error",   "error":   "<motivo>"}
    """
    try:
        import re

        resolved_dir, filename, error = _resolve_path_arg(filepath)
        if error:
            return {"status": "error", "error": error}
        resolved_dir = ANALYSIS_DIR # Sempre vai estar salvo em analysis_dir
        path = (resolved_dir / filename).resolve()

        content = path.read_text(encoding="utf-8")

        parts = re.split(r'<<<FIM_SECAO>>>', content)
        extracted = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            first_line = part.split('\n')[0].strip()
            match = re.match(r'^(\d+)\.', first_line)
            if match and int(match.group(1)) in sections:
                extracted.append(part)

        IOLogger.read(path.name + f" [sections:{sections}]", caller=caller)

        if not extracted:
            return {"status": "warning", "content": content, "msg": "Não foi possível extrair as seções solicitadas. Retornando arquivo completo."}

        return {"status": "ok", "content": "\n\n<<<FIM_SECAO>>>\n\n".join(extracted)}

    except Exception as e:
        IOLogger.error("read_analysis_sections", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


def read_multiple_files(filepaths: list[str], caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Lê o conteúdo de vários arquivos em uma única chamada.

    Cada item da lista pode ser um nome simples ou conter um alias de pasta.
    Arquivos sem alias são buscados automaticamente em ANALYSIS → DIAGRAMS → PROTOTYPE.
    Arquivos não encontrados ou inacessíveis são reportados individualmente sem
    impedir a leitura dos demais.

    Args:
        filepaths: Lista de nomes de arquivo, com ou sem alias de pasta.
                   Exemplo: ["relatorio_HU-001.md", "PROTOTYPE/login.html"]
        caller:    Nome do agente solicitante (usado apenas para rastreabilidade).

    Returns:
        Sucesso:  {"status": "ok", "contents": {
                      "<filepath>": {"status": "ok",    "content": "<conteúdo>"},
                      "<filepath>": {"status": "error", "error":   "<motivo>"},
                      ...
                  }}
        Falha:    {"status": "error", "error": "<motivo>"}
    """
    try:
        contents = {}
        for raw in filepaths:
            resolved_dir, filename, error = _resolve_path_arg(raw)

            if error:
                contents[raw] = {"status": "error", "error": error}
                continue

            if resolved_dir is not None:
                path = (resolved_dir / filename).resolve()
                if not _is_safe_path(path):
                    contents[raw] = {"status": "error", "error": "Acesso negado: caminho fora do projeto."}
                    continue
                if not path.exists():
                    contents[raw] = {"status": "error", "error": f"Arquivo '{filename}' não encontrado em {resolved_dir.name}."}
                    continue
            else:
                path = _find_existing_file(filename)
                if path is None:
                    contents[raw] = {"status": "error", "error": f"Arquivo '{filename}' não encontrado em nenhuma pasta conhecida."}
                    continue

            contents[raw] = {"status": "ok", "content": path.read_text(encoding="utf-8")}

        file_types = {Path(f).suffix.lstrip('.').lower() for f in filepaths if '.' in f}
        str_file_types = ", ".join(file_types) if file_types else "sem extensão"

        IOLogger.read(f"[batch: {len(filepaths)} files | types: {str_file_types}]", caller=caller)
        return {"status": "ok", "contents": contents}

    except Exception as e:
        IOLogger.error("read_multiple_files", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


def save_artifact(filename: str, content: str, caller: str | None = "unknown") -> dict:
    """
    Salva um arquivo em uma das pastas do projeto. Se o arquivo já existir,
    cria backup automático antes de sobrescrever.

    O agente pode prefixar o nome com um alias de pasta para controlar o destino.
    Sem alias, .html e global.css vão para PROTOTYPE; .mmd vai para DIAGRAMS;
    os demais vão para ANALYSIS.

    ⚠️  Sobrescreve o arquivo inteiro. Para acrescentar conteúdo, use append_artifact.
    ⚠️  Para corrigir uma seção específica de Markdown, use patch_section.
    ⚠️  Requer lock de escrita: adquira-o antes com acquire_lock (informando seu nome
        em caller) e libere-o com release_lock ao terminar. Escrita sem lock, ou com
        lock pertencente a outro especialista, é bloqueada.

    Args:
        filename: Nome do arquivo, com ou sem alias de pasta.
                  Exemplos: "relatorio_HU-001.md"
                            "ANALYSIS/relatorio_HU-001.md"
                            "PROTOTYPE/login.html"
        content:  Conteúdo completo do arquivo.
        caller:   Nome do agente solicitante (deve ser o detentor do lock do arquivo).

    Returns:
        dict com chaves: `status` ("ok" | "blocked" | "error"), `path` (str do
        path final em sucesso), `versioned_backup` (str do path do
        backup criado, se houve; None caso contrário), `timestamp`
        (ISO 8601). Em bloqueio ou erro: `error`, `filename`.
    """
    try:
        _ensure_dirs()

        resolved_dir, filename, error = _resolve_path_arg(filename)
        if error:
            return {"status": "error", "error": error, "filename": filename}

        denied = _check_write_permission(filename, caller)
        if denied:
            IOLogger.error("save_artifact", denied["error"], caller=caller)
            return denied

        if resolved_dir is not None:
            target_dir = resolved_dir
        elif filename.endswith(".html") or filename == "global.css":
            target_dir = PROTOTYPE_DIR
        elif filename.endswith(".mmd"):
            target_dir = DIAGRAMS_DIR
        else:
            target_dir = ANALYSIS_DIR

        destination = (target_dir / filename).resolve()
        if not _is_safe_path(destination):
            raise PermissionError("Segurança: Tentativa de escrita fora da área permitida.")

        destination.parent.mkdir(parents=True, exist_ok=True)

        versioned_backup = ""
        if destination.exists():
            backup_path = _next_version(destination)
            shutil.move(str(destination), str(backup_path))
            versioned_backup = str(backup_path)

        destination.write_text(content, encoding="utf-8")
        timestamp = datetime.now().isoformat()

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
    Copia um relatório aprovado para REPORT_DIR (diretório oficial permanente).

    Use somente quando o solicitante tiver alterado o status do relatório para "Aprovado"
    e pedir explicitamente a promoção. Nunca promova sem verificar o status antes.

    Restrições aplicadas automaticamente:
    - Apenas arquivos .md cujo nome contenha "relatorio" podem ser promovidos.
    - O arquivo deve conter "**Status:** Aprovado"; se ainda contiver "**Status:** Em análise",
      a promoção é bloqueada com status "blocked".
    - Diagramas .mmd, HTMLs, CSS e analise_tecnica_ nunca são promovidos.

    Args:
        filename: Nome do relatório. Apenas o nome — sem alias de pasta.
                  Exemplo: "relatorio_HU-001_HU-002.md"
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).

    Returns:
        dict com chaves: `status` ("ok" | "blocked" | "error"),
        `source`, `destination`, `timestamp` em sucesso; `reason` e
        `file` em "blocked"; `error` em "error".
    """
    try:
        raw_filename = Path(filename)
        if raw_filename.is_absolute() or ".." in raw_filename.parts:
            raise PermissionError("Segurança: Caminho inválido.")

        source = _find_existing_file(raw_filename.name)
        if source is None:
            return {"status": "error", "error": f"Arquivo '{filename}' não encontrado em nenhuma pasta conhecida."}

        if source.suffix != ".md":
            return {
                "status": "blocked",
                "reason": "Apenas relatórios .md podem ser promovidos. Diagramas .mmd permanecem em sua pasta de origem.",
                "file": filename,
            }

        if "relatorio" not in filename:
            return {
                "status": "blocked",
                "reason": "Apenas relatórios .md podem ser promovidos. A analise_tecnica_ permanece em sua pasta de origem.",
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
        destination = (OFFICIAL_DIR / raw_filename).resolve()
        if not _is_safe_path(destination):
            raise PermissionError("Segurança: Tentativa de escrita fora da área permitida.")

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


def list_design_files(filetype: str = "", folder: str = "", caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Lista os arquivos presentes em uma pasta do projeto.

    Sem `folder`, lista todas subpastas de design.
    Com `folder`, lista apenas a pasta indicada pelo alias.

    Backups (nomes com "_backup_") e o arquivo de log são ignorados automaticamente.

    Args:
        filetype: Extensão para filtrar, sem o ponto. Exemplos: "md", "html", "mmd".
                  Vazio = todos os arquivos.
        folder:   Alias da pasta a listar. Exemplos: "ANALYSIS", "PROTOTYPE", "DIAGRAMS".
                  Vazio = todas subpastas.
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).

    Returns:
        Sucesso:  {"status": "ok", "files": ["arquivo1.md", ...],
                   "folder": "<alias canônico da pasta listada>"}
        Falha:    {"status": "error", "error": "<motivo>"}
    """
    try:
        _ensure_dirs()

        # Resolve alias de pasta, se fornecido
        target_dir, error = _resolve_folder_alias(folder)
        if error:
            return {"status": "error", "error": error}

        def _list_dir(directory: Path) -> list[str]:
            if not directory.exists():
                return []
            return [
                f.name
                for f in sorted(directory.iterdir())
                if f.is_file()
                and f.name != LOG_FILENAME
                and BACKUP_PREFIX not in f.name
                and (not filetype or f.suffix == f".{filetype}")
            ]

        if target_dir is not None:
            # Pasta explícita
            files = _list_dir(target_dir)
            folder_label = target_dir.name.upper()
        else:
            # Comportamento padrão: todas as subpastas de design
            files = _list_dir(ANALYSIS_DIR) + _list_dir(DIAGRAMS_DIR) + _list_dir(PROTOTYPE_DIR) + _list_dir(REPORT_DIR)
            folder_label = "ANALYSIS+DIAGRAMS+PROTOTYPE+REPORT"

        IOLogger.read(f"[list:{filetype or 'all'} folder:{folder_label}]", caller=caller)
        return {
            "status": "ok",
            "files": sorted(list(set(files))),
            "folder": folder_label,
        }

    except Exception as e:
        IOLogger.error("list_design_files", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


def check_active_blocks(caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Verifica se há Doubt_Artifacts com status "Bloqueado" em DOUBT_DIR.

    Use após receber retomada de um bloqueio, para confirmar que todos os
    Doubt_Artifacts foram realmente resolvidos antes de prosseguir o pipeline.

    Um Doubt_Artifact é considerado bloqueado se seu conteúdo contiver:
    "**Status:** Bloqueado". Após resolução, o solicitante deve alterar essa
    linha para "**Status:** Resolvido".

    Args:
        caller: Nome do agente solicitante (usado apenas para rastreabilidade).

    Returns:
        Sem bloqueios: {"status": "ok", "has_blocks": false, "blocks": []}
        Com bloqueios: {"status": "ok", "has_blocks": true,
                        "blocks": [{"filename": "<nome>", "hu_id": "<HU_ID>"}, ...]}
        Falha:         {"status": "error", "error": "<motivo>"}
    """
    try:
        _ensure_dirs()
        blocks = []
        for f in sorted(DOUBT_DIR.iterdir()):
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


def clear_design_folder(caller: str | None = "unknown") -> bool:
    """
    Remove todos os arquivos de DESIGN e seus subdiretórios.
    A estrutura de pastas é preservada — apenas os arquivos são deletados.

    Use exclusivamente no início de um novo ciclo do pipeline.
    Esta operação é irreversível — não há backup dos arquivos removidos.

    ⚠️  Nunca chame esta função no meio de uma execução ativa do pipeline.

    Args:
        caller: Nome do agente solicitante (usado apenas para rastreabilidade).

    Returns:
        bool: True se todos os arquivos foram removidos com sucesso,
        False em caso de erro (ex: tentativa fora do diretório seguro, falha de I/O). Erros são registrados via IOLogger.
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

        _clear_recursive(DESIGN_DIR)
        IOLogger.erase(str(DESIGN_DIR), caller=caller)
        return True

    except Exception as e:
        IOLogger.error("ERASE", f"dir={DESIGN_DIR} | error={str(e)}", caller=caller)
        return False


def append_artifact(filename: str, content: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Adiciona conteúdo ao fim de um arquivo existente, sem apagar o que já está lá.
    Se o arquivo não existir, cria-o (comportamento idêntico ao save_artifact).

    O agente pode prefixar o nome com um alias de pasta. Sem alias, .html e
    global.css vão para PROTOTYPE; .mmd vai para DIAGRAMS; os demais vão para ANALYSIS.

    ⚠️  Não cria backup. Para substituir o arquivo inteiro, use save_artifact.
    ⚠️  Para corrigir uma seção já escrita, use patch_section.
    ⚠️  Requer lock de escrita: adquira-o antes com acquire_lock (informando seu nome
        em caller) e libere-o com release_lock ao terminar. Escrita sem lock, ou com
        lock pertencente a outro especialista, é bloqueada.

    Args:
        filename: Nome do arquivo, com ou sem alias de pasta.
                  Exemplos: "analise_tecnica_HU-001.md"
                            "PROTOTYPE/login.html"
        content:  Trecho a ser adicionado ao fim do arquivo.
        caller:   Nome do agente solicitante (deve ser o detentor do lock do arquivo).

    Returns:
        Sucesso:  {"status": "ok", "path": "<caminho>",
                   "bytes_total": <tamanho total após append>, "timestamp": "<ISO 8601>"}
        Bloqueio: {"status": "blocked", "error": "<motivo>", "filename": "<nome>"}
        Falha:    {"status": "error", "error": "<motivo>", "filename": "<nome>"}
    """
    try:
        _ensure_dirs()

        resolved_dir, filename, error = _resolve_path_arg(filename)
        if error:
            return {"status": "error", "error": error, "filename": filename}

        denied = _check_write_permission(filename, caller)
        if denied:
            IOLogger.error("append_artifact", denied["error"], caller=caller)
            return denied

        if resolved_dir is not None:
            target_dir = resolved_dir
        elif filename.endswith(".html") or filename == "global.css":
            target_dir = PROTOTYPE_DIR
        elif filename.endswith(".mmd"):
            target_dir = DIAGRAMS_DIR
        elif filename.startswith("relatorio_"):          # ← adicionar
            target_dir = REPORT_DIR                      # ← adicionar
        else:
            target_dir = ANALYSIS_DIR

        destination = (target_dir / filename).resolve()
        if not _is_safe_path(destination):
            raise PermissionError("Segurança: Tentativa de escrita fora da área permitida.")

        destination.parent.mkdir(parents=True, exist_ok=True)

        with destination.open("a", encoding="utf-8") as f:
            f.write(content)

        bytes_total = destination.stat().st_size
        timestamp = datetime.now().isoformat()

        IOLogger.append(filename, caller=caller, bytes_added=len(content.encode()), bytes_total=bytes_total)

        return {
            "status": "ok",
            "path": str(destination),
            "bytes_total": bytes_total,
            "timestamp": timestamp,
        }

    except Exception as e:
        IOLogger.error("append_artifact", str(e), caller=caller)
        return {"status": "error", "error": str(e), "filename": filename}


def append_architect_section(filename: str, content: str, caller: str | None = "design_architect") -> Dict[str, Any]:
    # A ideia inicial era fazer isso via prompt, mas estava instável e isso é essencial demais para ter qualquer instabilidade
    """
    Append exclusivo do design_architect.
    Adiciona conteúdo ao fim de um arquivo existente, sem apagar o que já está lá.
    Se o arquivo não existir, cria-o (comportamento idêntico ao save_artifact).

    ⚠️  Não cria backup. Para substituir o arquivo inteiro, use save_artifact.
    ⚠️  Para corrigir uma seção já escrita, use patch_section.

    Args:
        filename: Nome do arquivo, com ou sem alias de pasta.
                  Exemplos: "analise_tecnica_HU-001.md"
                            "PROTOTYPE/login.html"
        content:  Trecho a ser adicionado ao fim do arquivo.
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).

    Returns:
        Sucesso:  {"status": "ok", "path": "<caminho>",
                   "bytes_total": <tamanho total após append>, "timestamp": "<ISO 8601>"}
        Falha:    {"status": "error", "error": "<motivo>", "filename": "<nome>"}
    """
    # Remove token duplicado se o agente já incluiu (evita duplo marcador)
    normalized = content.rstrip("\n").removesuffix("<<<FIM_SECAO>>>").rstrip("\n")
    return append_artifact(filename, normalized + _SECTION_SEPARATOR, caller=caller)


def patch_section(filename: str, section_id: str, new_content: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Substitui uma seção específica de um arquivo Markdown, sem alterar as demais.

    O agente pode prefixar o nome com um alias de pasta. Sem alias, o sistema
    busca o arquivo automaticamente em ANALYSIS → DIAGRAMS → PROTOTYPE.

    A seção é identificada de duas formas (primeiro match vence):
    - Por número isolado: section_id="4" encontra a seção cuja primeira linha começa com "4." ou "4 ".
    - Por heading Markdown exato: section_id="## Título".

    ⚠️  section_id deve ser APENAS o número ("4") ou o heading exato — nunca "4. Título".
    ⚠️  new_content deve incluir o título da seção e terminar com "---".
    ⚠️  Um backup automático é criado antes de qualquer alteração.
    ⚠️  Requer lock de escrita: adquira-o antes com acquire_lock (informando seu nome
        em caller) e libere-o com release_lock ao terminar. Escrita sem lock, ou com
        lock pertencente a outro especialista, é bloqueada.

    Args:
        filename:    Nome do arquivo, com ou sem alias de pasta.
                     Exemplos: "analise_tecnica_HU-001.md"
                               "ANALYSIS/analise_tecnica_HU-001.md"
        section_id:  Número isolado ("4") ou heading Markdown exato ("## Título").
        new_content: Conteúdo completo da seção corrigida, incluindo título e "---" final.
        caller:      Nome do agente solicitante (deve ser o detentor do lock do arquivo).

    Returns:
        Sucesso:       {"status": "ok",      "path": "<caminho>", "section_found": true,
                        "backup": "<caminho do backup>", "timestamp": "<ISO 8601>"}
        Não encontrou: {"status": "warning", "section_found": false,
                        "error": "Seção '<id>' não encontrada. Arquivo não alterado.",
                        "hint": "Use read_analysis_sections para inspecionar os IDs disponíveis."}
        Falha:         {"status": "error",   "error": "<motivo>", "filename": "<nome>"}
    """
    try:
        import re
        _ensure_dirs()

        resolved_dir, filename, error = _resolve_path_arg(filename)
        if error:
            return {"status": "error", "error": error, "filename": filename}

        denied = _check_write_permission(filename, caller)
        if denied:
            IOLogger.error("patch_section", denied["error"], caller=caller)
            return denied

        if resolved_dir is not None:
            destination = (resolved_dir / filename).resolve()
            if not _is_safe_path(destination):
                raise PermissionError("Segurança: Tentativa de escrita fora da área permitida.")
            if not destination.exists():
                return {"status": "error", "error": f"Arquivo '{filename}' não encontrado em {resolved_dir.name}. Use save_artifact para criar."}
        else:
            destination = _find_existing_file(filename)
            if destination is None:
                return {"status": "error", "error": f"Arquivo '{filename}' não encontrado em nenhuma pasta conhecida. Use save_artifact para criar."}

        original = destination.read_text(encoding="utf-8")

        backup_path = _next_version(destination)
        shutil.copy2(str(destination), str(backup_path))

        parts = re.split(r'(?<=\n)---\n', original)
        section_found = False
        patched_parts = []

        for part in parts:
            stripped = part.strip()
            if not stripped:
                patched_parts.append(part)
                continue

            first_line = stripped.split("\n")[0].strip()
            matched_by_number = bool(section_id.isdigit() and re.match(rf'^{re.escape(section_id)}[.\s]', first_line))
            matched_by_heading = (first_line == section_id.strip())

            if not section_found and (matched_by_number or matched_by_heading):
                patched_parts.append(new_content.rstrip("\n") + "\n")
                section_found = True
            else:
                patched_parts.append(part)

        if not section_found:
            return {
                "status": "warning",
                "section_found": False,
                "error": f"Seção '{section_id}' não encontrada em '{filename}'. Arquivo não alterado.",
                "hint": "Use read_analysis_sections para inspecionar os IDs disponíveis.",
            }

        destination.write_text("---\n".join(patched_parts), encoding="utf-8")
        timestamp = datetime.now().isoformat()

        IOLogger.save(filename, caller=caller, backup=str(backup_path))

        return {
            "status": "ok",
            "path": str(destination),
            "section_found": True,
            "backup": str(backup_path),
            "timestamp": timestamp,
        }

    except Exception as e:
        IOLogger.error("patch_section", str(e), caller=caller)
        return {"status": "error", "error": str(e), "filename": filename}


# ──────────────────────────────────────────────────────────────────────────────
# Lock de Escrita (Ferramentas do Agente)
# ──────────────────────────────────────────────────────────────────────────────

def acquire_lock(filepath: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Adquire o lock de escrita exclusivo de um arquivo para o especialista `caller`.

    Enquanto o lock estiver ativo, somente o detentor pode modificar o arquivo
    (save_artifact, append_artifact e patch_section são bloqueados para os demais).
    A aquisição é atômica: dois especialistas nunca obtêm o mesmo lock ao mesmo
    tempo. Leituras nunca são afetadas por locks.

    Chamar novamente para um lock que você já possui é seguro (idempotente).

    ⚠️  Ao terminar as modificações, libere o lock com release_lock.

    Args:
        filepath: Nome do arquivo, com ou sem alias de pasta.
                  Exemplos: "analise_tecnica_HU-001.md"
                            "PROTOTYPE/login.html"
        caller:   OBRIGATÓRIO — nome do especialista que precisa escrever.
                  Exemplo: "mermaid_specialist".

    Returns:
        Sucesso:  {"status": "ok", "locked": true, "owner": "<caller>", "filepath": "<nome>"}
        Ocupado:  {"status": "blocked", "locked": true, "owner": "<outro>", "error": "<motivo>"}
        Falha:    {"status": "error", "error": "<motivo>"}
    """
    try:
        if not caller or caller.strip().lower() in ("", "unknown"):
            return {
                "status": "error",
                "error": "Identificação obrigatória: informe em `caller` o nome do especialista que precisa do lock.",
            }
        caller = caller.strip()

        _, filename, error = _resolve_path_arg(filepath)
        if error:
            return {"status": "error", "error": error}
        if not filename:
            return {"status": "error", "error": "Nome de arquivo vazio."}

        _ensure_dirs()
        lock_file = _lock_path(filename)
        payload = json.dumps(
            {"owner": caller, "filepath": filename, "acquired_at": datetime.now().isoformat()},
            ensure_ascii=False,
        )

        try:
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            current = _read_lock(lock_file) or {}
            owner = current.get("owner", "desconhecido")
            if owner == caller:
                return {
                    "status": "ok",
                    "locked": True,
                    "owner": caller,
                    "filepath": filename,
                    "msg": "Você já possuía o lock deste arquivo.",
                }
            return {
                "status": "blocked",
                "locked": True,
                "owner": owner,
                "filepath": filename,
                "error": (
                    f"Lock negado: '{filename}' já está com lock de '{owner}'. "
                    "Aguarde a liberação via release_lock pelo detentor."
                ),
            }

        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)

        IOLogger.lock(filename, caller=caller)
        return {"status": "ok", "locked": True, "owner": caller, "filepath": filename}

    except Exception as e:
        IOLogger.error("acquire_lock", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


def check_lock(filepath: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Verifica se um arquivo está com lock de escrita ativo e quem é o detentor.

    Operação apenas de consulta — não adquire nem libera o lock.

    Args:
        filepath: Nome do arquivo, com ou sem alias de pasta.
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).

    Returns:
        Livre:    {"status": "ok", "locked": false, "filepath": "<nome>"}
        Ocupado:  {"status": "ok", "locked": true, "owner": "<detentor>",
                   "acquired_at": "<ISO 8601>", "filepath": "<nome>"}
        Falha:    {"status": "error", "error": "<motivo>"}
    """
    try:
        _, filename, error = _resolve_path_arg(filepath)
        if error:
            return {"status": "error", "error": error}
        if not filename:
            return {"status": "error", "error": "Nome de arquivo vazio."}

        lock_info = _read_lock(_lock_path(filename))
        if lock_info is None:
            return {"status": "ok", "locked": False, "filepath": filename}
        return {
            "status": "ok",
            "locked": True,
            "owner": lock_info.get("owner", "desconhecido"),
            "acquired_at": lock_info.get("acquired_at", ""),
            "filepath": filename,
        }

    except Exception as e:
        IOLogger.error("check_lock", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


def release_lock(filepath: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Libera o lock de escrita de um arquivo. Somente o detentor pode liberar.

    Use sempre após concluir as modificações em um arquivo cujo lock você
    adquiriu com acquire_lock, para permitir que outros especialistas escrevam.

    Args:
        filepath: Nome do arquivo, com ou sem alias de pasta.
        caller:   OBRIGATÓRIO — nome do especialista que possui o lock.

    Returns:
        Sucesso:  {"status": "ok", "released": true, "filepath": "<nome>"}
        Já livre: {"status": "ok", "released": false, "filepath": "<nome>", "msg": "<aviso>"}
        Negado:   {"status": "blocked", "released": false, "owner": "<detentor>", "error": "<motivo>"}
        Falha:    {"status": "error", "error": "<motivo>"}
    """
    try:
        _, filename, error = _resolve_path_arg(filepath)
        if error:
            return {"status": "error", "error": error}
        if not filename:
            return {"status": "error", "error": "Nome de arquivo vazio."}

        lock_file = _lock_path(filename)
        lock_info = _read_lock(lock_file)
        if lock_info is None:
            return {
                "status": "ok",
                "released": False,
                "filepath": filename,
                "msg": "Nenhum lock ativo — o arquivo já estava livre.",
            }

        owner = lock_info.get("owner", "desconhecido")
        if owner != (caller or "").strip():
            return {
                "status": "blocked",
                "released": False,
                "owner": owner,
                "filepath": filename,
                "error": (
                    f"Liberação negada: o lock de '{filename}' pertence a '{owner}'. "
                    "Somente o detentor pode liberá-lo."
                ),
            }

        lock_file.unlink(missing_ok=True)
        IOLogger.unlock(filename, caller=caller)
        return {"status": "ok", "released": True, "filepath": filename}

    except Exception as e:
        IOLogger.error("release_lock", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


# ──────────────────────────────────────────────────────────────────────────────
# Mocks
# ──────────────────────────────────────────────────────────────────────────────

def list_versions(filepath: str) -> dict:
    """Mock: lista versões anteriores de um artefato."""
    return {"status": "ok", "versions": [], "filepath": filepath}