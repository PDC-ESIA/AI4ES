"""Emissor determinístico do Manifesto de Fase — Codificação (Time 4).

Padrão: after_agent_callback determinístico, zero LLM — alinhado ao
emit_requirements_manifest do Time 1 (PR #320), adaptado para o
workspace e fluxo de validação do pipeline coding_review.

Diferença em relação ao Time 1: a fase de codificação tem uma etapa de
revisão explícita (cr_reviewer) cujo veredicto (APROVADO / BLOQUEADO)
entra na derivação de status, além dos Doubt_Artifacts gerados pelo
context engineer.

Layout do workspace (ver shared/workspace.py::AGENT_DIRS):

    workspace_output/coder/src/app/      → tipo "source" (padrão: app/)
    workspace_output/coder/src/tests/    → tipo "teste"
    workspace_output/coder/src/          → tipo "config"  (Dockerfile, etc.)
    workspace_output/coder/review/       → tipo "revisao"
    workspace_output/coder/tasks/        → tipo "task"
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
    CallbackContext = Any  # type: ignore[misc,assignment]

logger = logging.getLogger(__name__)

PHASE_NAME = "coding"
STATE_KEY = "coding_manifest"

_REVIEW_PASS_MARKERS = ("## Status: APROVADO", "Status: APROVADO")
_REVIEW_FAIL_MARKERS = ("## Status: BLOQUEADO", "Status: BLOQUEADO")

_IGNORED = {"manifest.json", ".ai4se_workspace", "io_operations.log"}
_IGNORED_SUFFIXES = {".pyc", ".pyo"}


def _scan_artifacts(coder_ws: Path, ws_root: Path) -> list[dict]:
    """Varre o workspace de coding e classifica artefatos por tipo.
    Cataloga todos os arquivos gerados pelo coder — não apenas .py ou
    arquivos de configuração pré-definidos. O tipo é determinado pela
    subpasta dentro de src/ ou pela pasta de destino:
      - src/app/    → source
      - src/tests/  → teste
      - src/demais  → config
      - review/     → revisao
      - tasks/      → task (exceto _macro_context.json → macro_context)
    """
    artifacts: list[dict] = []

    src = coder_ws / "src"
    if src.exists():
        for f in sorted(src.rglob("*")):
            if (
                not f.is_file()
                or "__pycache__" in f.parts
                or f.name in _IGNORED
                or f.suffix in _IGNORED_SUFFIXES
            ):
                continue

            partes = f.relative_to(src).parts
            subdir = partes[0] if partes else ""

            if subdir == "app":
                tipo = "source"
                id_val = str(
                    f.relative_to(src / "app").with_suffix("")
                ).replace("\\", "/")
            elif subdir == "tests":
                tipo = "teste"
                id_val = str(
                    f.relative_to(src / "tests").with_suffix("")
                ).replace("\\", "/")
            else:
                tipo = "config"
                id_val = f.name

            artifacts.append({
                "tipo": tipo,
                "id": id_val,
                "path": str(f.relative_to(ws_root)).replace("\\", "/"),
            })

    review_dir = coder_ws / "review"
    if review_dir.exists():
        for f in sorted(review_dir.iterdir()):
            if (
                f.is_file()
                and f.name not in _IGNORED
                and f.suffix not in _IGNORED_SUFFIXES
            ):
                artifacts.append({
                    "tipo": "revisao",
                    "id": f.stem,
                    "path": str(f.relative_to(ws_root)).replace("\\", "/"),
                })

    tasks_dir = coder_ws / "tasks"
    if tasks_dir.exists():
        for f in sorted(tasks_dir.glob("*.json")):
            if f.name not in _IGNORED:
                tipo = "macro_context" if f.stem == "_macro_context" else "task"
                artifacts.append({
                    "tipo": tipo,
                    "id": f.stem,
                    "path": str(f.relative_to(ws_root)).replace("\\", "/"),
                })

    return artifacts


def _scan_doubts(coder_ws: Path, ws_root: Path) -> list[dict]:
    """Varre por Doubt_Artifact_*.md nos locais do workflow de coding.

    tool_gerar_doubt_artifact_adk escreve em ws_root/Doubt_Artifact_*.md
    (raiz do workspace). O scan cobre a raiz (não recursivo) e o interior
    de coder/ (recursivo), evitando capturar doubts de outras fases
    (requirements/, design/, etc.).
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

    Retorna 'pass', 'fail' ou 'absent'.
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


