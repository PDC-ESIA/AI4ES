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


def _eh_formato_doubt_handler(conteudo: str) -> bool:
    """Detecta se conteúdo é formato doubt_handler (arquivo centralizado)."""
    return "## Histórico de Dúvidas" in conteudo


def _parse_doubt_handler(conteudo: str, path: Path) -> List[Dict]:
    """Parse formato `doubt_handler.registrar_duvida` (arquivo único, múltiplos doubts)."""
    resultados = []
    # Divide em seções por header "### [D-"
    secoes = conteudo.split("### [D-")[1:]
    for secao in secoes:
        # Status aberto: emoji 🔴 + "Aberta" no campo Status
        if "🔴 Aberta" not in secao and "Status:** Aberta" not in secao:
            continue

        id_match = re.match(r"([\w-]+)\]", secao)
        if not id_match:
            continue
        duvida_id = f"D-{id_match.group(1)}"

        def _campo(pattern: str, default: str = "") -> str:
            m = re.search(pattern, secao, re.MULTILINE)
            return m.group(1).strip() if m else default

        severidade = _campo(r"\*\*Severidade:\*\*\s*(.+?)\s*$", "Desconhecida")
        bloqueante = severidade in {"Crítica", "Alta"}

        resultados.append({
            "path": str(path),
            "id": duvida_id,
            "status": _campo(r"\*\*Status:\*\*\s*(.+?)\s*$", "Aberta"),
            "categoria": _campo(r"\*\*Categoria:\*\*\s*(.+?)\s*$"),
            "severidade": severidade,
            "origem_agente": _inferir_origem(path),
            "pergunta": _campo(r"\*\*Descrição:\*\*\s*(.+?)\s*$"),
            "sugestao": _campo(r"\*\*Sugestão do Agente:\*\*\s*(.+?)\s*$"),
            "bloqueante": bloqueante,
        })
    return resultados


def _eh_formato_clarification(conteudo: str) -> bool:
    """Detecta se conteúdo é formato clarification (tool_ask_clarification)."""
    return "EXECUÇÃO PAUSADA — INTERVENÇÃO NECESSÁRIA" in conteudo


def _eh_formato_qa(conteudo: str) -> bool:
    """Detecta se conteúdo é formato QA (DoubtArtifactGenerator)."""
    return "DOUBT ARTEFACT |" in conteudo or "DOUBT ARTEFACT|" in conteudo


def _parse_clarification(conteudo: str, path: Path) -> List[Dict]:
    """Parse formato `tool_ask_clarification` — pergunta única por arquivo."""
    # Status: campo "Status:" linha solta no final do arquivo
    status_match = re.search(r"^Status:\s*(.+?)\s*$", conteudo, re.MULTILINE)
    status = status_match.group(1).strip() if status_match else "Pendente"
    if "Resolvido" in status or "Resolvida" in status:
        return []

    titulo_match = re.search(r"^# Doubt Artifact — (.+?)$", conteudo, re.MULTILINE)
    titulo = titulo_match.group(1).strip() if titulo_match else path.stem

    def _secao(nome: str) -> str:
        """Captura conteúdo entre `## <nome>` e próxima seção (## ou ---)."""
        pattern = rf"^## {re.escape(nome)}.*?\n(.*?)(?=\n## |\n---|\Z)"
        m = re.search(pattern, conteudo, re.MULTILINE | re.DOTALL)
        return m.group(1).strip() if m else ""

    return [{
        "path": str(path),
        "id": titulo[:60],
        "status": status,
        "categoria": "Clarification",
        "severidade": "Alta",
        "origem_agente": _inferir_origem(path),
        "pergunta": _secao("Descrição do Problema / Dúvida"),
        "sugestao": _secao("Pergunta / Sugestão de Resolução"),
        "bloqueante": True,
    }]


def _parse_qa(conteudo: str, path: Path) -> List[Dict]:
    """Parse formato `DoubtArtifactGenerator` (Time 3)."""
    # Status: rodapé com "[x] Aprovado" ou "[x] Reprovado" → resolvido
    if re.search(r"\[x\]\s*Aprovado", conteudo) or re.search(r"\[x\]\s*Reprovado", conteudo):
        return []

    id_match = re.search(r"\*\*ID do Artefato:\*\*\s*`([^`]+)`", conteudo)
    if not id_match:
        return []
    duvida_id = id_match.group(1)

    motivo_match = re.search(
        r"\*\*Análise / Motivo da Interrupção:\*\*\s*\n?>\s*`([^`]+)`",
        conteudo,
    )
    pergunta = motivo_match.group(1).strip() if motivo_match else ""

    return [{
        "path": str(path),
        "id": duvida_id,
        "status": "Aberta",
        "categoria": "QA",
        "severidade": "Alta",
        "origem_agente": "qa_agent",
        "pergunta": pergunta,
        "sugestao": "",
        "bloqueante": True,
    }]


# Funções principais — implementadas nas tasks 2-7
def coletar_doubts_pendentes(caminho_projeto: str = ".") -> List[Dict]:
    """Coleta todos os doubt artifacts ainda em aberto no projeto.

    Faz varredura recursiva por `Doubt_Artifact*.md`, identifica o formato
    de cada arquivo e extrai metadados. Retorna lista ordenada por
    (bloqueante DESC, severidade ASC, id ASC).

    Args:
        caminho_projeto: diretório raiz da busca.

    Returns:
        Lista de dicts com chaves: path, id, status, categoria, severidade,
        origem_agente, pergunta, sugestao, bloqueante.
    """
    base = Path(caminho_projeto).resolve()
    if not base.is_dir():
        return []

    parsers = [
        (_eh_formato_time1, _parse_time1),
        (_eh_formato_doubt_handler, _parse_doubt_handler),
        (_eh_formato_clarification, _parse_clarification),
        (_eh_formato_qa, _parse_qa),
    ]

    duvidas: List[Dict] = []
    for arquivo in base.rglob("Doubt_Artifact*.md"):
        if any(parte in DIRETORIOS_IGNORADOS for parte in arquivo.parts):
            continue
        try:
            conteudo = arquivo.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for detector, parser in parsers:
            if detector(conteudo):
                try:
                    duvidas.extend(parser(conteudo, arquivo))
                except Exception:
                    # Parser falhou — ignora silenciosamente (best-effort)
                    pass
                break

    duvidas.sort(key=lambda d: (
        not d.get("bloqueante", False),
        SEVERIDADE_ORDEM.get(d.get("severidade", "Desconhecida"), 4),
        d.get("id", ""),
    ))
    return duvidas


def responder_doubt(caminho_arquivo: str, resposta: str, autor: str = "humano") -> bool:
    raise NotImplementedError("Implementado em Task 7")
