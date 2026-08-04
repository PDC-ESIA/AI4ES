"""Emissor determinístico do Manifesto de Fase — Codificação (Time 4).

Padrão: after_agent_callback determinístico, zero LLM — alinhado ao
emit_requirements_manifest do Time 1 (PR #320), adaptado para o
workspace e fluxo de validação do pipeline coding_review.

Diferença em relação ao Time 1: a fase de codificação tem uma etapa de
revisão explícita (cr_reviewer) cujo veredicto (APROVADO / BLOQUEADO)
entra na derivação de status, além dos Doubt_Artifacts gerados pelo
context engineer.

Layout do workspace (ver shared/workspace.py::AGENT_DIRS):

    workspace_output/coder/src/app/      → tipo "codigo"
    workspace_output/coder/src/tests/    → tipo "teste"
    workspace_output/coder/src/          → tipo "config"  (Dockerfile, etc.)
    workspace_output/coder/review/       → tipo "revisao"
    workspace_output/coder/**/Doubt_*    → doubts
"""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from shared.workspace import get_agent_workspace, get_workspace_root

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
else:
    CallbackContext = Any

logger = logging.getLogger(__name__)

PHASE_NAME = "coding"
STATE_KEY = "coding_manifest"

_REVIEW_PASS_MARKERS = ("## Status: APROVADO", "Status: APROVADO")
_REVIEW_FAIL_MARKERS = ("## Status: BLOQUEADO", "Status: BLOQUEADO")

_CONFIG_FILES = {
    "requirements.txt", "Dockerfile", "docker-compose.yml",
    "docker-compose.yaml", "conftest.py", ".dockerignore",
    "pyproject.toml", "setup.py", "setup.cfg",
}

_IGNORED = {"manifest.json", ".ai4se_workspace", "io_operations.log"}
_IGNORED_SUFFIXES = {".pyc", ".pyo"}


def _scan_artifacts(coder_ws: Path, ws_root: Path) -> list[dict]:
    """Varre o workspace de coding e classifica artefatos por tipo."""
    artifacts: list[dict] = []

    app_dir = coder_ws / "src" / "app"
    if app_dir.exists():
        for f in sorted(app_dir.rglob("*.py")):
            if "__pycache__" not in f.parts and f.name not in _IGNORED:
                artifacts.append({
                    "tipo": "codigo",
                    "id": f.stem,
                    "path": str(f.relative_to(ws_root)).replace("\\", "/"),
                })

    tests_dir = coder_ws / "src" / "tests"
    if tests_dir.exists():
        for f in sorted(tests_dir.rglob("*.py")):
            if "__pycache__" not in f.parts and f.name not in _IGNORED:
                artifacts.append({
                    "tipo": "teste",
                    "id": f.stem,
                    "path": str(f.relative_to(ws_root)).replace("\\", "/"),
                })

    src = coder_ws / "src"
    if src.exists():
        for f in sorted(src.iterdir()):
            if f.is_file() and f.name in _CONFIG_FILES:
                artifacts.append({
                    "tipo": "config",
                    "id": f.stem,
                    "path": str(f.relative_to(ws_root)).replace("\\", "/"),
                })

    review_dir = coder_ws / "review"
    if review_dir.exists():
        for f in sorted(review_dir.iterdir()):
            if f.is_file() and f.name not in _IGNORED and f.suffix not in _IGNORED_SUFFIXES:
                artifacts.append({
                    "tipo": "revisao",
                    "id": f.stem,
                    "path": str(f.relative_to(ws_root)).replace("\\", "/"),
                })

    return artifacts


def _scan_doubts(coder_ws: Path, ws_root: Path) -> list[dict]:
    """Varre por Doubt_Artifact_*.md nos locais do workflow de coding.

    tool_gerar_doubt_artifact_adk escreve em ws_root/Doubt_Artifact_*.md
    (raiz do workspace). O scan cobre a raiz (não recursivo) e o interior
    de coder/ (recursivo), evitando capturar doubts de outras fases
    (requirements/, design/, etc.). O marcador de bloqueante é
    '**Bloqueante:** Sim' (mesmo padrão do Time 1).
    """
    candidates = set(ws_root.glob("Doubt_Artifact_*.md"))
    candidates |= set(coder_ws.rglob("Doubt_Artifact_*.md"))
    doubts: list[dict] = []
    for f in sorted(candidates):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        # Detecta dois formatos: padrão Time 1 ("**Bloqueante:** Sim") e
        # formato gerado por tool_gerar_doubt_artifact_adk ("EXECUÇÃO PAUSADA").
        bloqueante = "**Bloqueante:** Sim" in text or "EXECUÇÃO PAUSADA" in text
        doubts.append({
            "id": f.stem,
            "severidade": "alta" if bloqueante else "media",
            "bloqueante": bloqueante,
            "path": str(f.relative_to(ws_root)).replace("\\", "/"),
        })
    return doubts


