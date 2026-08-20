"""I/O do subagente receive_requirements: paths de workspace, slugs e persistência de arquivos/doubt artifacts."""

import base64
import re
from datetime import datetime, timezone
from pathlib import Path

from shared.workspace import get_agent_workspace


def _tests_dir(workspace_agent: str = "receive_requirements") -> Path:
    """workspace_output/tests/<agent>/ resolvido em runtime.

    Centraliza o destino dos arquivos pytest gerados pelo subagente.
    Resolvido em runtime para respeitar WORKSPACE_OUTPUT_DIR env var.
    """
    return get_agent_workspace(workspace_agent)


def _doubt_dir(workspace_agent: str = "receive_requirements") -> Path:
    """Sibling 'doubt_artifacts' dentro do diretório de testes."""
    return _tests_dir(workspace_agent) / "doubt_artifacts"


async def _gerar_doubt_artifact(
    id_artefato: str,
    motivo: str,
    workspace_agent: str = "receive_requirements",
    agent_label: str = "qa_agent",
) -> str:
    """Gera arquivo de doubt artifact para artefato bloqueado.

    Args:
        id_artefato: Identificador do artefato.
        motivo: Motivo do bloqueio.
        workspace_agent: Chave do workspace do subagente que chamou.
        agent_label: Rótulo do agente registrado no artefato.

    Returns:
        str: Caminho do arquivo gerado.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    _doubt_dir(workspace_agent).mkdir(parents=True, exist_ok=True)

    nome = f"Doubt_Artifact_{id_artefato}_{timestamp}.md"
    caminho = _doubt_dir(workspace_agent) / nome

    conteudo = f"""# Doubt Artifact — QA Agent

**ID do Artefato:** {id_artefato}
**Data/Hora:** {timestamp}
**Agente:** {agent_label}
**Status:** BLOQUEADO — aguardando intervenção humana

---

## Descrição do Bloqueio

{motivo}

## O que é necessário para continuar

[ Preencher após intervenção ]

## Resolução

- **Resolvido por:** [ Preencher ]
- **Data:** [ Preencher ]
- **Ação tomada:** [ Preencher ]
"""
    caminho.write_text(conteudo, encoding="utf-8")
    return str(caminho)


def _slugify(texto: str) -> str:
    """Normaliza texto para uso em nomes de arquivo.

    Args:
        texto: Texto a normalizar.

    Returns:
        str: Slug seguro para nomes de arquivo.
    """
    base = (texto or "artefato").strip().lower()
    base = re.sub(r"[^a-z0-9]+", "_", base)
    base = base.strip("_")
    return base or "artefato"


def _safe_filename(nome: str) -> str:
    """Sanitiza nome de arquivo removendo caracteres especiais.

    Args:
        nome: Nome original do arquivo.

    Returns:
        str: Nome seguro para filesystem.
    """
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", (nome or "arquivo.txt").strip())
    cleaned = cleaned.lstrip(".")
    return cleaned or "arquivo.txt"


def _salvar_arquivos_apoio(artefato: dict, destino: Path) -> list[Path]:
    """Salva arquivos de apoio (texto ou base64) no diretório de destino.

    Args:
        artefato: Dicionário contendo lista de arquivos_apoio.
        destino: Path do diretório onde arquivos serão salvos.

    Returns:
        list[Path]: Lista de paths dos arquivos salvos.
    """
    arquivos = artefato.get("arquivos_apoio", [])
    if not isinstance(arquivos, list):
        return []

    salvos: list[Path] = []
    for item in arquivos:
        if not isinstance(item, dict):
            continue

        nome = _safe_filename(item.get("nome") or item.get("filename") or "arquivo.txt")
        conteudo_texto = item.get("conteudo")
        conteudo_b64 = item.get("conteudo_base64")

        caminho = destino / nome

        if isinstance(conteudo_texto, str):
            caminho.write_text(conteudo_texto, encoding="utf-8")
            salvos.append(caminho)
            continue

        if isinstance(conteudo_b64, str):
            try:
                bruto = base64.b64decode(conteudo_b64)
            except Exception:
                continue
            caminho.write_bytes(bruto)
            salvos.append(caminho)

    return salvos
