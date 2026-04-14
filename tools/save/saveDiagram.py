"""
shared/tools/filesystem.py
──────────────────────────
Save Artifact Tool — ferramenta determinística para o File Governance Agent.
 
Responsabilidades:
    • Path Sanitization  → impede escrita fora dos diretórios permitidos
    • Versionamento      → nunca sobrescreve; cria <nome>_v<n>.<ext>
    • File Lock          → TTL 300 s, backoff exponencial (máx. 3 tentativas)
    • Staging            → escrita sempre em /temp/staging antes da promoção
    • Promoção           → move staging → destino oficial após aprovação
    • Log de operações   → registro estruturado de cada passo
 
Integração ADK:
    Cada função pública é decorada com @tool e pode ser passada diretamente
    para o LlmAgent via tools=[...].
"""
 
from __future__ import annotations
 
import json
import logging
import os
import re
import shutil
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Compatibilidade com ADK (importação opcional para testes locais) 
try:
    from google.adk.tools import tool  # type: ignore
except ImportError:
    def tool(fn):                       # shim local para testes sem ADK
        return fn
    
    
# Raiz do repositório (pode ser sobrescrita via variável de ambiente)
_REPO_ROOT = Path(os.environ.get("REPO_ROOT", Path.cwd())).resolve()
 
# Diretórios permitidos para escrita (caminhos relativos à raiz do repo)
ALLOWED_DIRS: list[str] = [
    "docs/Time_2_Design/architecture",
    "docs/Time_2_Design/design",
    "docs/Time_2_Design/diagrams",
    "docs/Time_2_Design/specs",
    "temp/staging",
]
 
# Extensões mapeadas a subdiretórios padrão dentro de docs/
EXTENSION_DIR_MAP: dict[str, str] = {
    ".puml": "docs/Time_2_Design/diagrams",
    ".mmd":  "docs/Time_2_Design/diagrams",
    ".md":   "docs/Time_2_Design/architecture",
}
 
# Diretório de staging (sempre relativo à raiz)
STAGING_DIR = _REPO_ROOT / "temp" / "staging"
 
# Padrões que NUNCA podem aparecer no caminho resolvido
_BLOCKED_PATTERNS: list[re.Pattern] = [
    re.compile(r"(^|/)\.env($|/)"),
    re.compile(r"(^|/)\.git($|/)"),
    re.compile(r"(^|/)(src|app|config|secrets|credentials)($|/)"),
    re.compile(r"\.\.(\\|/)"),           # path traversal
    re.compile(r"(^|/)__pycache__($|/)"),
]
 
# Lock store em memória (para testes/single-process). Em produção,
# substitua por um backend distribuído (Redis, DynamoDB…).
_LOCK_STORE: dict[str, dict] = {}
_LOCK_MUTEX = threading.Lock()
 
LOCK_TTL_SECONDS   = 300
LOCK_BACKOFF_BASE  = 1.5     # segundos
LOCK_MAX_ATTEMPTS  = 3
 
logger = logging.getLogger("save_artifact_tool")
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Tipos internos
# ─────────────────────────────────────────────────────────────────────────────
 
@dataclass
class ToolResult:
    success: bool
    message: str
    data:    dict = field(default_factory=dict)
 
    def to_dict(self) -> dict:
        return {"success": self.success, "message": self.message, **self.data}
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Path Sanitization
# ─────────────────────────────────────────────────────────────────────────────
 
class PathSanitizationError(ValueError):
    pass
 
 
def _resolve_and_sanitize(relative_path: str) -> Path:
    """
    Resolve o caminho relativo contra a raiz do repo e valida:
      1. O caminho não contém segmentos bloqueados.
      2. O caminho resolvido está dentro de um ALLOWED_DIR.
    Lança PathSanitizationError se qualquer verificação falhar.
    """
    # Normaliza separadores e remove espaços
    clean = relative_path.strip().replace("\\", "/")
 
    # 1. Bloqueio por padrão (antes de resolver)
    for pattern in _BLOCKED_PATTERNS:
        if pattern.search(clean):
            raise PathSanitizationError(
                f"[BLOQUEADO] Caminho contém segmento proibido: '{clean}' "
                f"(padrão: {pattern.pattern})"
            )
 
    # 2. Resolve completamente
    resolved = (_REPO_ROOT / clean).resolve()
 
    # 3. Confirma que está dentro da raiz
    try:
        resolved.relative_to(_REPO_ROOT)
    except ValueError:
        raise PathSanitizationError(
            f"[BLOQUEADO] Path traversal detectado: '{clean}' resolve para '{resolved}', "
            f"fora de '{_REPO_ROOT}'"
        )
 
    # 4. Confirma que está em um diretório permitido
    rel_from_root = resolved.relative_to(_REPO_ROOT)
    allowed = any(
        str(rel_from_root).startswith(allowed_dir.replace("/", os.sep))
        for allowed_dir in ALLOWED_DIRS
    )
    if not allowed:
        raise PathSanitizationError(
            f"[BLOQUEADO] Diretório não permitido: '{rel_from_root}'. "
            f"Diretórios permitidos: {ALLOWED_DIRS}"
        )
 
    return resolved
 
 
