"""Manifesto de Fase do Time 2 (Design).

Emissor determinístico do **Manifesto de Fase** — o contrato pequeno e
estruturado que cada Time grava no `session.state` ao terminar, em vez de
repassar o conteúdo volumoso dos artefatos entre fases.

Este módulo define duas coisas:

1. **Varredura + derivação** — funções puras que varrem
   `workspace_output/design/**`, coletam artefatos e doubts, e derivam o
   `status` da fase a partir do resultado da validação e das doubts. O
   schema e os invariantes do manifesto (`phase`, `status`, `artifacts`,
   `doubts`, `summary`) vêm de `shared.manifest.PhaseManifest` — a mesma
   fonte de verdade usada por Requisitos, Codificação e QA — para que as
   quatro fases produzam um contrato idêntico e validável pelo orquestrador.
2. **Emissor** — `emit_design_manifest`, um `after_agent_callback` plugado no
   `SequentialAgent` raiz do pipeline de design. Ao final da fase ele monta o
   manifesto, grava-o em `state["design_manifest"]` (persistência/rastreio
   local, mantido por compatibilidade), acrescenta-o à lista acumulada em
   `state["phase_manifests"]` (o canal que o orquestrador de fato repassa
   entre fases — ver `orchestrator/_helpers.py::_merge_state_delta`) e
   persiste uma cópia em `design/manifest.json` para rastreabilidade.

O conteúdo dos artefatos NUNCA entra no manifesto — apenas `path`, `tipo` e
`id`. A próxima fase lê do workspace só os `path` de que precisa.

Layout observado em disco (ver `shared/tools/design_filesystem.py::_resolve_dirs`,
fonte de verdade de onde cada tipo de arquivo é de fato salvo):

    workspace_output/design/analysis/        análise técnica (.md)   → tipo "analise"
    workspace_output/design/diagrams/        diagramas Mermaid (.mmd)→ tipo "diagrama"
    workspace_output/design/prototypes/      protótipos (.html/.css) → tipo "prototipo"
    workspace_output/design/reports/         relatórios (.md)        → tipo "relatorio"
    workspace_output/design/validation/      veredicto do validator  → tipo "validacao"
    workspace_output/design/doubts/          Doubt_Artifacts         → doubts

Arquivos cujo nome começa com "doubt" (case-insensitive) nunca contam como
artefato, mesmo que estejam soltos numa pasta de artefato (ex.: um Doubt
Artifact gravado direto em design/analysis/ por engano) — só entram na lista
de `doubts`. Confirmado por uma run real: um Doubt Artifact mal-nomeado
(sem o prefixo `Doubt_Artifact_`) e outro corretamente nomeado apareciam
duplicados como `tipo: "analise"` antes desta exclusão.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from shared.manifest import ArtifactItem, DoubtItem, PhaseManifest, PhaseStatus

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constantes do contrato
# ──────────────────────────────────────────────────────────────────────────────

PHASE_NAME = "design"

#: Nome do arquivo persistido em disco e chave gravada no session.state.
MANIFEST_FILENAME = "manifest.json"
STATE_KEY = "design_manifest"

#: Marcador usado pelos Doubt_Artifacts para sinalizar bloqueio ativo.
#: Espelha `design_filesystem.STATUS_BLOCKED` / `check_active_blocks`.
_STATUS_BLOCKED_MARKER = "**Status:** Bloqueado"

#: Marcadores textuais do veredicto do validator persistido em design/validation.
_VALIDATION_FAIL_MARKERS = ("REPROVADO", "❌", "valid: false", '"valid": false')
_VALIDATION_PASS_MARKERS = ("APROVADO", "✅", "valid: true", '"valid": true')

#: Backups e artefatos internos que nunca contam como saída da fase.
_BACKUP_PREFIX = "_backup_"
_IGNORED_NAMES = {MANIFEST_FILENAME, ".ai4se_workspace", "io_operations.log"}

#: Doubt sintética gravada quando a fase não produz nenhum artefato — o
#: invariante do contrato (status=blocked ⇒ ao menos uma doubt bloqueante)
#: exige que o motivo do bloqueio seja sempre rastreável como doubt, nunca
#: implícito só no status.
_SYNTHETIC_DOUBT_FILENAME = "Doubt_Artifact_fase_sem_artefatos.md"


# ──────────────────────────────────────────────────────────────────────────────
# Varredura do workspace
# ──────────────────────────────────────────────────────────────────────────────

def _design_root() -> Path:
    """Raiz do output de design, respeitando WORKSPACE_OUTPUT_DIR.

    Import tardio de `shared.workspace` para evitar acoplar a varredura
    (testável isoladamente) à camada de workspace.
    """
    from shared.workspace import get_workspace_root

    return get_workspace_root() / PHASE_NAME


def _repo_relative(path: Path, root: Path) -> str:
    """Caminho relativo à raiz do workspace (`workspace_output/`), com
    separador normalizado ("/") — mesmo padrão de
    `requirements/manifest.py::_rel_path` e
    `workflow_coding_review/manifest.py::_scan_artifacts`, para que o
    orquestrador e as fases seguintes resolvam os três manifestos da
    mesma forma.

    Ex.: `<repo>/adk/workspace_output/design/diagrams/HU-001.mmd`
         → `design/diagrams/HU-001.mmd`.
    Fallback: caminho absoluto, se a relativização não for possível.
    """
    try:
        base = root.parent  # design/ → workspace_output/
        return os.path.relpath(path, base).replace("\\", "/")
    except (ValueError, OSError):
        return str(path)


def _is_relevant_file(f: Path) -> bool:
    return (
        f.is_file()
        and f.name not in _IGNORED_NAMES
        and _BACKUP_PREFIX not in f.name
    )


def _is_doubt_filename(name: str) -> bool:
    """True se o nome do arquivo segue a convenção de Doubt Artifact.

    Usado para excluir doubts de todas as varreduras de artefato — um Doubt
    Artifact que caia (por engano ou por convenção do agente que o gerou)
    dentro de uma pasta de artefato (`analysis/`, `validation/` etc.) nunca
    deve ser contado como entregável.
    """
    return name.lower().startswith("doubt")


def _iter_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        p for p in directory.iterdir()
        if _is_relevant_file(p) and not _is_doubt_filename(p.name)
    )


def _extract_id(filename: str) -> str:
    """Deriva um id legível do nome do arquivo (HU-NNN se presente, senão stem)."""
    stem = Path(filename).stem
    m = re.search(r"HU-?\d+", stem, flags=re.IGNORECASE)
    return m.group(0).upper().replace("HU", "HU-").replace("HU--", "HU-") if m else stem


def _collect_artifacts(design_root: Path) -> list[ArtifactItem]:
    """Varre o subtree de design e classifica cada arquivo por tipo.

    `design/staging` é ignorado — é área de rascunho transitória do io_agent.
    """
    mapping = [
        # analise: design_filesystem.py::_resolve_dirs salva sempre em
        # analysis/ (ANALYSIS_DIR) — nunca solto na raiz de design/.
        ("analise", design_root / "analysis", True),
        ("diagrama", design_root / "diagrams", True),
        ("prototipo", design_root / "prototypes", True),
        ("relatorio", design_root / "reports", True),
        ("validacao", design_root / "validation", True),
    ]
    artifacts: list[ArtifactItem] = []
    for tipo, directory, recurse in mapping:
        files = (
            [
                p for p in directory.rglob("*")
                if _is_relevant_file(p) and not _is_doubt_filename(p.name)
            ]
            if recurse
            else _iter_files(directory)
        )
        for f in sorted(files):
            artifacts.append(
                ArtifactItem(
                    tipo=tipo,
                    id=_extract_id(f.name),
                    path=_repo_relative(f, design_root),
                )
            )
    return artifacts


def _collect_doubts(design_root: Path) -> list[DoubtItem]:
    """Localiza Doubt_Artifacts no subtree de design e classifica bloqueio.

    Espelha a convenção de `design_filesystem.check_active_blocks`: um doubt é
    bloqueante se seu conteúdo contém `**Status:** Bloqueado`.
    """
    doubts: list[DoubtItem] = []
    for f in sorted(design_root.rglob("*")):
        if not _is_relevant_file(f):
            continue
        if not _is_doubt_filename(f.name):
            continue
        try:
            content = f.read_text(encoding="utf-8")
        except OSError:
            content = ""
        bloqueante = _STATUS_BLOCKED_MARKER in content
        doubts.append(
            DoubtItem(
                id=_extract_id(f.name),
                severidade="alta" if bloqueante else "media",
                bloqueante=bloqueante,
                path=_repo_relative(f, design_root),
            )
        )
    return doubts


def _write_synthetic_blocking_doubt(design_root: Path) -> None:
    """Registra em disco uma doubt bloqueante sintética quando a fase não
    produziu nenhum artefato.

    Sem isso, `_derive_status` retornaria `blocked` sem nenhuma doubt
    associada — o que viola o invariante de `shared.manifest.PhaseManifest`
    (`status=blocked` exige ao menos uma doubt bloqueante) e faz o
    `PhaseManifest(...)` levantar `ValidationError` na construção.
    """
    doubts_dir = design_root / "doubts"
    doubt_path = doubts_dir / _SYNTHETIC_DOUBT_FILENAME
    if doubt_path.exists():
        return
    doubts_dir.mkdir(parents=True, exist_ok=True)
    doubt_path.write_text(
        "# Doubt Artifact — Fase de design sem artefatos\n\n"
        f"{_STATUS_BLOCKED_MARKER}\n\n"
        "## Descrição do Problema\n"
        "A fase de design não produziu nenhum artefato (análise técnica, "
        "diagrama, protótipo ou relatório).\n\n"
        "## Ação Necessária\n"
        "Reprocessar a fase de design.\n\n"
        "**Bloqueante:** Sim\n",
        encoding="utf-8",
    )


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
    artifacts: list[ArtifactItem],
    doubts: list[DoubtItem],
    validation: str,
) -> PhaseStatus:
    """Deriva o status conforme os invariantes do contrato.

    Precedência:
    1. Doubt bloqueante  → BLOCKED (invariante do contrato).
    2. Nenhum artefato   → BLOCKED (rede de segurança; em condições normais
       `build_design_manifest` já sintetizou uma doubt bloqueante antes de
       chegar aqui — ver `_write_synthetic_blocking_doubt` — então este
       branch só é alcançado se a escrita da doubt sintética falhar).
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
    status: PhaseStatus,
    artifacts: list[ArtifactItem],
    doubts: list[DoubtItem],
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
        f"Fase design concluída com status '{status.value}'. "
        f"Artefatos: {parts}. Validação: {validation}. {doubt_txt}."
    )


