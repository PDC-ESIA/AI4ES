"""Integração interna do QA Agent — Cenário 3: persistência de dados intermediários.

Cobre o pipeline real receive_requirements → pytest_runner → emissão do
Manifesto de Fase (workflow_qa) sobre um workspace isolado, e a coexistência
das três implementações de Doubt Artifact no mesmo diretório compartilhado.
Único ponto stubado é `_gerar_pytest_via_llm` — todo o resto (escrita em
disco, execução real do pytest via subprocess, montagem do manifesto) roda
de verdade.
"""

import asyncio
import json
from pathlib import Path

import pytest


@pytest.fixture
def tmp_workspace(tmp_path: Path, monkeypatch) -> Path:
    """Workspace isolado por teste, substituindo workspace_output."""
    ws = tmp_path / "workspace_output"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / ".ai4se_workspace").write_text("marker", encoding="utf-8")
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws))

    from shared import workspace as _ws_mod

    monkeypatch.setattr(_ws_mod, "_DEFAULT_WORKSPACE", str(ws))
    return ws


def test_pipeline_persiste_e_gera_manifesto(
    tmp_workspace: Path, monkeypatch
):
    """Gera teste real, executa pytest real e confirma que o manifesto de QA
    reflete exatamente os artefatos persistidos no workspace."""
    from src.agents.qa_agent.subagents.receive_requirements import orchestration
    from shared.tools.pytest_runner import executar_pytest_tool
    from src.agents.workflow_qa.agent import _emit_qa_manifest
    from shared.manifest import PhaseManifest, PhaseStatus

    monkeypatch.setattr(
        orchestration,
        "_gerar_pytest_via_llm",
        lambda **kwargs: "def test_soma():\n    assert 1 + 1 == 2\n",
    )

    artefato = {
        "id_artefato": "RF-SOMA",
        "tipo": "RF",
        "conteudo": "O sistema deve somar dois numeros.",
        "modulo": "calculadora",
        "criticidade": "alta",
    }
    resultado_geracao = orchestration.receber_requisitos(json.dumps([artefato]))

    assert resultado_geracao["status"] == "concluido"
    assert resultado_geracao["resumo"]["sucessos"] == 1
    caminho_teste = resultado_geracao["detalhes"][0]["arquivo_gerado"]
    assert Path(caminho_teste).exists()

    resultado_execucao = executar_pytest_tool(caminho_teste)
    assert resultado_execucao["status"] == "sucesso"
    assert resultado_execucao["testes_passaram"] == 1

    # Relatórios de execução persistem no MESMO diretório do teste gerado.
    dir_teste = Path(caminho_teste).parent
    assert (dir_teste / "report.json").exists()
    assert (dir_teste / "coverage.json").exists()

    class _FakeCallbackContext:
        def __init__(self) -> None:
            self.state: dict = {}

    ctx = _FakeCallbackContext()
    actions = _emit_qa_manifest(ctx)
    manifests = actions.state_delta["phase_manifests"]
    manifest = PhaseManifest.model_validate(manifests[-1])

    assert manifest.phase == "qa"
    assert manifest.status == PhaseStatus.OK
    tipos = {a.tipo for a in manifest.artifacts}
    assert "teste" in tipos
    # receive_requirements não grava tests/inputs/<slug>.json hoje — o
    # manifesto reflete a realidade atual, não o formato do fake de testes
    # de orquestração (documenta o comportamento real, não o assumido).
    assert "input" not in tipos
    assert any(a.id == "rf_soma" for a in manifest.artifacts)
    caminho_relativo_esperado = str(Path(caminho_teste).relative_to(tmp_workspace))
    assert caminho_relativo_esperado in {a.path for a in manifest.artifacts}


def test_doubt_artifacts_coexistem(
    tmp_workspace: Path,
):
    """io._gerar_doubt_artifact, DoubtArtifactGenerator e o gerador síncrono do
    pytest_runner escrevem no mesmo diretório sem se sobrescreverem."""
    from shared.tools import doubt_tool as dt
    from shared.tools import pytest_runner as pr
    from src.agents.qa_agent.subagents.receive_requirements import io as rr_io

    caminho_io = asyncio.run(rr_io._gerar_doubt_artifact("ID-IO-001", "motivo io"))
    dt.DoubtArtifactGenerator.generate(
        id_artefato="ID-TOOL-001",
        motivo="motivo tool",
        trecho_suspeito="trecho suspeito",
        caminho_base=Path("doubt_artifacts"),
        trigger_type="test",
    )
    caminho_runner = pr._gerar_doubt_artifact_sincrono("ID-RUNNER-001", "motivo runner")

    doubt_dir = tmp_workspace / "tests" / "inputs" / "doubt_artifacts"
    arquivos = sorted(p.name for p in doubt_dir.glob("Doubt_Artifact_*.md"))

    assert len(arquivos) == 3
    assert any("ID-IO-001" in nome for nome in arquivos)
    assert any("ID-TOOL-001" in nome for nome in arquivos)
    assert any("ID-RUNNER-001" in nome for nome in arquivos)
    assert Path(caminho_io).exists()
    assert Path(caminho_runner).exists()
