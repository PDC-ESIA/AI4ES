"""Testes do emissor de Manifesto de Design (Time 2).

Cobre schema, invariantes e derivação de status a partir do disco
(`build_design_manifest`), além do wiring do `after_agent_callback` no
`SequentialAgent` raiz e da escrita no `session.state`.

Não usa o runtime ADK: a varredura é uma função pura sobre o filesystem e o
`CallbackContext` é substituído por um duplo mínimo com `.state`.
"""

from pathlib import Path

import pytest

from src.agents.workflow_design_pipeline.manifest import (
    ManifestArtifact,
    ManifestDoubt,
    ManifestInvariantError,
    PhaseManifest,
    PhaseStatus,
    STATE_KEY,
    MANIFEST_FILENAME,
    build_design_manifest,
    emit_design_manifest,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de fixture — monta uma árvore design/ em tmp_path
# ──────────────────────────────────────────────────────────────────────────────

def _write(path: Path, content: str = "conteudo") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _design_tree(
    tmp_path: Path,
    *,
    analysis: bool = True,
    diagram: bool = True,
    report: bool = True,
    validation: str | None = "pass",  # "pass" | "fail" | None
    doubt: str | None = None,         # "blocked" | "open" | None
) -> Path:
    """Cria workspace_output/design/** e retorna o design_root."""
    root = tmp_path / "workspace_output" / "design"
    root.mkdir(parents=True, exist_ok=True)
    if analysis:
        _write(root / "analise_tecnica_HU-001.md")
    if diagram:
        _write(root / "diagrams" / "diagrama_HU-001.mmd")
    if report:
        _write(root / "reports" / "relatorio_HU-001.md")
    if validation == "pass":
        _write(root / "validation" / "veredicto.md", "✅ APROVADO — tudo certo")
    elif validation == "fail":
        _write(root / "validation" / "veredicto.md", "❌ REPROVADO — grammar")
    if doubt == "blocked":
        _write(root / "doubts" / "Doubt_Artifact_HU-002.md", "**Status:** Bloqueado")
    elif doubt == "open":
        _write(root / "doubts" / "Doubt_Artifact_HU-003.md", "**Status:** Resolvido")
    return root


# ──────────────────────────────────────────────────────────────────────────────
# Schema + invariantes
# ──────────────────────────────────────────────────────────────────────────────

def test_ok_manifesto_serializa_com_campos_do_contrato():
    m = PhaseManifest(
        phase="design",
        status=PhaseStatus.OK,
        artifacts=[ManifestArtifact("analise", "HU-001", "workspace_output/design/a.md")],
        summary="ok",
    )
    m.validate_invariants()
    d = m.to_dict()
    assert set(d) >= {"phase", "status", "artifacts", "doubts", "summary"}
    assert d["artifacts"][0] == {
        "tipo": "analise",
        "id": "HU-001",
        "path": "workspace_output/design/a.md",
    }


def test_invariante_doubt_bloqueante_exige_status_blocked():
    m = PhaseManifest(
        phase="design",
        status=PhaseStatus.PARTIAL,
        artifacts=[ManifestArtifact("analise", "HU-001", "a.md")],
        doubts=[ManifestDoubt("D-1", "alta", True, "d.md")],
    )
    with pytest.raises(ManifestInvariantError):
        m.validate_invariants()


def test_invariante_ok_exige_algum_artefato():
    m = PhaseManifest(phase="design", status=PhaseStatus.OK, artifacts=[])
    with pytest.raises(ManifestInvariantError):
        m.validate_invariants()


def test_invariante_status_desconhecido_rejeitado():
    m = PhaseManifest(phase="design", status="done")
    with pytest.raises(ManifestInvariantError):
        m.validate_invariants()


# ──────────────────────────────────────────────────────────────────────────────
# Derivação de status a partir do disco
# ──────────────────────────────────────────────────────────────────────────────

def test_status_ok_quando_validacao_passa_sem_doubt(tmp_path):
    root = _design_tree(tmp_path, validation="pass", doubt=None)
    m = build_design_manifest(root)
    assert m.status == PhaseStatus.OK
    tipos = {a.tipo for a in m.artifacts}
    assert {"analise", "diagrama", "relatorio", "validacao"} <= tipos


def test_status_partial_quando_validacao_ausente(tmp_path):
    root = _design_tree(tmp_path, validation=None, doubt=None)
    m = build_design_manifest(root)
    assert m.status == PhaseStatus.PARTIAL


def test_status_partial_quando_validacao_reprova(tmp_path):
    root = _design_tree(tmp_path, validation="fail", doubt=None)
    m = build_design_manifest(root)
    assert m.status == PhaseStatus.PARTIAL


def test_status_blocked_quando_doubt_bloqueante_mesmo_com_validacao_verde(tmp_path):
    root = _design_tree(tmp_path, validation="pass", doubt="blocked")
    m = build_design_manifest(root)
    assert m.status == PhaseStatus.BLOCKED
    assert m.has_blocking_doubt()
    # invariante segura: build nunca devolve ok com bloqueio
    m.validate_invariants()


def test_doubt_resolvido_nao_e_bloqueante(tmp_path):
    root = _design_tree(tmp_path, validation="pass", doubt="open")
    m = build_design_manifest(root)
    assert not m.has_blocking_doubt()
    assert m.status == PhaseStatus.OK


def test_status_blocked_quando_nada_produzido(tmp_path):
    root = _design_tree(
        tmp_path, analysis=False, diagram=False, report=False, validation=None
    )
    m = build_design_manifest(root)
    assert m.status == PhaseStatus.BLOCKED
    assert m.artifacts == []


def test_backups_e_manifest_json_sao_ignorados(tmp_path):
    root = _design_tree(tmp_path, validation="pass")
    _write(root / "analise_tecnica_HU-001_backup_20250101.md")
    _write(root / MANIFEST_FILENAME, "{}")
    m = build_design_manifest(root)
    paths = [a.path for a in m.artifacts]
    assert not any("_backup_" in p for p in paths)
    assert not any(p.endswith(MANIFEST_FILENAME) for p in paths)


# ──────────────────────────────────────────────────────────────────────────────
# Emissor (after_agent_callback) + wiring
# ──────────────────────────────────────────────────────────────────────────────

class _FakeCtx:
    """Duplo mínimo de CallbackContext: expõe apenas `.state`."""

    def __init__(self):
        self.state = {}


def test_emissor_grava_state_e_persiste_json(tmp_path, monkeypatch):
    _design_tree(tmp_path, validation="pass")
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace_output"))

    ctx = _FakeCtx()
    result = emit_design_manifest(ctx)

    assert result is None  # não sobrescreve a saída do agente
    assert STATE_KEY in ctx.state
    assert ctx.state[STATE_KEY]["status"] == PhaseStatus.OK

    manifest_json = tmp_path / "workspace_output" / "design" / MANIFEST_FILENAME
    assert manifest_json.exists()


def test_emissor_nao_derruba_pipeline_sem_workspace(tmp_path, monkeypatch):
    # Aponta para um workspace inexistente: emissor deve degradar sem exceção.
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "vazio"))
    ctx = _FakeCtx()
    # nada produzido → status blocked, sem exceção
    assert emit_design_manifest(ctx) is None
    assert ctx.state[STATE_KEY]["status"] == PhaseStatus.BLOCKED


def test_root_agent_tem_after_agent_callback_de_manifesto():
    from src.agents.workflow_design_pipeline.agent import agent
    from src.agents.workflow_design_pipeline.manifest import emit_design_manifest

    callbacks = agent.canonical_after_agent_callbacks
    assert emit_design_manifest in callbacks