def _derive_status(
    artifacts: list[dict],
    doubts: list[dict],
    validation: str,
    has_accepted_with_caveats: bool = False,
) -> str:
    """Deriva o status da fase coding.

    Precedência:
    1. Doubt bloqueante            → blocked
    2. Nenhum artefato produzido   → partial (na prática nunca ocorre sem
                                    doubt — emit_coding_manifest insere
                                    doubt sintético bloqueante nesse caso,
                                    resultando em blocked via regra 1)
    3. Reviewer reprovou           → partial (na prática nunca ocorre sem
                                    doubt — emit_coding_manifest insere
                                    doubt sintético bloqueante nesse caso,
                                    resultando em blocked via regra 1)
    4. Doubt não-bloqueante        → partial
    5. Reviewer aprovado, mas há task aceita com ressalvas → partial
    6. Reviewer aprovado sem ressalvas                     → ok
    7. Qualquer outro caso         → partial
    """
    if any(d["bloqueante"] for d in doubts):
        return "blocked"
    if not artifacts:
        return "partial"
    if doubts:
        return "partial"
    if validation == "pass" and has_accepted_with_caveats:
        return "partial"
    if validation == "pass":
        return "ok"
    return "partial"


def _build_summary(
    artifacts: list[dict],
    doubts: list[dict],
    validation: str,
    accepted_count: int = 0,
) -> str:
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
    if accepted_count:
        base += f" {accepted_count} task(s) aceita(s) com ressalvas."
    return base


def emit_coding_manifest(callback_context: CallbackContext) -> None:
    """after_agent_callback — emite o manifesto da fase de codificação.

    Grava em callback_context.state["coding_manifest"] (handoff in-memory
    para o orquestrador) e persiste coder/manifest.json no workspace para
    rastreabilidade e consumo pelo pipeline de QA.

    Retorna None para não sobrescrever a saída do agente (contrato ADK).
    """
    try:
        ws_root = get_workspace_root()
        coder_ws = get_agent_workspace("coder")

        artifacts  = _scan_artifacts(coder_ws, ws_root)
        doubts     = _scan_doubts(coder_ws, ws_root)
        validation = _validation_verdict(coder_ws)
        task_summary = callback_context.state.get("task_iteration_summary")
        accepted_ids = (
            task_summary.get("accepted_task_ids", [])
            if isinstance(task_summary, dict)
            else []
        )
        accepted_ids = accepted_ids if isinstance(accepted_ids, list) else []

        # Gera doubt sintético se nenhum artefato foi produzido
        if not artifacts:
            doubt_path = coder_ws / "Doubt_Artifact_sem_artefatos.md"
            doubt_path.parent.mkdir(parents=True, exist_ok=True)
            doubt_path.write_text(
                "# Doubt Artifact — Nenhum artefato produzido\n\n"
                "> EXECUÇÃO PAUSADA — INTERVENÇÃO NECESSÁRIA\n\n"
                "## Fase Bloqueada\n**coding**\n\n"
                "## Descrição do Problema\n"
                "O coder não produziu nenhum artefato.\n\n"
                "## Ação Necessária\n"
                "Reprocessar a fase de codificação.\n\n"
                "**Bloqueante:** Sim\n",
                encoding="utf-8",
            )
            doubts = _scan_doubts(coder_ws, ws_root)

        if validation == "fail":
            doubt_path = coder_ws / "Doubt_Artifact_reviewer_bloqueou.md"
            doubt_path.parent.mkdir(parents=True, exist_ok=True)
            doubt_path.write_text(
                "# Doubt Artifact — Reviewer bloqueou a entrega\n\n"
                "> EXECUÇÃO PAUSADA — INTERVENÇÃO NECESSÁRIA\n\n"
                "## Fase Bloqueada\n**coding**\n\n"
                "## Descrição do Problema\n"
                "O reviewer reprovou a entrega. Verifique o relatório de revisão em coder/review/.\n\n"
                "## Ação Necessária\n"
                "Corrigir os problemas apontados pelo reviewer e reprocessar.\n\n"
                "**Bloqueante:** Sim\n",
                encoding="utf-8",
            )
            doubts = _scan_doubts(coder_ws, ws_root)

        status = _derive_status(
            artifacts,
            doubts,
            validation,
            has_accepted_with_caveats=bool(accepted_ids),
        )


        manifest: dict = {
            "phase":      PHASE_NAME,
            "status":     status,
            "artifacts":  artifacts,
            "doubts":     doubts,
            "summary": _build_summary(
                artifacts, doubts, validation, accepted_count=len(accepted_ids)
            ),
        }

        callback_context.state[STATE_KEY] = manifest
        
        manifest_path = coder_ws / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        logger.info(
            "[MANIFEST] coding → %s | %d artefato(s) | %d dúvida(s) | revisão: %s",
            status, len(artifacts), len(doubts), validation,
        )

        existing = list(callback_context.state.get("phase_manifests", []) or [])
        existing.append(manifest)
        callback_context.state["phase_manifests"] = existing

    except Exception as exc:
        logger.warning("[MANIFEST] Falha ao emitir manifesto de coding: %s", exc)