def build_design_manifest(design_root: Path | None = None) -> PhaseManifest:
    """Monta (e valida) o manifesto de design a partir do disco.

    Função sobre o filesystem — testável sem o runtime ADK. Quando nenhum
    artefato foi produzido e ainda não há doubt bloqueante registrada, grava
    uma doubt sintética antes de derivar o status (ver
    `_write_synthetic_blocking_doubt`), para nunca violar o invariante
    `status=blocked ⇒ doubt bloqueante` de `shared.manifest.PhaseManifest`.

    A validação do schema/invariantes é feita por `PhaseManifest` (pydantic)
    na própria construção — não há verificação duplicada aqui.
    """
    root = design_root if design_root is not None else _design_root()
    artifacts = _collect_artifacts(root)
    doubts = _collect_doubts(root)

    if not artifacts and not any(d.bloqueante for d in doubts):
        _write_synthetic_blocking_doubt(root)
        doubts = _collect_doubts(root)

    validation = _validation_verdict(root)
    status = _derive_status(artifacts, doubts, validation)
    summary = _build_summary(status, artifacts, doubts, validation)

    return PhaseManifest(
        phase=PHASE_NAME,
        status=status,
        artifacts=artifacts,
        doubts=doubts,
        summary=summary,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Emissor — after_agent_callback
# ──────────────────────────────────────────────────────────────────────────────

def _persist_manifest(
    design_root: Path,
    manifest: PhaseManifest,
    session_id: str | None = None,
) -> None:
    """Grava uma cópia legível do manifesto em design/manifest.json.

    `session_id` é anexado apenas nesta cópia local de rastreabilidade — não
    faz parte do contrato compartilhado (`shared.manifest.PhaseManifest` não
    tem esse campo), então nunca é incluído no manifesto acrescentado a
    `state["phase_manifests"]`.
    """
    try:
        design_root.mkdir(parents=True, exist_ok=True)
        data = manifest.model_dump(mode="json")
        if session_id is not None:
            data["session_id"] = session_id
        target = design_root / MANIFEST_FILENAME
        target.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
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

    Varre o workspace, deriva o manifesto e:
    1. grava em `state["design_manifest"]` (persistência/rastreio local);
    2. acrescenta em `state["phase_manifests"]` — o canal que o orquestrador
       de fato repassa entre fases (`_merge_state_delta` só acumula em lista
       a chave literal `phase_manifests`; qualquer outra chave fica isolada);
    3. persiste uma cópia em `design/manifest.json`.

    Retorna `None` para não substituir a saída do agente (contrato ADK: um
    callback que retorna `types.Content` sobrescreve a resposta; `None` a mantém).
    """
    try:
        design_root = _design_root()
        manifest = build_design_manifest(design_root)
    except Exception as exc:  # emissor nunca deve derrubar o pipeline
        logger.exception("[design_manifest] falha ao emitir manifesto: %s", exc)
        return None

    manifest_dict = manifest.model_dump(mode="json")

    try:
        callback_context.state[STATE_KEY] = manifest_dict
    except Exception as exc:
        logger.warning("[design_manifest] falha ao gravar no state: %s", exc)

    try:
        existing = list(callback_context.state.get("phase_manifests", []) or [])
        # Reexecução da fase substitui a entrada anterior em vez de duplicá-la
        # — mesmo padrão de requirements/manifest.py::emit_requirements_manifest.
        existing = [
            m for m in existing
            if not (isinstance(m, dict) and m.get("phase") == PHASE_NAME)
        ]
        existing.append(manifest_dict)
        callback_context.state["phase_manifests"] = existing
    except Exception as exc:
        logger.warning("[design_manifest] falha ao acrescentar em phase_manifests: %s", exc)

    session_id = _session_id_from(callback_context)
    _persist_manifest(design_root, manifest, session_id=session_id)
    logger.info(
        "[design_manifest] status=%s artefatos=%d doubts=%d",
        manifest.status.value,
        len(manifest.artifacts),
        len(manifest.doubts),
    )
    return None
