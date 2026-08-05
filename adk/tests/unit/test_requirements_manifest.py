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


# ---------------------------------------------------------------------------
# Glossário — artefato opcional nesta fase
# ---------------------------------------------------------------------------

def _doubt_md(artefato: str, bloqueante: str = "Sim") -> str:
    return f"""# Doubt_Artifact

### D-VAL-001

- **Artefato afetado:** [{artefato}]
- **Dúvida:** O glossário não foi encontrado no repositório.
- **Bloqueante:** {bloqueante}
- **Status:** Aberta
"""


@pytest.mark.parametrize("artefato", ["Glossario", "Glossário", "Glossary"])
def test_doubt_sobre_glossario_perde_o_poder_de_veto(tmp_path, artefato):
    """Glossário não é obrigatório agora: sua ausência não pode barrar a fase."""
    _make_ws(tmp_path, {
        "Doubt_Artifact_D-VAL-001_20260804_223439_620865.md": _doubt_md(artefato),
    })
    doubts = _scan_doubts(tmp_path, tmp_path)

    assert doubts[0]["bloqueante"] is False
    assert doubts[0]["severidade"] == "media"


def test_doubt_sobre_glossario_continua_registrada(tmp_path):
    """Perde o veto, mas não some do manifesto — a fase fica `partial`."""
    _make_ws(tmp_path, {
        "HUs/HU-001.md": "x",
        "Doubt_Artifact_D-VAL-001_20260804_223439_620865.md": _doubt_md("Glossario"),
    })
    doubts = _scan_doubts(tmp_path, tmp_path)

    assert len(doubts) == 1
    assert _derive_status(_scan_artifacts(tmp_path, tmp_path), doubts) == "partial"


def test_doubt_sobre_requisito_continua_bloqueando(tmp_path):
    """O rebaixamento vale só para o glossário; o resto segue igual."""
    _make_ws(tmp_path, {
        "Doubt_Artifact_D-VAL-002_20260804_223516_895970.md": _doubt_md("RF-004"),
    })
    doubts = _scan_doubts(tmp_path, tmp_path)

    assert doubts[0]["bloqueante"] is True


def test_doubt_sem_artefato_afetado_nao_e_rebaixada(tmp_path):
    """Sem o campo, não há como afirmar que a dúvida é sobre o glossário."""
    content = "# Doubt_Artifact\n- **Bloqueante:** Sim\n- **Status:** Aberta\n"
    _make_ws(tmp_path, {"Doubt_Artifact_D-001_20260723_120000_000000.md": content})

    assert _scan_doubts(tmp_path, tmp_path)[0]["bloqueante"] is True


def test_glossario_citado_apenas_no_texto_nao_rebaixa(tmp_path):
    """O gatilho é o artefato afetado, não a palavra aparecer na descrição."""
    content = _doubt_md("RF-004").replace(
        "O glossário não foi encontrado no repositório.",
        "O termo 'selecionadas' não está no glossário e o RF-004 é ambíguo.",
    )
    _make_ws(tmp_path, {"Doubt_Artifact_D-VAL-002_20260804_223516_895970.md": content})

    assert _scan_doubts(tmp_path, tmp_path)[0]["bloqueante"] is True



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


def test_status_partial_sem_artefatos_e_sem_doubt():
    """`blocked` exige dúvida bloqueante no contrato PhaseManifest."""
    assert _derive_status([], []) == "partial"


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
    ctx.state = {"requirements_audit": {"schema_status": "ok", "coerente": True}}

    with patch("src.agents.requirements.manifest.get_agent_workspace", return_value=tmp_path), \
         patch("src.agents.requirements.manifest.get_workspace_root", return_value=tmp_path):
        emit_requirements_manifest(callback_context=ctx)

    manifests = ctx.state["phase_manifests"]
    assert len(manifests) == 1
    assert manifests[0]["phase"] == "requirements"
    assert manifests[0]["status"] == "ok"
    assert (tmp_path / "manifest.json").exists()


