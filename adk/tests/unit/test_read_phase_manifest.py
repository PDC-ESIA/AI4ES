"""Testes de `read_phase_manifest` / `read_phase_artifact` (design_filesystem.py).

Cobre a leitura, pelo lado Design, do Manifesto de Fase publicado por OUTRA
fase (hoje, na prática, "requirements" — ver
`src/agents/requirements/manifest.py::emit_requirements_manifest`).

Fixtures usam o formato REAL confirmado por inspeção do emissor de
Requisitos (ver `extracao_manifesto_requisitos.md`):
- `path` relativo à raiz do workspace (`get_workspace_root()`, que já É
  `workspace_output/`), SEM o prefixo "workspace_output/" — ex.:
  "requirements/HUs/HU-001.md".
- `status`/`tipo` em vocabulário canônico já compartilhado
  ("ok"/"blocked"/"partial", "HU"/"RF"/"RNF"/"RN"/"Outro"/"Glossario").

Não usa o runtime ADK: chama as funções puras diretamente, com
`WORKSPACE_OUTPUT_DIR` apontando para `tmp_path` (mesmo padrão de
`test_design_manifest.py`).
"""

import json
from pathlib import Path

import pytest

from shared.tools.design_filesystem import read_phase_manifest, read_phase_artifact


def _write(path: Path, content: str = "conteudo") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _requirements_manifest_dict(*, status: str = "ok", with_doubt: bool = False) -> dict:
    """Formato real emitido por `requirements/manifest.py::emit_requirements_manifest`."""
    artifacts = [
        {"tipo": "HU", "id": "HU-001", "path": "requirements/HUs/HU-001.md"},
        {"tipo": "HU", "id": "HU-002", "path": "requirements/HUs/HU-002.md"},
        {"tipo": "RF", "id": "RF-001", "path": "requirements/RFs/RF-001.md"},
        {"tipo": "Glossario", "id": "Glossario", "path": "requirements/glossario/Glossario.md"},
    ]
    doubts = []
    if with_doubt:
        doubts.append({
            "id": "Doubt_Artifact_HU-002_20260101",
            "severidade": "media",
            "bloqueante": False,
            "path": "requirements/Doubt_Artifact_HU-002_20260101.md",
        })
    return {
        "phase": "requirements",
        "status": status,
        "artifacts": artifacts,
        "doubts": doubts,
        "summary": "Fase de requisitos concluída.",
    }


