"""M3 — diagrama salvo/validado dentro de cercas Markdown não deve ser reprovado."""

import pytest

from shared.tools import design_filesystem as df
from shared.tools.design_validate.gatekeeper_tool import validate_artifact

CERCADO = "```mermaid\n%% Tipo de diagrama: flowchart\nflowchart TD\n A-->B\n```\n"


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    root = tmp_path / "design"
    monkeypatch.setattr(df, "ADK_DIR", tmp_path)
    monkeypatch.setattr(df, "DESIGN_DIR", root)
    monkeypatch.setattr(df, "LOCKS_DIR", root / ".locks")
    return root


def test_sanitize_mermaid_passa_no_gatekeeper():
    s = df._sanitize_mermaid(CERCADO)
    assert "```" not in s
    assert validate_artifact(s, "mmd")["valid"]


def test_gatekeeper_aceita_conteudo_cercado_em_mmd():
    assert validate_artifact(CERCADO, "mmd")["valid"]


def test_gatekeeper_continua_reprovando_tipo_invalido():
    assert not validate_artifact("```mermaid\nnaoexiste TD\n A-->B\n```", "mmd")["valid"]


def test_save_artifact_grava_mmd_sem_cercas(isolated):
    nome = "diagrama_HU-001_teste.mmd"
    assert df.acquire_lock(nome, caller="mermaid_specialist")["status"] == "ok"
    r = df.save_artifact(nome, CERCADO, caller="mermaid_specialist")
    assert r["status"] == "ok", r
    gravado = (isolated / "diagrams" / nome).read_text(encoding="utf-8")
    assert "```" not in gravado
    assert gravado.startswith("%% Tipo de diagrama: flowchart")


def test_validate_artifact_file_le_do_disco(isolated):
    from shared.tools.design_validate.gatekeeper_tool import validate_artifact_file
    nome = "diagrama_HU-002_teste.mmd"
    df.acquire_lock(nome, caller="mermaid_specialist")
    df.save_artifact(nome, CERCADO, caller="mermaid_specialist")
    assert validate_artifact_file(nome)["valid"]
    assert validate_artifact_file(f"DIAGRAMS/{nome}")["valid"]
    r = validate_artifact_file("diagrama_inexistente.mmd")
    assert r["valid"] is False and r["error_type"] == "READ_ERROR"


def test_validator_e_mermaid_leem_direto():
    from src.agents.validator.agent import agent as validator
    from src.agents.mermaid_specialist.agent import agent as mermaid
    nomes = lambda a: {getattr(t, "name", "") for t in a.tools}
    assert {"validate_artifact_file", "read_multiple_files",
            "read_analysis_sections", "list_design_files"} <= nomes(validator)
    assert "read_analysis_sections" in nomes(mermaid)


def test_gatekeeper_entradas_invalidas_nao_levantam_excecao():
    r = validate_artifact(None, "mmd")
    assert r["valid"] is False


@pytest.mark.parametrize("fmt", ["MMD", " mmd "])
def test_gatekeeper_normaliza_formato_antes_de_sanitizar(fmt):
    assert validate_artifact(CERCADO, fmt)["valid"]