def test_emit_preserva_manifestos_de_outras_fases(tmp_path):
    """O handoff é acumulativo: manifestos anteriores não podem ser perdidos."""
    _make_ws(tmp_path, {"HUs/HU-001.md": "# HU-001"})
    anterior = {"phase": "intake", "status": "ok", "artifacts": [], "doubts": []}
    ctx = MagicMock()
    ctx.state = {
        "phase_manifests": [anterior],
        "requirements_audit": {"schema_status": "ok", "coerente": True},
    }

    with patch("src.agents.requirements.manifest.get_agent_workspace", return_value=tmp_path), \
         patch("src.agents.requirements.manifest.get_workspace_root", return_value=tmp_path):
        emit_requirements_manifest(callback_context=ctx)

    fases = [m["phase"] for m in ctx.state["phase_manifests"]]
    assert fases == ["intake", "requirements"]


def test_emit_reemissao_substitui_em_vez_de_duplicar(tmp_path):
    """Retomada após HITL não pode acumular duas entradas de `requirements`."""
    _make_ws(tmp_path, {"HUs/HU-001.md": "# HU-001"})
    ctx = MagicMock()
    ctx.state = {"requirements_audit": {"schema_status": "ok", "coerente": True}}

    with patch("src.agents.requirements.manifest.get_agent_workspace", return_value=tmp_path), \
         patch("src.agents.requirements.manifest.get_workspace_root", return_value=tmp_path):
        emit_requirements_manifest(callback_context=ctx)
        emit_requirements_manifest(callback_context=ctx)

    assert [m["phase"] for m in ctx.state["phase_manifests"]] == ["requirements"]


def test_emit_publica_manifesto_valido_para_o_orquestrador(tmp_path):
    """O que é publicado precisa sobreviver à leitura do orquestrador.

    `orchestrator._helpers._load_phase_manifests` é exatamente
    `PhaseManifest.model_validate` sobre cada item de `phase_manifests`.
    Validamos contra o modelo diretamente porque importar o pacote
    `orchestrator` arrasta `qa_agent.callbacks`, que hoje não compila.
    """
    from shared.manifest import PhaseManifest

    def _load_phase_manifests(state):
        return [PhaseManifest.model_validate(i) for i in state.get("phase_manifests", [])]

    _make_ws(tmp_path, {
        "HUs/HU-001.md": "# HU-001",
        "Doubt_Artifact_D1.md": "**Bloqueante:** Sim",
    })
    ctx = MagicMock()
    ctx.state = {"requirements_audit": {"schema_status": "ok", "coerente": True}}

    with patch("src.agents.requirements.manifest.get_agent_workspace", return_value=tmp_path), \
         patch("src.agents.requirements.manifest.get_workspace_root", return_value=tmp_path):
        emit_requirements_manifest(callback_context=ctx)

    carregados = _load_phase_manifests(ctx.state)
    assert len(carregados) == 1
    assert carregados[0].phase == "requirements"
    assert [a.id for a in carregados[0].artifacts] == ["HU-001"]


def test_emit_regride_para_partial_quando_auditoria_incoerente(tmp_path):
    """Saída incoerente com o disco não pode ser reportada como fase ok."""
    _make_ws(tmp_path, {"HUs/HU-001.md": "# HU-001"})
    ctx = MagicMock()
    ctx.state = {
        "requirements_audit": {
            "schema_status": "ok",
            "coerente": False,
            "declarados_sem_arquivo": ["RF-009"],
        }
    }

    with patch("src.agents.requirements.manifest.get_agent_workspace", return_value=tmp_path), \
         patch("src.agents.requirements.manifest.get_workspace_root", return_value=tmp_path):
        emit_requirements_manifest(callback_context=ctx)

    assert ctx.state["phase_manifests"][0]["status"] == "partial"


def test_emit_manifest_json_valido(tmp_path):
    import json
    _make_ws(tmp_path, {
        "HUs/HU-001.md": "x",
        "RFs/RF-001.md": "x",
    })
    ctx = MagicMock()
    ctx.state = {"requirements_audit": {"schema_status": "ok", "coerente": True}}

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
