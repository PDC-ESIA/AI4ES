"""Testes do emissor de manifesto — Fase de Codificação (Time 4).

Cobre:
- Constantes: PHASE_NAME, STATE_KEY
- _scan_artifacts: classificação por subpasta (codigo, teste, config, revisao),
  filtros (__pycache__, .pyc, manifest.json), path com barra forward
- _scan_doubts: detecção de Doubt_Artifact_*.md e marcador de bloqueante
- _validation_verdict: pass / fail / absent a partir de arquivos do reviewer
- _derive_status: todas as combinações de artifacts, doubts e validation
- _build_summary: contagem por tipo, menção a doubts e revisão
- emit_coding_manifest: escrita em state + disco, degradação silenciosa
- Wiring: after_agent_callback no SequentialAgent raiz
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.agents.workflow_coding_review.manifest import (
    PHASE_NAME,
    STATE_KEY,
    _build_summary,
    _derive_status,
    _scan_artifacts,
    _scan_doubts,
    _validation_verdict,
    emit_coding_manifest,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ws(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------


def test_phase_name_canonico():
    assert PHASE_NAME == "coding"


def test_state_key_correto():
    assert STATE_KEY == "coding_manifest"


# ---------------------------------------------------------------------------
# _scan_artifacts
# ---------------------------------------------------------------------------


def test_scan_artifacts_workspace_vazio(tmp_path):
    assert _scan_artifacts(tmp_path, tmp_path) == []


def test_scan_artifacts_detecta_codigo(tmp_path):
    _make_ws(tmp_path, {
        "src/app/main.py": "# main",
        "src/app/models.py": "# models",
    })
    arts = _scan_artifacts(tmp_path, tmp_path)
    assert all(a["tipo"] == "codigo" for a in arts)
    ids = {a["id"] for a in arts}
    assert {"main", "models"} == ids


def test_scan_artifacts_detecta_teste(tmp_path):
    _make_ws(tmp_path, {"src/tests/test_main.py": "# test"})
    arts = _scan_artifacts(tmp_path, tmp_path)
    assert len(arts) == 1
    assert arts[0]["tipo"] == "teste"
    assert arts[0]["id"] == "test_main"


def test_scan_artifacts_detecta_config(tmp_path):
    _make_ws(tmp_path, {
        "src/Dockerfile": "FROM python:3.12-slim",
        "src/requirements.txt": "fastapi\nuvicorn[standard]",
    })
    arts = _scan_artifacts(tmp_path, tmp_path)
    tipos = {a["tipo"] for a in arts}
    ids = {a["id"] for a in arts}
    assert tipos == {"config"}
    assert "Dockerfile" in ids
    assert "requirements" in ids


def test_scan_artifacts_detecta_revisao(tmp_path):
    _make_ws(tmp_path, {"review/verificacao_revisao.md": "## Status: APROVADO"})
    arts = _scan_artifacts(tmp_path, tmp_path)
    assert len(arts) == 1
    assert arts[0]["tipo"] == "revisao"
    assert arts[0]["id"] == "verificacao_revisao"


def test_scan_artifacts_path_usa_barra_forward(tmp_path):
    _make_ws(tmp_path, {"src/app/main.py": "# main"})
    arts = _scan_artifacts(tmp_path, tmp_path)
    assert len(arts) == 1
    assert "\\" not in arts[0]["path"]
    assert "src/app/main.py" == arts[0]["path"]


def test_scan_artifacts_ignora_pycache(tmp_path):
    _make_ws(tmp_path, {"src/app/main.py": "# main"})
    cache = tmp_path / "src" / "app" / "__pycache__"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "main.cpython-312.pyc").write_bytes(b"\x00")
    arts = _scan_artifacts(tmp_path, tmp_path)
    assert all("__pycache__" not in a["path"] for a in arts)
    assert all(".pyc" not in a["path"] for a in arts)


def test_scan_artifacts_ignora_manifest_json_em_review(tmp_path):
    _make_ws(tmp_path, {
        "review/manifest.json": "{}",
        "review/revisao.md": "## Status: APROVADO",
    })
    arts = _scan_artifacts(tmp_path, tmp_path)
    ids = {a["id"] for a in arts}
    assert "manifest" not in ids
    assert "revisao" in ids


# ---------------------------------------------------------------------------
# _scan_doubts
# ---------------------------------------------------------------------------


def test_scan_doubts_sem_arquivos_retorna_vazio(tmp_path):
    assert _scan_doubts(tmp_path, tmp_path) == []


def test_scan_doubts_detecta_bloqueante(tmp_path):
    _make_ws(tmp_path, {
        "tasks/Doubt_Artifact_D-001_20260723.md": (
            "# Dúvida\n**Bloqueante:** Sim\nDescrição da dúvida."
        ),
    })
    doubts = _scan_doubts(tmp_path, tmp_path)
    assert len(doubts) == 1
    assert doubts[0]["bloqueante"] is True
    assert doubts[0]["severidade"] == "alta"
    assert doubts[0]["id"] == "Doubt_Artifact_D-001_20260723"


def test_scan_doubts_detecta_formato_tool_gerar_doubt_artifact(tmp_path):
    """Doubt gerado por tool_gerar_doubt_artifact_adk na raiz do workspace.

    A tool escreve 'EXECUÇÃO PAUSADA' (sem '**Bloqueante:** Sim').
    O scanner deve reconhecer esse formato como bloqueante.
    """
    conteudo = (
        "# Doubt Artifact — Artefatos mínimos ausentes\n"
        "\n"
        "> EXECUÇÃO PAUSADA — INTERVENÇÃO NECESSÁRIA\n"
        "> Gerado pelo context_engineer em 2026-08-04 10:00:00\n"
        "\n"
        "## Fase Bloqueada\n"
        "**requirements**\n"
        "\n"
        "## Descrição do Problema\n"
        "Pasta requirements/ não encontrada.\n"
        "\n"
        "## Ação Necessária\n"
        "Executar o pipeline de requisitos antes do coding.\n"
    )
    _make_ws(tmp_path, {"Doubt_Artifact_context_engineer.md": conteudo})
    doubts = _scan_doubts(tmp_path, tmp_path)
    assert len(doubts) == 1
    assert doubts[0]["bloqueante"] is True
    assert doubts[0]["severidade"] == "alta"
    assert doubts[0]["id"] == "Doubt_Artifact_context_engineer"


def test_scan_doubts_detecta_nao_bloqueante(tmp_path):
    _make_ws(tmp_path, {
        "tasks/Doubt_Artifact_D-002_20260723.md": (
            "# Dúvida\n**Bloqueante:** Não\nDescrição da dúvida."
        ),
    })
    doubts = _scan_doubts(tmp_path, tmp_path)
    assert len(doubts) == 1
    assert doubts[0]["bloqueante"] is False
    assert doubts[0]["severidade"] == "media"


# ---------------------------------------------------------------------------
# _validation_verdict
# ---------------------------------------------------------------------------


def test_validation_verdict_absent_sem_review_dir(tmp_path):
    assert _validation_verdict(tmp_path) == "absent"


def test_validation_verdict_absent_review_dir_vazio(tmp_path):
    (tmp_path / "review").mkdir()
    assert _validation_verdict(tmp_path) == "absent"


def test_validation_verdict_pass(tmp_path):
    _make_ws(tmp_path, {"review/revisao.md": "## Status: APROVADO\nTudo certo."})
    assert _validation_verdict(tmp_path) == "pass"


def test_validation_verdict_fail(tmp_path):
    _make_ws(tmp_path, {"review/revisao.md": "## Status: BLOQUEADO\nErros encontrados."})
    assert _validation_verdict(tmp_path) == "fail"


def test_validation_verdict_fail_tem_prioridade(tmp_path):
    _make_ws(tmp_path, {
        "review/r1.md": "## Status: APROVADO",
        "review/r2.md": "## Status: BLOQUEADO",
    })
    assert _validation_verdict(tmp_path) == "fail"


# ---------------------------------------------------------------------------
# _derive_status
# ---------------------------------------------------------------------------


def _art(tipo: str) -> dict:
    return {"tipo": tipo, "id": "x", "path": "p"}


def _blocking() -> dict:
    return {"id": "D-001", "severidade": "alta", "bloqueante": True, "path": "p"}


def _nonblocking() -> dict:
    return {"id": "D-002", "severidade": "media", "bloqueante": False, "path": "p"}


def test_status_ok():
    assert _derive_status([_art("codigo")], [], "pass") == "ok"


def test_status_blocked_sem_codigo():
    assert _derive_status([], [], "pass") == "blocked"


def test_status_blocked_doubt_bloqueante():
    assert _derive_status([_art("codigo")], [_blocking()], "pass") == "blocked"


def test_status_partial_doubt_nao_bloqueante():
    assert _derive_status([_art("codigo")], [_nonblocking()], "pass") == "partial"


def test_status_partial_validation_fail():
    assert _derive_status([_art("codigo")], [], "fail") == "partial"


def test_status_partial_validation_absent():
    assert _derive_status([_art("codigo")], [], "absent") == "partial"


# ---------------------------------------------------------------------------
# _build_summary
# ---------------------------------------------------------------------------


def test_summary_conta_tipos():
    arts = [_art("codigo"), _art("codigo"), _art("config")]
    s = _build_summary(arts, [], "pass")
    assert "2 codigo(s)" in s
    assert "1 config(s)" in s


def test_summary_menciona_doubts():
    arts = [_art("codigo")]
    doubts = [_nonblocking()]
    s = _build_summary(arts, doubts, "pass")
    assert "dúvida" in s


def test_summary_menciona_revisao():
    s = _build_summary([_art("codigo")], [], "pass")
    assert "pass" in s


# ---------------------------------------------------------------------------
# emit_coding_manifest
# ---------------------------------------------------------------------------


def test_emit_grava_state_e_arquivo(tmp_path):
    coder_ws = tmp_path / "coder"
    _make_ws(coder_ws, {
        "src/app/main.py": "# main",
        "review/revisao.md": "## Status: APROVADO",
    })

    ctx = MagicMock()
    ctx.state = {}
    ctx.session = MagicMock(id=None)
    ctx.session_id = None

    with patch("src.agents.workflow_coding_review.manifest.get_agent_workspace", return_value=coder_ws), \
         patch("src.agents.workflow_coding_review.manifest.get_workspace_root", return_value=tmp_path):
        emit_coding_manifest(callback_context=ctx)

    assert STATE_KEY in ctx.state
    assert ctx.state[STATE_KEY]["phase"] == PHASE_NAME
    assert ctx.state[STATE_KEY]["status"] == "ok"
    assert (tmp_path / "coding" / "manifest.json").exists()


def test_emit_manifest_json_valido(tmp_path):
    coder_ws = tmp_path / "coder"
    _make_ws(coder_ws, {"src/app/main.py": "# main"})

    ctx = MagicMock()
    ctx.state = {}
    ctx.session = MagicMock(id=None)
    ctx.session_id = None

    with patch("src.agents.workflow_coding_review.manifest.get_agent_workspace", return_value=coder_ws), \
         patch("src.agents.workflow_coding_review.manifest.get_workspace_root", return_value=tmp_path):
        emit_coding_manifest(callback_context=ctx)

    data = json.loads((tmp_path / "coding" / "manifest.json").read_text(encoding="utf-8"))
    assert data["phase"] == PHASE_NAME
    assert data["status"] == "partial"   # código sem review → partial
    assert "artifacts" in data
    assert "doubts" in data
    assert "summary" in data
    assert "session_id" in data


def test_emit_nao_quebra_pipeline_em_falha():
    ctx = MagicMock()
    ctx.state = {}

    with patch(
        "src.agents.workflow_coding_review.manifest.get_agent_workspace",
        side_effect=RuntimeError("disco cheio"),
    ):
        emit_coding_manifest(callback_context=ctx)  # não deve levantar

    assert STATE_KEY not in ctx.state


# ---------------------------------------------------------------------------
# Wiring — after_agent_callback no SequentialAgent
# ---------------------------------------------------------------------------


def test_sequentialagent_tem_after_agent_callback():
    from src.agents.workflow_coding_review.agent import agent

    assert hasattr(agent, "after_agent_callback")
    assert agent.after_agent_callback is not None


def test_after_agent_callback_e_emit_coding_manifest():
    from src.agents.workflow_coding_review.agent import agent
    from src.agents.workflow_coding_review.manifest import emit_coding_manifest

    assert agent.after_agent_callback is emit_coding_manifest
