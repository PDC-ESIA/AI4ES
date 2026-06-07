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


# Ordem de busca usada quando o agente não especifica uma pasta.
# read_file e read_multiple_files percorrem essa lista e retornam o primeiro match.
_SEARCH_ORDER: list[Path] = [STAGING_DIR, PROTOTYPE_DIR, OFFICIAL_DIR]

# Mapa de aliases simbólicos → diretório canônico.
# Chaves sempre em minúsculas; a normalização é feita em _resolve_folder_alias.
_FOLDER_ALIASES: Dict[str, Path] = {
    # STAGING
    "staging":          STAGING_DIR,
    "staging_dir":      STAGING_DIR,
    "staging_folder":   STAGING_DIR,
    # PROTOTYPE (subpasta de staging)
    "prototype":        PROTOTYPE_DIR,
    "prototype_dir":    PROTOTYPE_DIR,
    "prototype_folder": PROTOTYPE_DIR,
    # ARTIFACTS / OFFICIAL
    "artifacts":        OFFICIAL_DIR,
    "artifacts_dir":    OFFICIAL_DIR,
    "artifacts_folder": OFFICIAL_DIR,
    "official":         OFFICIAL_DIR,
    "official_dir":     OFFICIAL_DIR,
}

# Nomes exibidos nas mensagens de erro — apenas os canônicos, legível para o agente.
_FOLDER_ALIAS_DISPLAY = (
    "STAGING, STAGING_DIR, STAGING_FOLDER, "
    "PROTOTYPE, PROTOTYPE_DIR, PROTOTYPE_FOLDER, "
    "ARTIFACTS, ARTIFACTS_DIR, ARTIFACTS_FOLDER, "
    "OFFICIAL, OFFICIAL_DIR"
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
        "STAGING/relatorio.md"   → ("STAGING",    "relatorio.md")
        "relatorio.md"           → ("",            "relatorio.md")
        "PROTOTYPE/"             → ("PROTOTYPE",   "")
        "spec/algo.md"           → ("spec",        "algo.md")
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
        "STAGING/relatorio.md"      → STAGING_DIR,   "relatorio.md",  sem erro
        "STAGING_FOLDER/login.html" → STAGING_DIR,   "login.html",    sem erro
        "PROTOTYPE/login.html"      → PROTOTYPE_DIR, "login.html",    sem erro
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
# Funções Públicas (Ferramentas do Agente)
# ──────────────────────────────────────────────────────────────────────────────

def read_file(filepath: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Lê e retorna o conteúdo completo de um arquivo.

    O agente pode informar apenas o nome do arquivo ou prefixá-lo com um alias
    de pasta. Quando nenhum alias é fornecido, o sistema busca automaticamente
    em STAGING → PROTOTYPE → ARTIFACTS e retorna o primeiro arquivo encontrado.

    Args:
        filepath: Nome do arquivo, com ou sem alias de pasta.
                  Exemplos: "relatorio_HU-001.md"
                            "STAGING/relatorio_HU-001.md"
                            "PROTOTYPE/login.html"
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).

    Returns:
        Sucesso:  {"status": "ok",    "content": "<conteúdo do arquivo>"}
        Falha:    {"status": "error", "error":   "<motivo>"}
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
    de pasta. Sem alias, busca automaticamente em STAGING → PROTOTYPE → ARTIFACTS.

    Args:
        filepath: Nome do arquivo, com ou sem alias de pasta.
                  Exemplo: "analise_tecnica_HU-001.md"
                           "STAGING/analise_tecnica_HU-001.md"
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

        if resolved_dir is not None:
            path = (resolved_dir / filename).resolve()
            if not _is_safe_path(path):
                return {"status": "error", "error": "Acesso negado: caminho fora do projeto."}
            if not path.exists():
                return {"status": "error", "error": f"Arquivo '{filename}' não encontrado em {resolved_dir.name}."}
        else:
            path = _find_existing_file(filename)
            if path is None:
                return {"status": "error", "error": f"Arquivo '{filename}' não encontrado em nenhuma pasta conhecida ({_FOLDER_ALIAS_DISPLAY})."}

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
    Arquivos sem alias são buscados automaticamente em STAGING → PROTOTYPE → ARTIFACTS.
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
    Sem alias, .html e global.css vão para PROTOTYPE; os demais vão para STAGING.

    ⚠️  Sobrescreve o arquivo inteiro. Para acrescentar conteúdo, use append_artifact.
    ⚠️  Para corrigir uma seção específica de Markdown, use patch_section.

    Args:
        filename: Nome do arquivo, com ou sem alias de pasta.
                  Exemplos: "relatorio_HU-001.md"
                            "STAGING/relatorio_HU-001.md"
                            "PROTOTYPE/login.html"
        content:  Conteúdo completo do arquivo.
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).

    Returns:
        Sucesso:  {"status": "ok", "path": "<caminho>",
                   "versioned_backup": "<backup ou vazio>", "timestamp": "<ISO 8601>"}
        Falha:    {"status": "error", "error": "<motivo>", "filename": "<nome>"}
    """
    try:
        _ensure_dirs()

        resolved_dir, filename, error = _resolve_path_arg(filename)
        if error:
            return {"status": "error", "error": error, "filename": filename}

        if resolved_dir is not None:
            target_dir = resolved_dir
        elif filename.endswith(".html") or filename == "global.css":
            target_dir = PROTOTYPE_DIR
        else:
            target_dir = STAGING_DIR

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
    Copia um relatório aprovado de STAGING para ARTIFACTS (diretório oficial permanente).

    Use somente quando o solicitante tiver alterado o status do relatório para "Aprovado"
    e pedir explicitamente a promoção. Nunca promova sem verificar o status antes.

    Restrições aplicadas automaticamente:
    - Apenas arquivos .md cujo nome contenha "relatorio" podem ser promovidos.
    - O arquivo deve conter "**Status:** Aprovado"; se ainda contiver "**Status:** Em análise",
      a promoção é bloqueada com status "blocked".
    - Diagramas .mmd, HTMLs, CSS e analise_tecnica_ nunca são promovidos.

    Args:
        filename: Nome do relatório em STAGING. Apenas o nome — sem alias de pasta.
                  Exemplo: "relatorio_HU-001_HU-002.md"
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).

    Returns:
        Sucesso:  {"status": "ok",      "source": "<origem>", "destination": "<destino>",
                   "timestamp": "<ISO 8601>"}
        Bloqueio: {"status": "blocked", "reason": "<motivo>", "file": "<nome>"}
        Falha:    {"status": "error",   "error":  "<motivo>"}
    """
    try:
        raw_filename = Path(filename)
        if raw_filename.is_absolute() or ".." in raw_filename.parts:
            raise PermissionError("Segurança: Caminho inválido.")

        source = (STAGING_DIR / raw_filename).resolve()
        if not _is_safe_path(source):
            raise PermissionError("Segurança: Tentativa de escrita fora da área permitida.")

        if not source.exists():
            return {"status": "error", "error": f"Arquivo '{filename}' não encontrado em STAGING."}

        if source.suffix != ".md":
            return {
                "status": "blocked",
                "reason": "Apenas relatórios .md podem ser promovidos. Diagramas .mmd permanecem em STAGING.",
                "file": filename,
            }

        if "relatorio" not in filename:
            return {
                "status": "blocked",
                "reason": "Apenas relatórios .md podem ser promovidos. A analise_tecnica_ permanece em STAGING.",
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


def list_staging_files(filetype: str = "", folder: str = "", caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Lista os arquivos presentes em uma pasta do projeto.

    Sem `folder`, lista STAGING e PROTOTYPE juntos (comportamento original).
    Com `folder`, lista apenas a pasta indicada pelo alias.

    Backups (nomes com "_backup_") e o arquivo de log são excluídos automaticamente.

    Args:
        filetype: Extensão para filtrar, sem o ponto. Exemplos: "md", "html", "mmd".
                  Vazio = todos os arquivos.
        folder:   Alias da pasta a listar. Exemplos: "STAGING", "PROTOTYPE", "ARTIFACTS".
                  Vazio = STAGING + PROTOTYPE (comportamento padrão).
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
            # Comportamento padrão: STAGING + PROTOTYPE
            files = _list_dir(STAGING_DIR) + _list_dir(PROTOTYPE_DIR)
            folder_label = "STAGING+PROTOTYPE"

        IOLogger.read(f"[list:{filetype or 'all'} folder:{folder_label}]", caller=caller)
        return {
            "status": "ok",
            "files": sorted(list(set(files))),
            "folder": folder_label,
        }

    except Exception as e:
        IOLogger.error("list_staging_files", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


def check_active_blocks(caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Verifica se há Doubt_Artifacts com status "Bloqueado" em STAGING.

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
    Remove todos os arquivos de STAGING e seus subdiretórios (incluindo PROTOTYPE).
    A estrutura de pastas é preservada — apenas os arquivos são deletados.

    Use exclusivamente no início de um novo ciclo do pipeline.
    Esta operação é irreversível — não há backup dos arquivos removidos.

    ⚠️  Nunca chame esta função no meio de uma execução ativa do pipeline.

    Args:
        caller: Nome do agente solicitante (usado apenas para rastreabilidade).

    Returns:
        True  → todos os arquivos foram removidos com sucesso.
        False → ocorreu um erro durante a limpeza (detalhes no log de operações).
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


def append_artifact(filename: str, content: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Adiciona conteúdo ao fim de um arquivo existente, sem apagar o que já está lá.
    Se o arquivo não existir, cria-o (comportamento idêntico ao save_artifact).

    O agente pode prefixar o nome com um alias de pasta. Sem alias, .html e
    global.css vão para PROTOTYPE; os demais vão para STAGING.

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
    try:
        _ensure_dirs()

        resolved_dir, filename, error = _resolve_path_arg(filename)
        if error:
            return {"status": "error", "error": error, "filename": filename}

        if resolved_dir is not None:
            target_dir = resolved_dir
        elif filename.endswith(".html") or filename == "global.css":
            target_dir = PROTOTYPE_DIR
        else:
            target_dir = STAGING_DIR

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


def patch_section(filename: str, section_id: str, new_content: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Substitui uma seção específica de um arquivo Markdown, sem alterar as demais.

    O agente pode prefixar o nome com um alias de pasta. Sem alias, o sistema
    busca o arquivo automaticamente em STAGING → PROTOTYPE → ARTIFACTS.

    A seção é identificada de duas formas (primeiro match vence):
    - Por número isolado: section_id="4" encontra a seção cuja primeira linha começa com "4." ou "4 ".
    - Por heading Markdown exato: section_id="## Título".

    ⚠️  section_id deve ser APENAS o número ("4") ou o heading exato — nunca "4. Título".
    ⚠️  new_content deve incluir o título da seção e terminar com "---".
    ⚠️  Um backup automático é criado antes de qualquer alteração.

    Args:
        filename:    Nome do arquivo, com ou sem alias de pasta.
                     Exemplos: "analise_tecnica_HU-001.md"
                               "STAGING/analise_tecnica_HU-001.md"
        section_id:  Número isolado ("4") ou heading Markdown exato ("## Título").
        new_content: Conteúdo completo da seção corrigida, incluindo título e "---" final.
        caller:      Nome do agente solicitante (usado apenas para rastreabilidade).

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