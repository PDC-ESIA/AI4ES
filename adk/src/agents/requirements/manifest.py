"""Emissor determinístico do Manifesto de Fase — Requisitos (Time 1).

Decisão de 23/07/2026: cada artefato é referenciado individualmente no
manifesto (não só a pasta). O consumidor (context engineer do Time 3)
escolhe quais arquivos priorizar sem varrer o workspace inteiro.

Padrão de implementação: after_agent_callback determinístico, zero LLM,
idêntico ao cr_reviewer.py (Time 4, PR #316). Falha é logada e degradada,
nunca derruba o pipeline.

Contrato inter-times:
- o manifesto é anexado a state["phase_manifests"], lista padronizada
  consumida pelo orquestrador e pelas demais fases; state["requirements_manifest"]
  é mantido por compatibilidade;
- paths usam separador "/" independentemente do SO de origem;
- quando status=blocked, o summary explicita o motivo do bloqueio.
"""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from shared.manifest import PhaseManifest
from shared.workspace import get_agent_workspace, get_workspace_root

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
else:
    CallbackContext = Any  # type: ignore[misc,assignment]

logger = logging.getLogger(__name__)

PHASE_NAME = "requirements"


def _rel_path(f: Path, ws_root: Path) -> str:
    """Path relativo ao workspace root, com separador normalizado ("/").

    O manifesto é consumido por agentes que podem rodar em SOs distintos;
    barras invertidas (Windows) quebram a resolução dos paths no consumidor.
    """
    return str(f.relative_to(ws_root)).replace("\\", "/")

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
                "path": _rel_path(f, ws_root),
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
                "path": _rel_path(candidate, ws_root),
            })
            break

    return artifacts


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
        bloqueante = "**Bloqueante:** Sim" in text
        doubts.append({
            "id":         f.stem,
            "severidade": "alta" if bloqueante else "media",
            "bloqueante": bloqueante,
            "path":       _rel_path(f, ws_root),
        })
    return doubts


def _derive_status(artifacts: list[dict], doubts: list[dict]) -> str:
    """Deriva o status da fase a partir dos artefatos e dúvidas coletados.

    Invariante: status=ok ⟹ sem dúvidas bloqueantes e ao menos um artefato.
    """
    if any(d["bloqueante"] for d in doubts):
        return "blocked"
    if not artifacts:
        return "blocked"
    if doubts:
        return "partial"
    return "ok"


def _blocked_reason(artifacts: list[dict], doubts: list[dict]) -> str | None:
    """Motivo do bloqueio, quando status=blocked.

    Permite ao consumidor entender por que a fase parou sem precisar
    abrir os Doubt_Artifacts.
    """
    bloqueantes = [d for d in doubts if d["bloqueante"]]
    if bloqueantes:
        ids = ", ".join(d["id"] for d in bloqueantes)
        return f"Motivo do bloqueio: dúvida(s) bloqueante(s): {ids}."
    if not artifacts:
        return "Motivo do bloqueio: nenhum artefato de requisitos foi gerado."
    return None


def _build_summary(artifacts: list[dict], doubts: list[dict], status: str) -> str:
    counts: dict[str, int] = {}
    for a in artifacts:
        counts[a["tipo"]] = counts.get(a["tipo"], 0) + 1
    partes = [f"{v} {k}(s)" for k, v in counts.items()]
    base = "Fase de requisitos concluída. " + ", ".join(partes) + "."
    if doubts:
        base += f" {len(doubts)} dúvida(s) registrada(s)."
    if status == "blocked":
        reason = _blocked_reason(artifacts, doubts)
        if reason:
            base += f" {reason}"
    return base


def emit_requirements_manifest(callback_context: CallbackContext) -> None:
    """after_agent_callback — emite manifesto de saída da fase de requisitos.

    Anexa o manifesto a callback_context.state["phase_manifests"] — lista
    padronizada entre as fases, consumida pelo orquestrador e pelos agentes
    seguintes. Mantém também state["requirements_manifest"] por
    compatibilidade e persiste requirements/manifest.json no workspace
    para rastreabilidade e debug.

    Retorna None para não sobrescrever a saída do agente.
    """
    try:
        ws_root = get_workspace_root()
        req_ws  = get_agent_workspace("requirements_agent")

        artifacts = _scan_artifacts(req_ws, ws_root)
        doubts    = _scan_doubts(req_ws, ws_root)
        status    = _derive_status(artifacts, doubts)

        manifest: dict = {
            "phase":     PHASE_NAME,
            "status":    status,
            "artifacts": artifacts,
            "doubts":    doubts,
            "summary":   _build_summary(artifacts, doubts, status),
        }

        # Valida o contrato comum antes de publicar no state.
        manifest = PhaseManifest.model_validate(manifest).model_dump()

        # Handoff padronizado entre fases: lista phase_manifests
        # (substitui entrada anterior da própria fase, se houver).
        manifests = [
            m for m in (callback_context.state.get("phase_manifests") or [])
            if m.get("phase") != PHASE_NAME
        ]
        manifests.append(manifest)
        callback_context.state["phase_manifests"] = manifests

        # Compatibilidade com consumidores legados.
        callback_context.state["requirements_manifest"] = manifest

        # Cópia persistida para rastreabilidade
        manifest_path = req_ws / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        logger.info(
            "[MANIFEST] requirements → %s | %d artefato(s) | %d dúvida(s)",
            status, len(artifacts), len(doubts),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[MANIFEST] Falha ao emitir manifesto de requisitos: %s", exc)