def _auto_destination(filename: str) -> str:
    """
    Retorna o caminho relativo padrão baseado na extensão do arquivo.
    Usado quando o chamador não especifica um subdiretório.
    """
    ext = Path(filename).suffix.lower()
    base_dir = EXTENSION_DIR_MAP.get(ext, "docs/architecture")
    return f"{base_dir}/{filename}"
 
 
# ─────────────────────────────────────────────────────────────────────────────
# File Lock
# ─────────────────────────────────────────────────────────────────────────────
 
def _lock_key(path: Path) -> str:
    return str(path.resolve())
 
 
def _is_lock_expired(lock_entry: dict) -> bool:
    return (time.time() - lock_entry["acquired_at"]) > LOCK_TTL_SECONDS
 
 
@tool
def check_lock(relative_path: str) -> dict:
    """
    Verifica se um arquivo está bloqueado.
 
    Parâmetros
    ----------
    relative_path : str
        Caminho relativo ao repo (ex: "docs/diagrams/arch.puml").
 
    Retorno
    -------
    dict  { success, message, locked, owner, expires_in_seconds }
    """
    try:
        resolved = _resolve_and_sanitize(relative_path)
    except PathSanitizationError as e:
        return ToolResult(False, str(e)).to_dict()
 
    key = _lock_key(resolved)
    with _LOCK_MUTEX:
        entry = _LOCK_STORE.get(key)
        if entry and not _is_lock_expired(entry):
            expires_in = int(LOCK_TTL_SECONDS - (time.time() - entry["acquired_at"]))
            return ToolResult(
                True,
                f"Arquivo bloqueado por '{entry['owner']}'. Expira em {expires_in}s.",
                {"locked": True, "owner": entry["owner"], "expires_in_seconds": expires_in},
            ).to_dict()
 
        # Lock expirado ou inexistente
        if entry:
            del _LOCK_STORE[key]   # limpa lock expirado
        return ToolResult(
            True, "Arquivo livre.", {"locked": False, "owner": None, "expires_in_seconds": 0}
        ).to_dict()
 
 
def _acquire_lock(resolved: Path, owner: str = "io_agent") -> bool:
    """Tenta adquirir o lock com backoff exponencial. Retorna True se bem-sucedido."""
    key = _lock_key(resolved)
    for attempt in range(LOCK_MAX_ATTEMPTS):
        with _LOCK_MUTEX:
            entry = _LOCK_STORE.get(key)
            if not entry or _is_lock_expired(entry):
                _LOCK_STORE[key] = {"owner": owner, "acquired_at": time.time()}
                logger.info("Lock adquirido: %s (owner=%s)", resolved.name, owner)
                return True
        wait = LOCK_BACKOFF_BASE ** attempt
        logger.warning("Lock ocupado. Tentativa %d/%d. Aguardando %.1fs…", attempt + 1, LOCK_MAX_ATTEMPTS, wait)
        time.sleep(wait)
    return False
 
 
@tool
def release_lock(relative_path: str) -> dict:
    """
    Libera o lock de um arquivo.
 
    Parâmetros
    ----------
    relative_path : str
        Caminho relativo ao repo.
 
    Retorno
    -------
    dict  { success, message }
    """
    try:
        resolved = _resolve_and_sanitize(relative_path)
    except PathSanitizationError as e:
        return ToolResult(False, str(e)).to_dict()
 
    key = _lock_key(resolved)
    with _LOCK_MUTEX:
        if key in _LOCK_STORE:
            del _LOCK_STORE[key]
            logger.info("Lock liberado: %s", resolved.name)
            return ToolResult(True, f"Lock liberado: {resolved.name}").to_dict()
        return ToolResult(True, "Arquivo não estava bloqueado.").to_dict()
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Versionamento
# ─────────────────────────────────────────────────────────────────────────────
 
