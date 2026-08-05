"""Emissor determinístico do Manifesto de Fase — Requisitos (Time 1).

Decisão de 23/07/2026: cada artefato é referenciado individualmente no
manifesto (não só a pasta). O consumidor (context engineer do Time 3)
escolhe quais arquivos priorizar sem varrer o workspace inteiro.

Padrão de implementação: after_agent_callback determinístico, zero LLM,
idêntico ao cr_reviewer.py (Time 4, PR #316). Falha é logada e degradada,
nunca derruba o pipeline.
"""

import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from shared.manifest import PhaseManifest
from shared.workspace import get_agent_workspace, get_workspace_root
from .validation import STATE_AUDITORIA

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
else:
    CallbackContext = Any  # type: ignore[misc,assignment]

logger = logging.getLogger(__name__)

# Chave de handoff lida pelo orquestrador em
# `orchestrator/_helpers._load_phase_manifests`. É uma LISTA de manifestos de
# fase, não um manifesto único: publicar em qualquer outra chave faz a fase
# seguinte iniciar sem enxergar nenhum artefato desta.
STATE_PHASE_MANIFESTS = "phase_manifests"
PHASE = "requirements"

# Mapeamento subpasta → tipo de artefato.
# Espelha os subdirs criados por tool_salvar_artefato_requisito (filesystem.py).
_SUBDIR_TIPOS: dict[str, str] = {
    "HUs":    "HU",
    "RFs":    "RF",
    "RNFs":   "RNF",
    "RNs":    "RN",
    "Outros": "Outro",
}


def _scan_artifacts(req_ws: Path, ws_root: Path) -> list[dict]:
    """Varre o workspace de requisitos e retorna lista de ponteiros de artefatos.

    Cada item contém tipo, id e path relativo à raiz do workspace.
    Nunca inclui o conteúdo dos artefatos.
    """
    artifacts: list[dict] = []

    for subdir, tipo in _SUBDIR_TIPOS.items():
        folder = req_ws / subdir
        if not folder.exists():
            continue
        for f in sorted(folder.glob("*.md")):
            artifacts.append({
                "tipo": tipo,
                "id":   f.stem,
                "path": str(f.relative_to(ws_root)),
            })

    # Glossário: glossario_agent grava em requirements/glossario/Glossario.md
    # Fallback: requirements/Glossario.md (legado)
    for candidate in [
        req_ws / "glossario" / "Glossario.md",
        req_ws / "Glossario.md",
    ]:
        if candidate.exists():
            artifacts.append({
                "tipo": "Glossario",
                "id":   "Glossario",
                "path": str(candidate.relative_to(ws_root)),
            })
            break

    return artifacts


# O glossário ainda não é produzido de forma confiável, então sua ausência não
# pode barrar a fase: uma dúvida cujo artefato afetado é o glossário é
# rebaixada a não-bloqueante. A dúvida continua registrada no manifesto (o
# status vira `partial`, não `ok`) — o que se remove é só o poder de veto.
_ARTEFATO_AFETADO = re.compile(
    r"^\s*-\s*\*\*Artefato afetado:\*\*\s*(.+?)\s*$", re.MULTILINE
)
_TERMOS_GLOSSARIO = ("glossario", "glossário", "glossary")


def _e_sobre_glossario(text: str) -> bool:
    """True quando a dúvida trata exclusivamente do glossário."""
    match = _ARTEFATO_AFETADO.search(text)
    if not match:
        return False
    alvo = match.group(1).strip().strip("[]").lower()
    return any(termo in alvo for termo in _TERMOS_GLOSSARIO)


def _scan_doubts(req_ws: Path, ws_root: Path) -> list[dict]:
    """Varre o workspace de requisitos por arquivos Doubt_Artifact_*.md.

    Os doubts são gravados por gerar_doubt_artifact diretamente na raiz
    de req_ws (workspace_output/requirements/), com nome no padrão
    Doubt_Artifact_<ID>_<timestamp>.md.

    O marcador de bloqueante no arquivo é '**Bloqueante:** Sim'.
    """
    doubts: list[dict] = []
    for f in sorted(req_ws.glob("Doubt_Artifact_*.md")):
        text = f.read_text(encoding="utf-8", errors="ignore")
        bloqueante = "**Bloqueante:** Sim" in text and not _e_sobre_glossario(text)
        doubts.append({
            "id":         f.stem,
            "severidade": "alta" if bloqueante else "media",
            "bloqueante": bloqueante,
            "path":       str(f.relative_to(ws_root)),
        })
    return doubts


