"""Manifesto de Fase do Time 2 (Design).

Emissor determinístico do **Manifesto de Fase** — o contrato pequeno e
estruturado que cada Time grava no `session.state` ao terminar, em vez de
repassar o conteúdo volumoso dos artefatos entre fases.

Este módulo define três coisas:

1. **Schema** — dataclasses `ManifestArtifact`, `ManifestDoubt` e
   `PhaseManifest`, com serialização JSON-friendly.
2. **Invariantes** — regras que todo manifesto válido deve respeitar
   (ex.: `status=ok` ⇒ nenhum doubt bloqueante), verificadas por
   `PhaseManifest.validate_invariants()`.
3. **Emissor** — `emit_design_manifest`, um `after_agent_callback` plugado no
   `SequentialAgent` raiz do pipeline de design. Ao final da fase ele varre
   `workspace_output/design/**`, deriva o `status` do resultado da validação e
   dos doubts, monta o manifesto, grava-o em `state["design_manifest"]` e
   persiste uma cópia em `design/manifest.json` para rastreabilidade.

O conteúdo dos artefatos NUNCA entra no manifesto — apenas `path`, `tipo` e
`id`. A próxima fase lê do workspace só os `path` de que precisa.

Layout observado em disco (ver `shared/workspace.py::AGENT_DIRS`):

    workspace_output/design/                 análise técnica (.md)   → tipo "analise"
    workspace_output/design/diagrams/        diagramas Mermaid (.mmd)→ tipo "diagrama"
    workspace_output/design/prototypes/      protótipos (.html/.css) → tipo "prototipo"
    workspace_output/design/reports/         relatórios (.md)        → tipo "relatorio"
    workspace_output/design/validation/      veredicto do validator  → tipo "validacao"
    workspace_output/design/doubts/          Doubt_Artifacts         → doubts
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constantes do contrato
# ──────────────────────────────────────────────────────────────────────────────

PHASE_NAME = "design"

#: Nome do arquivo persistido em disco e chave gravada no session.state.
MANIFEST_FILENAME = "manifest.json"
STATE_KEY = "design_manifest"


class PhaseStatus:
    """Estados canônicos de um manifesto de fase."""

    OK = "ok"            # concluída e auto-validada, sem doubts bloqueantes
    BLOCKED = "blocked"  # doubt bloqueante impede seguir / nada foi produzido
    PARTIAL = "partial"  # produziu algo com pendências não-bloqueantes

    ALL = (OK, BLOCKED, PARTIAL)


#: Marcador usado pelos Doubt_Artifacts para sinalizar bloqueio ativo.
#: Espelha `design_filesystem.STATUS_BLOCKED` / `check_active_blocks`.
_STATUS_BLOCKED_MARKER = "**Status:** Bloqueado"

#: Marcadores textuais do veredicto do validator persistido em design/validation.
_VALIDATION_FAIL_MARKERS = ("REPROVADO", "❌", "valid: false", '"valid": false')
_VALIDATION_PASS_MARKERS = ("APROVADO", "✅", "valid: true", '"valid": true')

#: Backups e artefatos internos que nunca contam como saída da fase.
_BACKUP_PREFIX = "_backup_"
_IGNORED_NAMES = {MANIFEST_FILENAME, ".ai4se_workspace", "io_operations.log"}


class ManifestInvariantError(ValueError):
    """Levantada quando um manifesto viola um invariante do contrato."""


# ──────────────────────────────────────────────────────────────────────────────
# Schema
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ManifestArtifact:
    """Um arquivo persistido pela fase. `path` é relativo à raiz do repo."""

    tipo: str  # "analise" | "diagrama" | "prototipo" | "relatorio" | "validacao"
    id: str
    path: str

    def to_dict(self) -> dict[str, str]:
        return {"tipo": self.tipo, "id": self.id, "path": self.path}


@dataclass
class ManifestDoubt:
    """Uma dúvida aberta pela fase."""

    id: str
    severidade: str  # "alta" | "media" | "baixa"
    bloqueante: bool
    path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "severidade": self.severidade,
            "bloqueante": self.bloqueante,
            "path": self.path,
        }


@dataclass
class PhaseManifest:
    """Manifesto de uma fase do SDLC (aqui, sempre `design`)."""

    phase: str
    status: str
    artifacts: list[ManifestArtifact] = field(default_factory=list)
    doubts: list[ManifestDoubt] = field(default_factory=list)
    summary: str = ""
    session_id: str | None = None

    # ── invariantes ──────────────────────────────────────────────────────────
    def has_blocking_doubt(self) -> bool:
        return any(d.bloqueante for d in self.doubts)

    def validate_invariants(self) -> None:
        """Verifica as regras do contrato. Levanta `ManifestInvariantError`.

        Invariantes:
        - `phase` deve ser o nome canônico da fase.
        - `status` deve ser um dos valores canônicos.
        - Doubt bloqueante ⇒ `status == blocked`.
        - `status == ok` ⇒ nenhum doubt bloqueante (auto-validado).
        - `status == ok` ⇒ ao menos um artefato produzido.
        """
        if self.phase != PHASE_NAME:
            raise ManifestInvariantError(
                f"phase inválida: {self.phase!r} (esperado {PHASE_NAME!r})"
            )
        if self.status not in PhaseStatus.ALL:
            raise ManifestInvariantError(
                f"status inválido: {self.status!r} (esperado um de {PhaseStatus.ALL})"
            )
        if self.has_blocking_doubt() and self.status != PhaseStatus.BLOCKED:
            raise ManifestInvariantError(
                "há doubt bloqueante mas status != 'blocked' "
                f"(status={self.status!r})"
            )
        if self.status == PhaseStatus.OK:
            if self.has_blocking_doubt():
                raise ManifestInvariantError(
                    "status='ok' incompatível com doubt bloqueante"
                )
            if not self.artifacts:
                raise ManifestInvariantError(
                    "status='ok' exige ao menos um artefato produzido"
                )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "phase": self.phase,
            "status": self.status,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "doubts": [d.to_dict() for d in self.doubts],
            "summary": self.summary,
        }
        if self.session_id is not None:
            data["session_id"] = self.session_id
        return data


# ──────────────────────────────────────────────────────────────────────────────
# Varredura do workspace
# ──────────────────────────────────────────────────────────────────────────────

def _design_root() -> Path:
    """Raiz do output de design, respeitando WORKSPACE_OUTPUT_DIR.

    Import tardio de `shared.workspace` para evitar acoplar o schema/invariantes
    (testáveis isoladamente) à camada de workspace.
    """
    from shared.workspace import get_workspace_root

    return get_workspace_root() / PHASE_NAME


def _repo_relative(path: Path, root: Path) -> str:
    """Caminho relativo à raiz do repo (o pai de `workspace_output/`).

    Ex.: `<repo>/adk/workspace_output/design/diagrams/HU-001.mmd`
         → `workspace_output/design/diagrams/HU-001.mmd`.
    Fallback: caminho absoluto, se a relativização não for possível.
    """
    try:
        base = root.parent.parent  # design/ → workspace_output/ → base
        return os.path.relpath(path, base)
    except (ValueError, OSError):
        return str(path)


def _is_relevant_file(f: Path) -> bool:
    return (
        f.is_file()
        and f.name not in _IGNORED_NAMES
        and _BACKUP_PREFIX not in f.name
    )


def _iter_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(p for p in directory.iterdir() if _is_relevant_file(p))


def _extract_id(filename: str) -> str:
    """Deriva um id legível do nome do arquivo (HU-NNN se presente, senão stem)."""
    stem = Path(filename).stem
    m = re.search(r"HU-?\d+", stem, flags=re.IGNORECASE)
    return m.group(0).upper().replace("HU", "HU-").replace("HU--", "HU-") if m else stem


def _collect_artifacts(design_root: Path) -> list[ManifestArtifact]:
    """Varre o subtree de design e classifica cada arquivo por tipo.

    `design/staging` é ignorado — é área de rascunho transitória do io_agent.
    """
    mapping = [
        ("analise", design_root, False),            # apenas o nível raiz de design/
        ("diagrama", design_root / "diagrams", True),
        ("prototipo", design_root / "prototypes", True),
        ("relatorio", design_root / "reports", True),
        ("validacao", design_root / "validation", True),
    ]
    artifacts: list[ManifestArtifact] = []
    for tipo, directory, recurse in mapping:
        files = (
            [p for p in directory.rglob("*") if _is_relevant_file(p)]
            if recurse
            else _iter_files(directory)
        )
        for f in sorted(files):
            artifacts.append(
                ManifestArtifact(
                    tipo=tipo,
                    id=_extract_id(f.name),
                    path=_repo_relative(f, design_root),
                )
            )
    return artifacts


def _collect_doubts(design_root: Path) -> list[ManifestDoubt]:
    """Localiza Doubt_Artifacts no subtree de design e classifica bloqueio.

    Espelha a convenção de `design_filesystem.check_active_blocks`: um doubt é
    bloqueante se seu conteúdo contém `**Status:** Bloqueado`.
    """
    doubts: list[ManifestDoubt] = []
    for f in sorted(design_root.rglob("*")):
        if not _is_relevant_file(f):
            continue
        if not f.name.lower().startswith("doubt"):
            continue
        try:
            content = f.read_text(encoding="utf-8")
        except OSError:
            content = ""
        bloqueante = _STATUS_BLOCKED_MARKER in content
        doubts.append(
            ManifestDoubt(
                id=_extract_id(f.name),
                severidade="alta" if bloqueante else "media",
                bloqueante=bloqueante,
                path=_repo_relative(f, design_root),
            )
        )
    return doubts


def _validation_verdict(design_root: Path) -> str:
    """Lê o veredicto do validator em design/validation.

    Retorna "pass", "fail" ou "absent". O `ok` do manifesto exige "pass" —
    espelha a regra do design doc: "status=ok só após a validação passar".
    """
    validation_dir = design_root / "validation"
    files = [p for p in _iter_files(validation_dir)]
    if not files:
        return "absent"

    saw_pass = False
    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
        except OSError:
            continue
        if any(marker in content for marker in _VALIDATION_FAIL_MARKERS):
            return "fail"
        if any(marker in content for marker in _VALIDATION_PASS_MARKERS):
            saw_pass = True
    return "pass" if saw_pass else "absent"


# ──────────────────────────────────────────────────────────────────────────────
# Derivação de status (determinística)
# ──────────────────────────────────────────────────────────────────────────────

def _derive_status(
    artifacts: list[ManifestArtifact],
    doubts: list[ManifestDoubt],
    validation: str,
) -> str:
    """Deriva o status conforme os invariantes do contrato.

    Precedência:
    1. Doubt bloqueante  → BLOCKED (invariante do contrato).
    2. Nenhum artefato   → BLOCKED (a fase não produziu design).
    3. Validação reprovada / ausente → PARTIAL (produziu, sem validação verde).
    4. Validação aprovada → OK.
    """
    if any(d.bloqueante for d in doubts):
        return PhaseStatus.BLOCKED
    if not artifacts:
        return PhaseStatus.BLOCKED
    if validation == "pass":
        return PhaseStatus.OK
    return PhaseStatus.PARTIAL


def _build_summary(
    status: str,
    artifacts: list[ManifestArtifact],
    doubts: list[ManifestDoubt],
    validation: str,
) -> str:
    counts: dict[str, int] = {}
    for a in artifacts:
        counts[a.tipo] = counts.get(a.tipo, 0) + 1
    parts = ", ".join(f"{n} {tipo}" for tipo, n in sorted(counts.items())) or "nenhum artefato"
    n_bloq = sum(1 for d in doubts if d.bloqueante)
    doubt_txt = (
        f"{len(doubts)} doubt(s) ({n_bloq} bloqueante(s))" if doubts else "sem doubts"
    )
    return (
        f"Fase design concluída com status '{status}'. "
        f"Artefatos: {parts}. Validação: {validation}. {doubt_txt}."
    )


def build_design_manifest(
    design_root: Path | None = None,
    session_id: str | None = None,
) -> PhaseManifest:
    """Monta (e valida) o manifesto de design a partir do disco.

    Função pura sobre o filesystem — testável sem o runtime ADK.
    """
    root = design_root if design_root is not None else _design_root()
    artifacts = _collect_artifacts(root)
    doubts = _collect_doubts(root)
    validation = _validation_verdict(root)
    status = _derive_status(artifacts, doubts, validation)
    summary = _build_summary(status, artifacts, doubts, validation)

    manifest = PhaseManifest(
        phase=PHASE_NAME,
        status=status,
        artifacts=artifacts,
        doubts=doubts,
        summary=summary,
        session_id=session_id,
    )
    manifest.validate_invariants()
    return manifest


# ──────────────────────────────────────────────────────────────────────────────
# Emissor — after_agent_callback
# ──────────────────────────────────────────────────────────────────────────────

def _persist_manifest(design_root: Path, manifest: PhaseManifest) -> None:
    """Grava uma cópia legível do manifesto em design/manifest.json."""
    try:
        design_root.mkdir(parents=True, exist_ok=True)
        target = design_root / MANIFEST_FILENAME
        target.write_text(
            json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:  # persistência é best-effort — o state é a fonte de verdade
        logger.warning("[design_manifest] falha ao persistir manifest.json: %s", exc)


def _session_id_from(callback_context: Any) -> str | None:
    try:
        return callback_context._invocation_context.session.id
    except AttributeError:
        return None


def emit_design_manifest(callback_context: Any) -> None:
    """`after_agent_callback` do pipeline de design.

    Varre o workspace, deriva o manifesto e grava-o em `state["design_manifest"]`
    (o handoff para a próxima fase) e em `design/manifest.json` (rastreabilidade).

    Retorna `None` para não substituir a saída do agente (contrato ADK: um
    callback que retorna `types.Content` sobrescreve a resposta; `None` a mantém).
    """
    try:
        design_root = _design_root()
        session_id = _session_id_from(callback_context)
        manifest = build_design_manifest(design_root, session_id=session_id)
    except Exception as exc:  # emissor nunca deve derrubar o pipeline
        logger.exception("[design_manifest] falha ao emitir manifesto: %s", exc)
        return None

    try:
        callback_context.state[STATE_KEY] = manifest.to_dict()
    except Exception as exc:
        logger.warning("[design_manifest] falha ao gravar no state: %s", exc)

    _persist_manifest(design_root, manifest)
    logger.info(
        "[design_manifest] status=%s artefatos=%d doubts=%d",
        manifest.status,
        len(manifest.artifacts),
        len(manifest.doubts),
    )
    return None
