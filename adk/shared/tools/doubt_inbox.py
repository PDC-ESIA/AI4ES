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


# Funções principais — implementadas nas tasks 2-7
def coletar_doubts_pendentes(caminho_projeto: str = ".") -> List[Dict]:
    raise NotImplementedError("Implementado em Task 6")


def responder_doubt(caminho_arquivo: str, resposta: str, autor: str = "humano") -> bool:
    raise NotImplementedError("Implementado em Task 7")
