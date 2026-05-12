"""Helpers para registrar arquivos gerados na aba Artifacts do ADK Web."""

from pathlib import Path
from typing import Any

from google.genai import types


def _artifact_filename(caminho: str | Path) -> str:
    path = Path(caminho)
    if path.is_absolute():
        try:
            path = path.resolve().relative_to(Path.cwd().resolve())
        except ValueError:
            path = Path(path.name)

    return path.as_posix()


async def registrar_markdown_artifact(
    tool_context: Any | None,
    caminho: str | Path,
    conteudo_md: str,
) -> dict:
    """Registra Markdown no ArtifactService da sessão ADK, quando disponível."""
    filename = _artifact_filename(caminho)

    if tool_context is None:
        return {
            "registrado": False,
            "filename": filename,
            "versao": None,
            "erro": "tool_context indisponível fora de uma execução ADK.",
        }

    try:
        versao = await tool_context.save_artifact(
            filename=filename,
            artifact=types.Part.from_bytes(
                data=conteudo_md.encode("utf-8"),
                mime_type="text/markdown",
            ),
        )
        return {
            "registrado": True,
            "filename": filename,
            "versao": versao,
            "erro": None,
        }
    except Exception as exc:
        return {
            "registrado": False,
            "filename": filename,
            "versao": None,
            "erro": str(exc),
        }