def _next_version_path(target: Path) -> Path:
    """
    Dado docs/diagrams/arch.puml já existente, retorna
    docs/diagrams/arch_v2.puml (ou _v3, _v4…).
    """
    stem = target.stem
    suffix = target.suffix
    parent = target.parent
 
    # Detecta se já tem sufixo _vN
    version_match = re.match(r"^(.+)_v(\d+)$", stem)
    if version_match:
        base, n = version_match.group(1), int(version_match.group(2))
    else:
        base, n = stem, 1
 
    # Incrementa até encontrar nome livre
    while True:
        n += 1
        candidate = parent / f"{base}_v{n}{suffix}"
        if not candidate.exists():
            return candidate
 
 
@tool
def list_versions(relative_path: str) -> dict:
    """
    Lista todas as versões de um artefato.
 
    Parâmetros
    ----------
    relative_path : str
        Caminho relativo ao repo do arquivo base (sem sufixo _vN).
 
    Retorno
    -------
    dict  { success, message, versions: List[str] }
    """
    try:
        resolved = _resolve_and_sanitize(relative_path)
    except PathSanitizationError as e:
        return ToolResult(False, str(e)).to_dict()
 
    stem   = re.sub(r"_v\d+$", "", resolved.stem)
    suffix = resolved.suffix
    parent = resolved.parent
 
    versions = sorted(parent.glob(f"{stem}*{suffix}"))
    names    = [str(v.relative_to(_REPO_ROOT)) for v in versions]
    return ToolResult(
        True, f"{len(names)} versão(ões) encontrada(s).", {"versions": names}
    ).to_dict()
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Save Artifact (escrita em staging)
# ─────────────────────────────────────────────────────────────────────────────
 
@tool
def save_artifact(
    content:       str,
    filename:      str,
    relative_path: Optional[str] = None,
    approved_by:   Optional[str] = None,
) -> dict:
    """
    Persiste um artefato em /temp/staging com versionamento automático.
 
    O arquivo PERMANECE em staging até que promote_artifact() seja chamado
    com aprovação registrada.
 
    Parâmetros
    ----------
    content       : str           Conteúdo bruto do artefato.
    filename      : str           Nome do arquivo (ex: "arch.puml").
    relative_path : str | None    Caminho relativo ao destino final (opcional).
                                  Se omitido, usa mapeamento automático por extensão.
    approved_by   : str | None    Identificador de quem aprovou (ex: "human:joao").
                                  Obrigatório apenas na promoção, não aqui.
 
    Retorno
    -------
    dict  { success, message, staging_path, version }
    """
    # 0. Guarda de conteúdo vazio
    if not content or not content.strip():
        return ToolResult(
            False,
            "Conteúdo vazio rejeitado. O Agente Arquiteto deve gerar conteúdo não-vazio.",
        ).to_dict()
 
    # 1. Destino final (para validar permissões antecipadamente)
    dest_relative = relative_path or _auto_destination(filename)
    try:
        _resolve_and_sanitize(dest_relative)   # valida destino antes de qualquer I/O
    except PathSanitizationError as e:
        return ToolResult(False, str(e)).to_dict()
 
    # 2. Caminho de staging
    staging_path = STAGING_DIR / filename
    staging_path.parent.mkdir(parents=True, exist_ok=True)
 
    # 3. Adquire lock no staging
    if not _acquire_lock(staging_path):
        return ToolResult(
            False,
            f"Não foi possível adquirir lock para '{filename}' após {LOCK_MAX_ATTEMPTS} tentativas.",
        ).to_dict()
 
    version = "v1"
    try:
        # 4. Versionamento no staging (se já existe)
        if staging_path.exists():
            versioned = _next_version_path(staging_path)
            shutil.copy2(staging_path, versioned)
            version = f"v{re.search(r'_v(\d+)', versioned.name).group(1)}" # type: ignore
            logger.info("Versão anterior preservada: %s", versioned.name)
 
        # 5. Escreve conteúdo novo
        staging_path.write_text(content, encoding="utf-8")
 
        # 6. Grava metadados de staging (usado na promoção)
        meta = {
            "filename":      filename,
            "dest_relative": dest_relative,
            "approved_by":   approved_by,
            "staged_at":     datetime.now(timezone.utc).isoformat(),
            "version":       version,
        }
        meta_path = staging_path.with_suffix(staging_path.suffix + ".meta.json")
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
 
        logger.info("Artefato salvo em staging: %s (%s)", staging_path.name, version)
        return ToolResult(
            True,
            f"Artefato '{filename}' salvo em staging ({version}). Aguardando aprovação.",
            {"staging_path": str(staging_path.relative_to(_REPO_ROOT)), "version": version},
        ).to_dict()
 
    except OSError as exc:
        logger.error("Falha de I/O ao salvar '%s': %s", filename, exc)
        return ToolResult(False, f"Erro de I/O: {exc}").to_dict()
 
    finally:
        release_lock(str(staging_path.relative_to(_REPO_ROOT)))
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Promote Artifact (staging → destino oficial)
# ─────────────────────────────────────────────────────────────────────────────
 