def _write_requirements_workspace(tmp_path: Path, manifest: dict) -> Path:
    """Monta workspace_output/requirements/** com o manifesto e os artefatos que ele referencia."""
    ws_root = tmp_path / "workspace_output"
    req_root = ws_root / "requirements"
    _write(req_root / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    for artifact in manifest["artifacts"]:
        _write(ws_root / artifact["path"], f"Conteúdo de {artifact['id']}")
    for doubt in manifest.get("doubts", []):
        _write(ws_root / doubt["path"], "**Bloqueante:** Não")
    return ws_root


# ──────────────────────────────────────────────────────────────────────────────
# read_phase_manifest
# ──────────────────────────────────────────────────────────────────────────────

def test_read_phase_manifest_absent_e_estado_neutro(tmp_path, monkeypatch):
    """Regressão: sem manifest.json, retorna 'absent' — nunca erro."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace_output"))

    result = read_phase_manifest("requirements", caller="pipeline_controller")

    assert result["status"] == "absent"
    assert result["phase"] == "requirements"
    assert "hint" in result


def test_read_phase_manifest_ok_com_manifesto_real(tmp_path, monkeypatch):
    """Com um manifest.json no formato real de Requisitos, status vem 'ok' e o
    JSON é repassado integralmente (sem filtro) quando `tipo` não é informado."""
    manifest = _requirements_manifest_dict(status="ok")
    ws_root = _write_requirements_workspace(tmp_path, manifest)
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws_root))

    result = read_phase_manifest("requirements", caller="pipeline_controller")

    assert result["status"] == "ok"
    assert result["phase"] == "requirements"
    assert result["manifest"]["status"] == "ok"
    assert len(result["manifest"]["artifacts"]) == 4  # sem filtro: HU+HU+RF+Glossario


def test_read_phase_manifest_error_sem_chave_artifacts(tmp_path, monkeypatch):
    """manifest.json malformado (sem 'artifacts') é 'error', distinto de 'absent'."""
    ws_root = tmp_path / "workspace_output"
    _write(ws_root / "requirements" / "manifest.json", json.dumps({"phase": "requirements"}))
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws_root))

    result = read_phase_manifest("requirements", caller="pipeline_controller")

    assert result["status"] == "error"


def test_read_phase_manifest_filtra_por_tipo_hu(tmp_path, monkeypatch):
    """Filtro determinístico: só os artifacts com tipo == 'HU' voltam, e nada
    mais — RF/Glossario nunca vazam para quem só pediu HU."""
    manifest = _requirements_manifest_dict(status="ok")
    ws_root = _write_requirements_workspace(tmp_path, manifest)
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws_root))

    result = read_phase_manifest("requirements", tipo="HU", caller="pipeline_controller")

    assert result["status"] == "ok"
    artifacts = result["manifest"]["artifacts"]
    assert len(artifacts) == 2
    assert all(a["tipo"] == "HU" for a in artifacts)
    assert {a["id"] for a in artifacts} == {"HU-001", "HU-002"}


def test_read_phase_manifest_filtro_por_tipo_preserva_doubts_e_status(tmp_path, monkeypatch):
    """O filtro por tipo só afeta 'artifacts' — doubts/status/summary continuam
    integrais, mesmo que as doubts se refiram a um artefato de outro tipo."""
    manifest = _requirements_manifest_dict(status="partial", with_doubt=True)
    ws_root = _write_requirements_workspace(tmp_path, manifest)
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws_root))

    result = read_phase_manifest("requirements", tipo="HU", caller="pipeline_controller")

    assert result["manifest"]["status"] == "partial"
    assert len(result["manifest"]["doubts"]) == 1
    assert result["manifest"]["doubts"][0]["bloqueante"] is False


def test_read_phase_manifest_filtro_sem_correspondencia_retorna_vazio(tmp_path, monkeypatch):
    """Se nenhum artifact bater com o tipo pedido, volta 'ok' com artifacts=[]
    (o chamador trata isso como equivalente a 'absent' — ver ETAPA 1-B)."""
    manifest = _requirements_manifest_dict(status="ok")
    manifest["artifacts"] = [a for a in manifest["artifacts"] if a["tipo"] != "HU"]
    ws_root = _write_requirements_workspace(tmp_path, manifest)
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws_root))

    result = read_phase_manifest("requirements", tipo="HU", caller="pipeline_controller")

    assert result["status"] == "ok"
    assert result["manifest"]["artifacts"] == []


# ──────────────────────────────────────────────────────────────────────────────
# read_phase_artifact
# ──────────────────────────────────────────────────────────────────────────────

def test_read_phase_artifact_convencao_real_sem_prefixo(tmp_path, monkeypatch):
    """Bug corrigido: path real ("requirements/HUs/HU-001.md", relativo direto
    a get_workspace_root(), sem "workspace_output/") deve ser lido com sucesso —
    a versão anterior resolvia via `get_workspace_root().parent`, o que
    rejeitava exatamente este caso ("fora de workspace_output/")."""
    manifest = _requirements_manifest_dict(status="ok")
    ws_root = _write_requirements_workspace(tmp_path, manifest)
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws_root))

    result = read_phase_artifact("requirements/HUs/HU-001.md", caller="pipeline_controller")

    assert result["status"] == "ok"
    assert result["content"] == "Conteúdo de HU-001"


def test_read_phase_artifact_aceita_prefixo_workspace_output_defensivamente(tmp_path, monkeypatch):
    """Normalização defensiva: se um path vier com o prefixo que o manifesto de
    Design usa para si mesmo (convenção diferente), ainda assim resolve."""
    manifest = _requirements_manifest_dict(status="ok")
    ws_root = _write_requirements_workspace(tmp_path, manifest)
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws_root))

    prefixed = f"{ws_root.name}/requirements/HUs/HU-001.md"  # "workspace_output/requirements/..."
    result = read_phase_artifact(prefixed, caller="pipeline_controller")

    assert result["status"] == "ok"
    assert result["content"] == "Conteúdo de HU-001"


def test_read_phase_artifact_rejeita_caminho_fora_do_workspace(tmp_path, monkeypatch):
    """Path tentando escapar de workspace_output/ (ex.: '../../etc/passwd') é recusado."""
    ws_root = tmp_path / "workspace_output"
    ws_root.mkdir(parents=True)
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws_root))

    result = read_phase_artifact("../fora_do_workspace.md", caller="pipeline_controller")

    assert result["status"] == "error"
    assert "Acesso negado" in result["error"]


def test_read_phase_artifact_arquivo_ausente_em_disco(tmp_path, monkeypatch):
    """Artefato listado no manifesto mas ausente em disco é erro pontual daquele
    artefato — não deve derrubar o processo nem ser confundido com acesso negado."""
    ws_root = tmp_path / "workspace_output"
    ws_root.mkdir(parents=True)
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws_root))

    result = read_phase_artifact("requirements/HUs/HU-999.md", caller="pipeline_controller")

    assert result["status"] == "error"
    assert "não encontrado" in result["error"]


# ──────────────────────────────────────────────────────────────────────────────
# Integração: fluxo completo "manifesto presente" (ETAPA 1-B do pipeline_controller)
# ──────────────────────────────────────────────────────────────────────────────

def test_fluxo_manifesto_ok_le_apenas_hus_end_to_end(tmp_path, monkeypatch):
    """Simula o que a ETAPA 1-B faz: lê o manifesto filtrado por tipo 'HU' e
    concatena o conteúdo de cada artefato listado, na ordem do manifesto."""
    manifest = _requirements_manifest_dict(status="ok")
    ws_root = _write_requirements_workspace(tmp_path, manifest)
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws_root))

    manifest_result = read_phase_manifest("requirements", tipo="HU", caller="pipeline_controller")
    assert manifest_result["status"] == "ok"

    conteudos = []
    for artifact in manifest_result["manifest"]["artifacts"]:
        artifact_result = read_phase_artifact(artifact["path"], caller="pipeline_controller")
        assert artifact_result["status"] == "ok"
        conteudos.append(artifact_result["content"])

    assert conteudos == ["Conteúdo de HU-001", "Conteúdo de HU-002"]


def test_fluxo_manifesto_blocked_nao_deve_ler_artefatos(tmp_path, monkeypatch):
    """Quando o manifesto vem 'blocked', a ETAPA 1-B não deve prosseguir para
    leitura de artefatos nem acionar o design_architect — só confirma o sinal."""
    manifest = _requirements_manifest_dict(status="ok")
    manifest["status"] = "blocked"
    manifest["doubts"] = [{
        "id": "Doubt_Artifact_HU-001_20260101",
        "severidade": "alta",
        "bloqueante": True,
        "path": "requirements/Doubt_Artifact_HU-001_20260101.md",
    }]
    ws_root = _write_requirements_workspace(tmp_path, manifest)
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws_root))

    result = read_phase_manifest("requirements", tipo="HU", caller="pipeline_controller")

    assert result["status"] == "ok"
    assert result["manifest"]["status"] == "blocked"
    assert result["manifest"]["doubts"][0]["bloqueante"] is True
