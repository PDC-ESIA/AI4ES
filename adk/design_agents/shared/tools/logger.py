"""
io_logger.py
────────────
Responsabilidade exclusiva: registrar operações do Agente IO em disco.

Separação de papéis:
    filesystem.py  →  persistência de artefatos (save, promote, read, list…)
    io_logger.py   →  auditoria de operações (quem leu/escreveu/promoveu o quê)

Uso:
    from .io_logger import IOLogger

    IOLogger.read("analise_HU-001.md")
    IOLogger.save("diagrama_HU-001.mmd", backup="diagrama_HU-001_backup_20260426_120000.mmd")
    IOLogger.promote("relatorio_HU-001.md")
    IOLogger.error("save_artifact", "Permissão negada ao gravar em staging/")
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


# ──────────────────────────────────────────────────────────────────────────────
# API pública
# ──────────────────────────────────────────────────────────────────────────────

class IOLogger:
    """Métodos estáticos, um por tipo de operação do Agente IO."""

    @staticmethod
    def read(filename: str) -> None:
        """Registrado apenas quando LOG_DETAIL == 'HIGH'."""
        if LOG_DETAIL == "HIGH":
            _write(f"[{_now()}] READ    | file={filename}\n")

    @staticmethod
    def save(filename: str, *, backup: str | None = None) -> None:
        entry = f"[{_now()}] SAVE    | file={filename}"
        if backup:
            entry += f" | backup={backup}"
        _write(entry + "\n")

    @staticmethod
    def promote(filename: str) -> None:
        _write(f"[{_now()}] PROMOTE | file={filename} | from=staging | to=artifacts\n")

    @staticmethod
    def error(operation: str, detail: str) -> None:
        """Erros são sempre registrados, independente de LOG_DETAIL."""
        _write(f"[{_now()}] ERROR   | op={operation} | detail={detail}\n")