def _derive_status(artifacts: list[dict], doubts: list[dict]) -> str:
    """Deriva o status da fase a partir dos artefatos e dúvidas coletados.

    Invariante do contrato `PhaseManifest`: `blocked` exige ao menos uma
    dúvida bloqueante. Por isso a ausência de artefatos sem dúvida registrada
    degrada para `partial` — emitir `blocked` ali reprovaria a validação e o
    manifesto não chegaria à fase seguinte.
    """
    if any(d["bloqueante"] for d in doubts):
        return "blocked"
    if not artifacts:
        return "partial"
    if doubts:
        return "partial"
    return "ok"


def _build_summary(artifacts: list[dict], doubts: list[dict]) -> str:
    counts: dict[str, int] = {}
    for a in artifacts:
        counts[a["tipo"]] = counts.get(a["tipo"], 0) + 1
    partes = [f"{v} {k}(s)" for k, v in counts.items()]
    base = "Fase de requisitos concluída. " + ", ".join(partes) + "."
    if doubts:
        base += f" {len(doubts)} dúvida(s) registrada(s)."
    return base


def _publicar_no_state(state: Any, manifest: dict) -> None:
    """Anexa o manifesto à lista `phase_manifests` do state.

    Valida contra `PhaseManifest` antes de publicar: um manifesto que viole o
    contrato faria `_load_phase_manifests` estourar no orquestrador, derrubando
    o handoff de todas as fases seguintes.

    Uma reemissão da mesma fase (retomada após HITL, por exemplo) substitui a
    entrada anterior em vez de duplicá-la.
    """
    PhaseManifest.model_validate(manifest)

    anteriores = state.get(STATE_PHASE_MANIFESTS) or []
    if not isinstance(anteriores, list):
        anteriores = []

    manifests = [
        m for m in anteriores
        if not (isinstance(m, dict) and m.get("phase") == manifest["phase"])
    ]
    manifests.append(manifest)

    # Reatribuição (e não mutação in-place) para que o ADK gere o state_delta.
    state[STATE_PHASE_MANIFESTS] = manifests


def emit_requirements_manifest(callback_context: CallbackContext) -> None:
    """after_agent_callback — emite manifesto de saída da fase de requisitos.

    Anexa o manifesto a `callback_context.state["phase_manifests"]`, que é o
    handoff (in-memory) consumido pelo orquestrador, e persiste
    requirements/manifest.json no workspace para rastreabilidade e debug.

    Retorna None para não sobrescrever a saída do agente.
    """
    try:
        ws_root = get_workspace_root()
        req_ws  = get_agent_workspace("requirements_agent")

        artifacts = _scan_artifacts(req_ws, ws_root)
        doubts    = _scan_doubts(req_ws, ws_root)
        status    = _derive_status(artifacts, doubts)

        # Relatório produzido pela auditoria (validation.auditar_saida_final,
        # after_agent_callback do requirements_agent). Aqui só se consome —
        # a validação em si mora em validation.py.
        auditoria = callback_context.state.get(STATE_AUDITORIA) or {
            "schema_status": "nao_executada",
            "coerente": False,
        }

        # Saída incoerente com o que foi gravado não pode ser reportada como ok.
        if status == "ok" and not auditoria.get("coerente", False):
            status = "partial"

        manifest: dict = {
            "phase":     PHASE,
            "status":    status,
            "artifacts": artifacts,
            "doubts":    doubts,
            "summary":   _build_summary(artifacts, doubts),
            "audit":     auditoria,
        }

        # Handoff in-memory para o orquestrador
        _publicar_no_state(callback_context.state, manifest)

        # Cópia persistida para rastreabilidade
        manifest_path = req_ws / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        logger.info(
            "[MANIFEST] requirements → %s | %d artefato(s) | %d dúvida(s) | auditoria=%s",
            status, len(artifacts), len(doubts), auditoria.get("schema_status"),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[MANIFEST] Falha ao emitir manifesto de requisitos: %s", exc)
