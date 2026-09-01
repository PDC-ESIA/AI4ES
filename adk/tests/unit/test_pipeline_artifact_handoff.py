"""Regressões do handoff de fontes persistidos para o QA."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace


def test_qa_manifest_publica_delta_por_mutacao_de_state(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace"))
    from shared.workspace import get_agent_workspace
    from src.agents.workflow_qa.agent import _emit_qa_manifest

    tests_dir = get_agent_workspace("receive_requirements") / "rf_001"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_rf_001.py").write_text(
        "def test_ok():\n    assert True\n",
        encoding="utf-8",
    )
    (tests_dir / "report.json").write_text(
        json.dumps(
            {
                "exitcode": 0,
                "summary": {"passed": 1, "failed": 0, "skipped": 0},
            }
        ),
        encoding="utf-8",
    )
    context = SimpleNamespace(
        state={
            "phase_manifests": [
                {
                    "phase": "coding",
                    "status": "ok",
                    "artifacts": [],
                    "doubts": [],
                    "summary": "ok",
                }
            ]
        }
    )

    result = _emit_qa_manifest(context)

    assert result is None
    assert context.state["qa_manifest"]["status"] == "ok"
    assert [item["phase"] for item in context.state["phase_manifests"]] == [
        "coding",
        "qa",
    ]
    assert context.state["qa_manifest"]["artifacts"] == [
        {
            "tipo": "teste",
            "id": "rf_001",
            "path": "tests/inputs/rf_001/test_rf_001.py",
        }
    ]


def test_qa_manifest_bloqueia_zero_testes_e_doubt(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    from shared.workspace import get_agent_workspace
    from src.agents.workflow_qa.agent import _emit_qa_manifest

    tests_dir = get_agent_workspace("receive_requirements") / "rf_test_001"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_rf_test_001.py").write_text(
        "from src.checkout import calculate_checkout\n",
        encoding="utf-8",
    )
    (tests_dir / "report.json").write_text(
        json.dumps({"exitcode": 2, "summary": {"total": 0, "collected": 0}}),
        encoding="utf-8",
    )
    doubt = get_agent_workspace("receive_requirements") / "doubt_artifacts"
    doubt.mkdir(parents=True)
    (doubt / "Doubt_Artifact_import_fail.md").write_text(
        "# Bloqueio de import",
        encoding="utf-8",
    )
    context = SimpleNamespace(state={"phase_manifests": []})

    _emit_qa_manifest(context)

    manifest = context.state["qa_manifest"]
    assert manifest["status"] == "blocked"
    assert manifest["doubts"][0]["bloqueante"] is True
    assert "0 passed" in manifest["summary"]


def test_qa_materializa_source_path_do_manifest(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    source = workspace / "coder" / "src" / "src" / "order_calculator.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 42\n", encoding="utf-8")
    destination = workspace / "tests" / "inputs" / "rf_001"
    destination.mkdir(parents=True)

    from src.agents.qa_agent.subagents.receive_requirements.io import (
        _salvar_arquivos_apoio,
    )

    saved = _salvar_arquivos_apoio(
        {
            "arquivos_apoio": [
                {
                    "nome": "order_calculator.py",
                    "path": "coder/src/src/order_calculator.py",
                }
            ]
        },
        destination,
    )

    assert saved == [destination / "src" / "order_calculator.py"]
    assert saved[0].read_text(encoding="utf-8") == "VALUE = 42\n"


def test_qa_descobre_fontes_persistidos_sem_manifest(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    coder_src = workspace / "coder" / "src" / "src"
    coder_src.mkdir(parents=True)
    (coder_src / "__init__.py").write_text("", encoding="utf-8")
    (coder_src / "checkout.py").write_text("VALUE = 42\n", encoding="utf-8")
    (workspace / "coder" / "src" / "conftest.py").write_text(
        "CODER_TEST_CONFIG = True\n",
        encoding="utf-8",
    )
    destination = workspace / "tests" / "inputs" / "rf_001"
    destination.mkdir(parents=True)

    from src.agents.qa_agent.subagents.receive_requirements.io import (
        _salvar_arquivos_apoio,
    )

    saved = _salvar_arquivos_apoio(
        {"arquivos_apoio": []},
        destination,
    )

    assert saved == [
        destination / "src" / "__init__.py",
        destination / "src" / "checkout.py",
    ]
    assert saved[1].read_text(encoding="utf-8") == "VALUE = 42\n"


def test_qa_preserva_pacote_src_com_multiplos_fontes(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    coder_src = workspace / "coder" / "src" / "src"
    coder_src.mkdir(parents=True)
    (coder_src / "__init__.py").write_text("", encoding="utf-8")
    (coder_src / "price_rules.py").write_text("RATE = 5\n", encoding="utf-8")
    (coder_src / "checkout.py").write_text(
        "from .price_rules import RATE\n",
        encoding="utf-8",
    )
    destination = workspace / "tests" / "inputs" / "rf_test_001"
    destination.mkdir(parents=True)

    from src.agents.qa_agent.subagents.receive_requirements.io import (
        _salvar_arquivos_apoio,
    )

    saved = _salvar_arquivos_apoio(
        {
            "arquivos_apoio": [
                {
                    "nome": "src/checkout.py",
                    "path": "coder/src/src/checkout.py",
                },
                {
                    "nome": "src/price_rules.py",
                    "path": "coder/src/src/price_rules.py",
                },
                {
                    "nome": "src/__init__.py",
                    "path": "coder/src/src/__init__.py",
                },
            ]
        },
        destination,
    )

    assert saved == [
        destination / "src" / "checkout.py",
        destination / "src" / "price_rules.py",
        destination / "src" / "__init__.py",
    ]
    assert (destination / "src" / "checkout.py").read_text(
        encoding="utf-8"
    ) == "from .price_rules import RATE\n"


def test_code_fix_consegue_alterar_teste_fisicamente(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    test_file = (
        workspace / "tests" / "inputs" / "rf_test_001" / "test_rf_test_001.py"
    )
    test_file.parent.mkdir(parents=True)
    test_file.write_text("from src.inexistente import x\n", encoding="utf-8")

    from shared.tools.qa_test_files import read_qa_test, write_qa_test

    before = read_qa_test("tests/inputs/rf_test_001/test_rf_test_001.py")
    result = write_qa_test(
        "tests/inputs/rf_test_001/test_rf_test_001.py",
        "def test_corrigido():\n    assert True\n",
    )

    assert before["status"] == "ok"
    assert result["status"] == "aplicado"
    assert test_file.read_text(encoding="utf-8") == (
        "def test_corrigido():\n    assert True\n"
    )


def test_code_fix_rejeita_manipulacao_de_sys_path(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    test_file = (
        workspace / "tests" / "inputs" / "rf_test_001" / "test_rf_test_001.py"
    )
    test_file.parent.mkdir(parents=True)
    original = "def test_original():\n    assert True\n"
    test_file.write_text(original, encoding="utf-8")

    from shared.tools.qa_test_files import write_qa_test

    result = write_qa_test(
        "tests/inputs/rf_test_001/test_rf_test_001.py",
        "import sys\n"
        "sys.path.insert(0, '../../../coder')\n\n"
        "def test_invalido():\n"
        "    assert True\n",
    )

    assert result["status"] == "erro"
    assert "não pode alterar sys.path" in result["erro"]
    assert test_file.read_text(encoding="utf-8") == original


def test_code_fix_nao_cria_teste_ausente(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    from shared.tools.qa_test_files import write_qa_test

    result = write_qa_test(
        "artefactsTests/shipping/test_inventado.py",
        "def test_inventado():\n    assert True\n",
    )

    assert result["status"] == "erro"
    assert "só pode corrigir um teste existente" in result["erro"]
    assert not (
        workspace
        / "tests"
        / "inputs"
        / "artefactsTests"
        / "shipping"
        / "test_inventado.py"
    ).exists()


def test_receive_ignora_path_sugerido_e_retorna_canonico(
    monkeypatch,
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    source = workspace / "coder" / "src" / "src" / "shipping_rules.py"
    source.parent.mkdir(parents=True)
    source.write_text("def calculate():\n    return 5\n", encoding="utf-8")

    from src.agents.qa_agent.subagents.receive_requirements import orchestration

    monkeypatch.setattr(
        orchestration,
        "_gerar_pytest_via_llm",
        lambda **_kwargs: "def test_ok():\n    assert True\n",
    )

    result = asyncio.run(
        orchestration._processar_artefato(
            {
                "id_artefato": "RF-001",
                "tipo": "RF",
                "conteudo": "Validar cálculo.",
                "modulo": "shipping",
                "caminho_desejado": (
                    "artefactsTests/shipping/test_shipping_integration.py"
                ),
            }
        )
    )

    expected = (
        workspace / "tests" / "inputs" / "rf_001" / "test_rf_001.py"
    ).resolve()
    assert result["status"] == "sucesso"
    assert Path(result["arquivo_gerado"]) == expected
    assert not (
        workspace / "tests" / "inputs" / "artefactsTests"
    ).exists()


def test_workflow_qa_usa_fluxo_unitario_deterministico_em_vez_de_agent_tool():
    from google.adk.tools.agent_tool import AgentTool
    from src.agents.workflow_qa.agent import agent

    unit_tool = next(
        tool for tool in agent.tools
        if getattr(tool, "name", "") == "gerar_testes_unitarios"
    )

    assert not isinstance(unit_tool, AgentTool)
    assert "detalhes[].arquivo_gerado" in agent.instruction


def test_workflow_qa_nao_exige_manifesto_de_coding():
    from src.agents.workflow_qa.agent import agent

    assert "manifesto de Coding NÃO é obrigatório" in agent.instruction
    assert "workspace_output/coder/src" in agent.instruction
