"""Doubt Inbox — coleta e respostas centralizadas de Doubt_Artifacts.

Suporta os 4 formatos vigentes no AI4ES:
- Time 1 (gerar_doubt_artifact): arquivo único, header `## Metadados da Sessão`.
- doubt_handler: arquivo centralizado com múltiplas seções `### [D-NNN]`.
- clarification: header `# Doubt Artifact — <titulo>` + `> EXECUÇÃO PAUSADA`.
- QA (DoubtArtifactGenerator): header `# DOUBT ARTEFACT |`.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

DIRETORIOS_IGNORADOS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", "dist", "build", ".tox",
}

SEVERIDADE_ORDEM = {
    "Crítica": 0, "Alta": 1, "Média": 2, "Baixa": 3, "Desconhecida": 4,
}


def _inferir_origem(path: Path) -> str:
    """Tenta inferir o agente origem pelo caminho do arquivo."""
    partes_lower = [p.lower() for p in path.parts]
    candidatos = [
        "requirements", "design_architect", "mermaid_specialist",
        "markdown_specialist", "validator", "io_agent",
        "coder", "reviewer", "architect", "test_planner",
        "finalizer", "qa_agent", "action_planner", "code_fix_agent",
        "design_orchestrator", "glossario_agent",
    ]
    for agente in candidatos:
        if any(agente in p for p in partes_lower):
            return agente
    return "desconhecido"


def _eh_formato_time1(conteudo: str) -> bool:
    """Detecta se conteúdo é formato Time 1 (gerar_doubt_artifact)."""
    return "## Metadados da Sessão" in conteudo and "## Dúvida Registrada" in conteudo


def _parse_time1(conteudo: str, path: Path) -> List[Dict]:
    """Parse formato `gerar_doubt_artifact` (Time 1). Um doubt por arquivo."""
    id_match = re.search(r"### (D-[\w-]+)", conteudo)
    if not id_match:
        return []

    def _campo(pattern: str) -> str:
        m = re.search(pattern, conteudo, re.MULTILINE)
        return m.group(1).strip() if m else ""

    status = _campo(r"\*\*Status:\*\*\s*(.+?)\s*$")
    if "Resolvido" in status or "✅" in status:
        return []

    bloq_raw = _campo(r"\*\*Bloqueante:\*\*\s*(.+?)\s*$")
    bloqueante = "Sim" in bloq_raw

    return [{
        "path": str(path),
        "id": id_match.group(1),
        "status": status or "Aberta",
        "categoria": "Falta de Contexto",
        "severidade": "Crítica" if bloqueante else "Média",
        "origem_agente": _inferir_origem(path),
        "pergunta": _campo(r"\*\*Dúvida:\*\*\s*(.+?)\s*$"),
        "sugestao": _campo(r"\*\*Sugestão do Agente:\*\*\s*(.+?)\s*$"),
        "bloqueante": bloqueante,
    }]


# Funções principais — implementadas nas tasks 2-7
def coletar_doubts_pendentes(caminho_projeto: str = ".") -> List[Dict]:
    raise NotImplementedError("Implementado em Task 6")


def responder_doubt(caminho_arquivo: str, resposta: str, autor: str = "humano") -> bool:
    raise NotImplementedError("Implementado em Task 7")