def _validation_verdict(coder_ws: Path) -> str:
    """Lê o veredicto do cr_reviewer em coder/review/.

    Retorna 'pass', 'fail' ou 'absent'. Exclusivo da fase de coding —
    o reviewer emite um relatório explícito que vai além dos doubts.
    """
    review_dir = coder_ws / "review"
    if not review_dir.exists():
        return "absent"

    saw_pass = False
    for f in review_dir.iterdir():
        if not f.is_file() or f.name in _IGNORED or f.suffix in _IGNORED_SUFFIXES:
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(m in content for m in _REVIEW_FAIL_MARKERS):
            return "fail"
        if any(m in content for m in _REVIEW_PASS_MARKERS):
            saw_pass = True

    return "pass" if saw_pass else "absent"


def _derive_status(artifacts: list[dict], doubts: list[dict], validation: str) -> str:
    """Deriva o status da fase coding.

    Precedência:
    1. Doubt bloqueante            → blocked
    2. Nenhum artefato de código   → blocked
    3. Doubt não-bloqueante        → partial
    4. Reviewer aprovado           → ok
    5. Reviewer falhou / ausente   → partial
    """
    if any(d["bloqueante"] for d in doubts):
        return "blocked"
    code_artifacts = [a for a in artifacts if a["tipo"] == "codigo"]
    if not code_artifacts:
        return "blocked"
    if doubts:
        return "partial"
    if validation == "pass":
        return "ok"
    return "partial"


def _build_summary(artifacts: list[dict], doubts: list[dict], validation: str) -> str:
    counts: dict[str, int] = {}
    for a in artifacts:
        counts[a["tipo"]] = counts.get(a["tipo"], 0) + 1
    partes = (
        ", ".join(f"{n} {tipo}(s)" for tipo, n in sorted(counts.items()))
        or "nenhum artefato"
    )
    base = f"Fase de codificação concluída. {partes}. Revisão: {validation}."
    if doubts:
        n_bloq = sum(1 for d in doubts if d["bloqueante"])
        base += f" {len(doubts)} dúvida(s) ({n_bloq} bloqueante(s))."
    return base


def emit_coding_manifest(callback_context: CallbackContext) -> None:
    """after_agent_callback — emite o manifesto da fase de codificação.

    Grava em callback_context.state["coding_manifest"] (handoff in-memory
    para o orquestrador) e persiste coding/manifest.json no workspace para
    rastreabilidade e consumo pelo pipeline de QA.

    Retorna None para não sobrescrever a saída do agente (contrato ADK).
    """
    try:
        ws_root = get_workspace_root()
        coder_ws = get_agent_workspace("coder")

        artifacts  = _scan_artifacts(coder_ws, ws_root)
        doubts     = _scan_doubts(coder_ws, ws_root)
        validation = _validation_verdict(coder_ws)
        status     = _derive_status(artifacts, doubts, validation)

        session_id = (
            getattr(getattr(callback_context, "session", None), "id", None)
            or getattr(callback_context, "session_id", None)
            or callback_context.state.get("session_id")
        )

        manifest: dict = {
            "phase":      PHASE_NAME,
            "status":     status,
            "artifacts":  artifacts,
            "doubts":     doubts,
            "summary":    _build_summary(artifacts, doubts, validation),
            "session_id": session_id,
        }

        callback_context.state[STATE_KEY] = manifest

        manifest_path = ws_root / "coding" / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        logger.info(
            "[MANIFEST] coding → %s | %d artefato(s) | %d dúvida(s) | revisão: %s",
            status, len(artifacts), len(doubts), validation,
        )
    except Exception as exc:
        logger.warning("[MANIFEST] Falha ao emitir manifesto de coding: %s", exc)
