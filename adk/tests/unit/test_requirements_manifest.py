"""Testes do emissor de manifesto — Agente de Requisitos (Time 1).

Cobre:
- varredura de artefatos por tipo
- paths relativos ao workspace root
- derivação de status (ok / partial / blocked)
- emissão para ctx.state + persistência em disco
- degradação silenciosa em caso de falha
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.requirements.manifest import (
    _build_summary,
    _derive_status,
    _scan_artifacts,
    _scan_doubts,
    emit_requirements_manifest,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ws(tmp_path: Path, files: dict[str, str]) -> Path:
    """Cria estrutura de workspace temporária com os arquivos informados."""
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# _scan_artifacts
# ---------------------------------------------------------------------------

def test_scan_detecta_hu_e_rf(tmp_path):
    _make_ws(tmp_path, {
        "HUs/HU-001.md": "# HU-001",
        "RFs/RF-001.md": "# RF-001",
    })
    arts = _scan_artifacts(tmp_path, tmp_path)
    tipos = {a["tipo"] for a in arts}
    assert "HU" in tipos and "RF" in tipos


def test_scan_detecta_todos_os_tipos(tmp_path):
    _make_ws(tmp_path, {
        "HUs/HU-001.md":  "x",
        "RFs/RF-001.md":  "x",
        "RNFs/RNF-001.md": "x",
        "RNs/RN-001.md":  "x",
        "glossario/Glossario.md": "x",
    })
    arts = _scan_artifacts(tmp_path, tmp_path)
    tipos = {a["tipo"] for a in arts}
    assert tipos == {"HU", "RF", "RNF", "RN", "Glossario"}


def test_scan_path_e_relativo(tmp_path):
    _make_ws(tmp_path, {"HUs/HU-001.md": "x"})
    arts = _scan_artifacts(tmp_path, tmp_path)
    assert arts, "deve encontrar ao menos um artefato"
    assert not Path(arts[0]["path"]).is_absolute()


def test_scan_workspace_vazio_retorna_lista_vazia(tmp_path):
    arts = _scan_artifacts(tmp_path, tmp_path)
    assert arts == []


def test_scan_glossario_fallback_raiz(tmp_path):
    """Glossario.md na raiz (legado) também deve ser detectado."""
    _make_ws(tmp_path, {"Glossario.md": "# Glossário"})
    arts = _scan_artifacts(tmp_path, tmp_path)
    assert any(a["tipo"] == "Glossario" for a in arts)


def test_scan_doubts_detecta_nao_bloqueante(tmp_path):
    content = """# Doubt_Artifact
- **Bloqueante:** N\u00e3o
- **Status:** Aberta
"""
    _make_ws(tmp_path, {"Doubt_Artifact_D-001_20260723_120000_000000.md": content})
    doubts = _scan_doubts(tmp_path, tmp_path)
    assert len(doubts) == 1
    assert doubts[0]["bloqueante"] is False
    assert doubts[0]["severidade"] == "media"


def test_scan_doubts_detecta_bloqueante(tmp_path):
    content = """# Doubt_Artifact
- **Bloqueante:** Sim
- **Status:** Aberta
"""
    _make_ws(tmp_path, {"Doubt_Artifact_D-001_20260723_120000_000000.md": content})
    doubts = _scan_doubts(tmp_path, tmp_path)
    assert doubts[0]["bloqueante"] is True
    assert doubts[0]["severidade"] == "alta"


def test_scan_doubts_vazio_sem_arquivos(tmp_path):
    assert _scan_doubts(tmp_path, tmp_path) == []



def test_status_ok_sem_doubts():
    arts = [{"tipo": "HU", "id": "HU-001", "path": "x"}]
    assert _derive_status(arts, []) == "ok"


def test_status_blocked_doubt_bloqueante():
    arts   = [{"tipo": "HU", "id": "HU-001", "path": "x"}]
    doubts = [{"id": "D-001", "severidade": "alta", "bloqueante": True, "path": "y"}]
    assert _derive_status(arts, doubts) == "blocked"


def test_status_partial_doubt_nao_bloqueante():
    arts   = [{"tipo": "HU", "id": "HU-001", "path": "x"}]
    doubts = [{"id": "D-001", "severidade": "baixa", "bloqueante": False, "path": "y"}]
    assert _derive_status(arts, doubts) == "partial"


def test_status_blocked_sem_artefatos():
    assert _derive_status([], []) == "blocked"


def test_status_blocked_sem_artefatos_com_doubt():
    doubts = [{"id": "D-001", "severidade": "alta", "bloqueante": True, "path": "y"}]
    assert _derive_status([], doubts) == "blocked"


# ---------------------------------------------------------------------------
# _build_summary
# ---------------------------------------------------------------------------

def test_summary_conta_tipos():
    arts = [
        {"tipo": "HU",  "id": "HU-001", "path": "x"},
        {"tipo": "HU",  "id": "HU-002", "path": "x"},
        {"tipo": "RF",  "id": "RF-001", "path": "x"},
    ]
    summary = _build_summary(arts, [])
    assert "2 HU" in summary and "1 RF" in summary


def test_summary_menciona_duvidas():
    arts   = [{"tipo": "HU", "id": "HU-001", "path": "x"}]
    doubts = [{"id": "D-001", "severidade": "media", "bloqueante": False, "path": "y"}]
    assert "dúvida" in _build_summary(arts, doubts)


# ---------------------------------------------------------------------------
# emit_requirements_manifest
# ---------------------------------------------------------------------------

def test_emit_grava_state_e_arquivo(tmp_path):
    _make_ws(tmp_path, {"HUs/HU-001.md": "# HU-001"})
    ctx = MagicMock()
    ctx.state = {}

    with patch("src.agents.requirements.manifest.get_agent_workspace", return_value=tmp_path), \
         patch("src.agents.requirements.manifest.get_workspace_root", return_value=tmp_path):
        emit_requirements_manifest(callback_context=ctx)

    assert "requirements_manifest" in ctx.state
    assert ctx.state["requirements_manifest"]["phase"] == "requirements"
    assert ctx.state["requirements_manifest"]["status"] == "ok"
    assert (tmp_path / "manifest.json").exists()


def test_emit_manifest_json_valido(tmp_path):
    import json
    _make_ws(tmp_path, {
        "HUs/HU-001.md": "x",
        "RFs/RF-001.md": "x",
    })
    ctx = MagicMock()
    ctx.state = {}

    with patch("src.agents.requirements.manifest.get_agent_workspace", return_value=tmp_path), \
         patch("src.agents.requirements.manifest.get_workspace_root", return_value=tmp_path):
        emit_requirements_manifest(callback_context=ctx)

    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["phase"] == "requirements"
    assert len(manifest["artifacts"]) == 2
    assert manifest["status"] == "ok"


def test_emit_nao_quebra_pipeline_em_falha(tmp_path):
    """Falha no emissor não deve propagar exceção — pipeline deve continuar."""
    ctx = MagicMock()
    ctx.state = {}

    with patch(
        "src.agents.requirements.manifest.get_agent_workspace",
        side_effect=RuntimeError("erro simulado"),
    ):
        emit_requirements_manifest(callback_context=ctx)  # não deve lançar
