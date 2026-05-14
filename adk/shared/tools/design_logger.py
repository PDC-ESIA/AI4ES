"""
design_logger.py
────────────
Responsabilidade exclusiva: registrar operações do Agente IO em disco.

Separação de papéis:
    design_filesystem.py  →  persistência de artefatos (save, promote, read, list…)
    design_logger.py      →  auditoria de operações (quem leu/escreveu/promoveu o quê)

Uso:
    from .design_logger import IOLogger

    IOLogger.read("analise_HU-001.md", caller="mermaid_specialist")
    IOLogger.save("diagrama_HU-001.mmd", caller="mermaid_specialist", backup="..._backup_.mmd")
    IOLogger.promote("relatorio_HU-001.md", caller="orchestrator")
    IOLogger.error("save_artifact", "Permissão negada ao gravar em staging/", caller="design_architect")
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

# "DEFAULT" → apenas SAVE, PROMOTE e ERROR são registrados.
# "HIGH"    → READ também é registrado.
LOG_DETAIL: str = "HIGH"

_LOG_FILE = Path("temp/staging/io_operations.log")

def _write(entry: str) -> None:
    """Abre o log em modo append e escreve uma entrada já formatada."""
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(entry)


def _now() -> str:
    return datetime.now().isoformat()


def _caller_tag(caller: str | None) -> str:
    return f" | caller={caller}" if caller else ""

def _make_string(operation: str, filename: str, *, caller: str , backup: str = "", detail: str = "") -> str:
    if backup:
        backup = "\tbackup: " + backup
    return f"[{_now()}] {operation:<6} {_caller_tag(caller):<32} | {detail}{filename}{backup}\n"


# ──────────────────────────────────────────────────────────────────────────────
# API pública
# ──────────────────────────────────────────────────────────────────────────────

class IOLogger:
    """Métodos estáticos, um por tipo de operação do Agente IO."""

    @staticmethod
    def read(filename: str, *, caller: str | None = None) -> None:
        """Registrado apenas quando LOG_DETAIL == 'HIGH'."""
        if LOG_DETAIL == "HIGH":
            _write(_make_string("READ", filename, caller=caller))

    @staticmethod
    def save(filename: str, *, caller: str | None = None, backup: str | None = "") -> None:
        _write(_make_string("SAVE", filename, caller=caller, backup=backup))

    @staticmethod
    def promote(filename: str, *, caller: str | None = None) -> None:
        _write(_make_string("PRMT", filename, caller=caller))

    @staticmethod
    def erase(directory: str, *, caller: str | None = None) -> None:
        _write(_make_string("ERASE", directory, caller=caller, detail="dir "))

    @staticmethod
    def error(operation: str, detail: str, *, caller: str | None = None) -> None:
        """Erros são sempre registrados, independente de LOG_DETAIL."""
        _write(_make_string("ERROR", operation, caller=caller, detail=detail))

    @staticmethod
    def copy(source_path: str, destination_filename: str, *, caller: str | None = None) -> None:
        _write(_make_string("COPY", source_path, caller=caller, detail=destination_filename))
