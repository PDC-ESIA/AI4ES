"""Tests para gerar_doubt_artifact — base_dir opcional + fallback legado."""

from pathlib import Path

import pytest

from shared.tools.doubt_generator_analista import gerar_doubt_artifact


def _kwargs(**overrides):
    """Args mínimos para gerar_doubt_artifact."""
    base = dict(
        id_duvida="D-001",
        id_artefato_afetado="HU-001",
        trecho_contexto="trecho qualquer",
        duvida_descricao="dúvida X",
        motivo="motivo X",
        impacto="impacto X",
    )
    base.update(overrides)
    return base


def test_gerar_doubt_sem_base_dir_usa_path_legado(tmp_path, monkeypatch):
    """Sem base_dir, escreve em docs/Time_1_Requisitos/setup-ADK/AgenteAnalista/."""
    monkeypatch.chdir(tmp_path)
    caminho = gerar_doubt_artifact(**_kwargs())
    p = Path(caminho)
    assert p.is_file()
    # path absoluto, mas o subdir esperado está no meio
    assert "docs/Time_1_Requisitos/setup-ADK/AgenteAnalista" in str(p)
    assert p.name.startswith("Doubt_Artifact_D-001_")


def test_gerar_doubt_com_base_dir_escreve_no_workspace(tmp_path):
    """Com base_dir setado, escreve direto em <base_dir>/Doubt_Artifact_*.md."""
    base = tmp_path / "ws" / "requirements"
    base.mkdir(parents=True)
    caminho = gerar_doubt_artifact(**_kwargs(base_dir=str(base)))
    p = Path(caminho)
    assert p.is_file()
    assert p.parent == base
    assert p.name.startswith("Doubt_Artifact_D-001_")
    # Conteúdo preserva cabeçalho do template
    content = p.read_text(encoding="utf-8")
    assert "# Doubt_Artifact — Registro de Dúvida do Agente" in content
    assert "### D-001" in content
    assert "HU-001" in content


def test_gerar_doubt_sanitiza_id_duvida(tmp_path):
    """Caracteres não-alfanuméricos em id_duvida são sanitizados no nome do arquivo."""
    base = tmp_path / "ws"
    base.mkdir()
    caminho = gerar_doubt_artifact(**_kwargs(id_duvida="D/001 with spaces", base_dir=str(base)))
    p = Path(caminho)
    assert p.is_file()
    assert " " not in p.name
    assert "/" not in p.name
