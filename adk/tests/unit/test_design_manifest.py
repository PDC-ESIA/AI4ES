"""Testes do emissor de Manifesto de Design (Time 2).

Cobre a derivação de status a partir do disco (`build_design_manifest`),
o wiring do `after_agent_callback` no `SequentialAgent` raiz, a escrita no
`session.state` (`design_manifest` local e `phase_manifests` acumulado) e a
doubt bloqueante sintética emitida quando a fase não produz nenhum artefato.

O schema e os invariantes do manifesto vêm de `shared.manifest.PhaseManifest`
— não há mais dataclasses/validação locais (ver decisão em
`docs/Time_2_Design/manifesto-fase-plano-de-acao.md`, itens 3 e 4).

Não usa o runtime ADK: a varredura é uma função pura sobre o filesystem e o
`CallbackContext` é substituído por um duplo mínimo com `.state`.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from shared.manifest import ArtifactItem, DoubtItem, PhaseManifest, PhaseStatus
from src.agents.workflow_design_pipeline.manifest import (
    MANIFEST_FILENAME,
    STATE_KEY,
    _SYNTHETIC_DOUBT_FILENAME,
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
        _write(root / "analysis" / "analise_tecnica_HU-001.md")
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
# Schema + invariantes (delegados a shared.manifest.PhaseManifest)
# ──────────────────────────────────────────────────────────────────────────────

def test_ok_manifesto_serializa_com_campos_do_contrato():
    m = PhaseManifest(
        phase="design",
        status=PhaseStatus.OK,
        artifacts=[ArtifactItem(tipo="analise", id="HU-001", path="workspace_output/design/a.md")],
        summary="ok",
    )
    d = m.model_dump(mode="json")
    assert set(d) >= {"phase", "status", "artifacts", "doubts", "summary"}
    assert d["artifacts"][0] == {
        "tipo": "analise",
        "id": "HU-001",
        "path": "workspace_output/design/a.md",
    }
    assert "session_id" not in d  # não faz parte do contrato compartilhado


def test_invariante_ok_rejeita_doubt_bloqueante():
    with pytest.raises(ValidationError):
        PhaseManifest(
            phase="design",
            status=PhaseStatus.OK,
            artifacts=[ArtifactItem(tipo="analise", id="HU-001", path="a.md")],
            doubts=[DoubtItem(id="D-1", severidade="alta", bloqueante=True, path="d.md")],
        )


def test_invariante_blocked_exige_doubt_bloqueante():
    with pytest.raises(ValidationError):
        PhaseManifest(
            phase="design",
            status=PhaseStatus.BLOCKED,
            artifacts=[],
            doubts=[],
        )


def test_invariante_status_desconhecido_rejeitado():
    with pytest.raises(ValidationError):
        PhaseManifest(phase="design", status="done")


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
    assert any(d.bloqueante for d in m.doubts)


def test_doubt_resolvido_nao_e_bloqueante(tmp_path):
    root = _design_tree(tmp_path, validation="pass", doubt="open")
    m = build_design_manifest(root)
    assert not any(d.bloqueante for d in m.doubts)
    assert m.status == PhaseStatus.OK


def test_status_blocked_quando_nada_produzido_sintetiza_doubt_bloqueante(tmp_path):
    """Regressão do item 4.2 do plano: `blocked` nunca pode sair sem doubt
    bloqueante associada — antes violava o invariante do contrato
    compartilhado quando validado; agora a doubt é sintetizada e persistida
    em disco antes da derivação do status."""
    root = _design_tree(
        tmp_path, analysis=False, diagram=False, report=False, validation=None
    )
    m = build_design_manifest(root)
    assert m.status == PhaseStatus.BLOCKED
    assert m.artifacts == []
    assert len(m.doubts) == 1
    assert m.doubts[0].bloqueante is True

    doubt_file = root / "doubts" / _SYNTHETIC_DOUBT_FILENAME
    assert doubt_file.exists()

    # Não deve derrubar a construção do contrato compartilhado.
    PhaseManifest(
        phase="design",
        status=m.status,
        artifacts=m.artifacts,
        doubts=m.doubts,
        summary=m.summary,
    )


def test_status_blocked_nao_duplica_doubt_sintetica_em_reprocessamento(tmp_path):
    """Rodar build_design_manifest duas vezes sobre o mesmo workspace vazio
    não deve gerar dois arquivos de doubt sintética nem duplicar entradas."""
    root = _design_tree(
        tmp_path, analysis=False, diagram=False, report=False, validation=None
    )
    build_design_manifest(root)
    m2 = build_design_manifest(root)
    assert len(m2.doubts) == 1


def test_backups_e_manifest_json_sao_ignorados(tmp_path):
    root = _design_tree(tmp_path, validation="pass")
    _write(root / "analysis" / "analise_tecnica_HU-001_backup_20250101.md")
    _write(root / MANIFEST_FILENAME, "{}")
    m = build_design_manifest(root)
    paths = [a.path for a in m.artifacts]
    assert not any("_backup_" in p for p in paths)
    assert not any(p.endswith(MANIFEST_FILENAME) for p in paths)


def test_doubt_artifact_solto_em_pasta_de_artefato_nao_conta_como_artefato(tmp_path):
    """Regressão de uma run real (2026-08-20, github_copilot/gpt-4o): um
    Doubt_Artifact_*.md gravado dentro de design/analysis/ (em vez de
    design/doubts/) aparecia DUPLICADO — corretamente em `doubts` e também,
    errado, como `tipo: "analise"` em `artifacts`. A varredura de artefato
    agora exclui qualquer arquivo cujo nome comece com "doubt"."""
    root = _design_tree(tmp_path, validation="pass", doubt=None)
    _write(
        root / "analysis" / "Doubt_Artifact_Clarification.md",
        "# Doubt Artifact — dúvida\n\n**Status:** Pendente\n",
    )
    m = build_design_manifest(root)

    tipos_por_id = {a.id: a.tipo for a in m.artifacts}
    assert "Doubt_Artifact_Clarification" not in tipos_por_id

    doubt_ids = {d.id for d in m.doubts}
    assert "Doubt_Artifact_Clarification" in doubt_ids


def test_analise_tecnica_fora_de_analysis_nao_e_coletada(tmp_path):
    """Regressão da mesma run real: o mapeamento antigo escaneava a raiz de
    design/ para o tipo "analise", mas design_filesystem.py sempre salva em
    design/analysis/ — um arquivo solto na raiz nunca deveria ter sido
    contado (nem sequer detectado, já que não é o local oficial)."""
    root = _design_tree(tmp_path, validation="pass", analysis=False)
    _write(root / "analise_tecnica_HU-001_fora_do_lugar.md")

    m = build_design_manifest(root)

    assert not any(a.tipo == "analise" for a in m.artifacts)


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
    # nada produzido → status blocked (com doubt sintética), sem exceção
    assert emit_design_manifest(ctx) is None
    assert ctx.state[STATE_KEY]["status"] == PhaseStatus.BLOCKED


def test_emissor_acrescenta_em_phase_manifests_sem_perder_anteriores(tmp_path, monkeypatch):
    """Regressão do item 4.1 do plano: o manifesto de Design precisa chegar
    ao orquestrador pelo canal `phase_manifests` (lista), não só sob a chave
    isolada `design_manifest`."""
    _design_tree(tmp_path, validation="pass")
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace_output"))

    ctx = _FakeCtx()
    ctx.state["phase_manifests"] = [
        {"phase": "requirements", "status": "ok", "artifacts": [], "doubts": [], "summary": ""}
    ]

    emit_design_manifest(ctx)

    manifests = ctx.state["phase_manifests"]
    assert len(manifests) == 2
    assert manifests[0]["phase"] == "requirements"
    assert manifests[1]["phase"] == "design"
    assert manifests[1]["status"] == "ok"
    # O item acrescentado precisa validar contra o contrato compartilhado.
    PhaseManifest.model_validate(manifests[1])


def test_session_id_persiste_em_disco_mas_nao_em_phase_manifests(tmp_path, monkeypatch):
    """Resolução do item 5 do plano: `session_id` não é campo oficial de
    `shared.manifest.PhaseManifest` — fica só na cópia local em disco."""
    _design_tree(tmp_path, validation="pass")
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace_output"))

    class _FakeSession:
        id = "sess-123"

    class _FakeInvocationContext:
        session = _FakeSession()

    ctx = _FakeCtx()
    ctx._invocation_context = _FakeInvocationContext()

    emit_design_manifest(ctx)

    appended = ctx.state["phase_manifests"][-1]
    assert "session_id" not in appended
    assert "session_id" not in ctx.state[STATE_KEY]

    manifest_json = json.loads(
        (tmp_path / "workspace_output" / "design" / MANIFEST_FILENAME).read_text(encoding="utf-8")
    )
    assert manifest_json["session_id"] == "sess-123"


def test_root_agent_tem_after_agent_callback_de_manifesto():
    from src.agents.workflow_design_pipeline.agent import agent
    from src.agents.workflow_design_pipeline.manifest import emit_design_manifest

    callbacks = agent.canonical_after_agent_callbacks
    assert emit_design_manifest in callbacks
