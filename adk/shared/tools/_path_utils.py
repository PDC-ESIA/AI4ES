"""Helper de resolução de caminho compartilhado entre tools de filesystem.

Usado tanto pelas tools do fluxo de codificação
(shared/tools/coding_review/filesystem.py) quanto pelas tools de
requisitos/workspace que permanecem em shared/tools/filesystem.py.
"""

from pathlib import Path
from typing import Optional


def _resolver_caminho(caminho: str, base_dir: Optional[str] = None) -> Path:
    """Resolve caminho relativo ao base_dir (se informado) com proteção anti-traversal.

    Args:
        caminho: Caminho informado pelo agente.
        base_dir: Diretório base do agente no workspace (opcional).

    Returns:
        Path resolvido e validado.

    Raises:
        ValueError: Se o caminho tenta escapar do base_dir (absolute ou ..).
    """
    if base_dir is None:
        return Path(caminho)

    base = Path(base_dir).resolve()
    rel = Path(caminho)

    if rel.is_absolute():
        raise ValueError(
            f"Caminho absoluto não permitido com base_dir: '{caminho}'. "
            f"Use caminhos relativos ao seu diretório de trabalho."
        )

    if ".." in rel.parts:
        raise ValueError(
            f"Path traversal não permitido: '{caminho}'. "
            f"Não use '..' no caminho."
        )

    return base / rel