@tool
def promote_artifact(filename: str, approved_by: str) -> dict:
    """
    Move um artefato de /temp/staging para o diretório oficial.
    Só executa se approved_by estiver preenchido.
 
    Parâmetros
    ----------
    filename    : str   Nome do arquivo em staging (ex: "arch.puml").
    approved_by : str   Identificador de quem aprovou (obrigatório).
 
    Retorno
    -------
    dict  { success, message, final_path, version }
    """
    # 1. Aprovação obrigatória
    if not approved_by or not approved_by.strip():
        return ToolResult(
            False,
            "Promoção bloqueada: campo 'approved_by' está vazio. "
            "Preencha com o identificador de aprovação antes de promover.",
        ).to_dict()
 
    # 2. Arquivo de staging deve existir
    staging_path = STAGING_DIR / filename
    if not staging_path.exists():
        return ToolResult(
            False,
            f"Arquivo '{filename}' não encontrado em staging. "
            "Execute save_artifact() antes de promover.",
        ).to_dict()
 
    # 3. Lê metadados de staging
    meta_path = staging_path.with_suffix(staging_path.suffix + ".meta.json")
    if not meta_path.exists():
        return ToolResult(
            False,
            f"Metadados de staging ausentes para '{filename}'. "
            "O arquivo pode ter sido salvo sem usar save_artifact().",
        ).to_dict()
 
    meta: dict = json.loads(meta_path.read_text(encoding="utf-8"))
    dest_relative: str = meta["dest_relative"]
 
    # 4. Valida destino final
    try:
        dest_path = _resolve_and_sanitize(dest_relative)
    except PathSanitizationError as e:
        return ToolResult(False, str(e)).to_dict()
 
    # 5. Adquire lock no destino
    if not _acquire_lock(dest_path):
        return ToolResult(
            False,
            f"Não foi possível adquirir lock no destino '{dest_relative}'.",
        ).to_dict()
 
    version = "v1"
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
 
        # 6. Versionamento no destino
        if dest_path.exists():
            versioned = _next_version_path(dest_path)
            shutil.copy2(dest_path, versioned)
            match = re.search(r"_v(\d+)", versioned.name)
            version = f"v{match.group(1)}" if match else "v?"
            logger.info("Versão anterior arquivada em destino: %s", versioned.name)
 
        # 7. Copia staging → destino
        shutil.copy2(staging_path, dest_path)
 
        # 8. Atualiza metadados com aprovação e timestamp de promoção
        meta.update({
            "approved_by":  approved_by,
            "promoted_at":  datetime.now(timezone.utc).isoformat(),
            "final_path":   dest_relative,
        })
        meta_dest = dest_path.with_suffix(dest_path.suffix + ".meta.json")
        meta_dest.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
 
        # 9. Remove staging
        staging_path.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)
 
        logger.info(
            "Artefato promovido: %s → %s (aprovado por: %s)",
            filename, dest_relative, approved_by,
        )
        return ToolResult(
            True,
            f"'{filename}' promovido com sucesso para '{dest_relative}' (aprovado por: {approved_by}).",
            {"final_path": dest_relative, "version": version, "approved_by": approved_by},
        ).to_dict()
 
    except OSError as exc:
        logger.error("Falha de I/O na promoção de '%s': %s", filename, exc)
        return ToolResult(False, f"Erro de I/O na promoção: {exc}").to_dict()
 
    finally:
        release_lock(dest_relative)