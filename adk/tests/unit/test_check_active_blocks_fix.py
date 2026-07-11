"""Testes do fix de baixo risco em check_active_blocks (design_filesystem.py).

Contexto: ver DIAGNOSTICO_BLOQUEIO_HITL_2026-07.md. Doubt_Artifacts gerados
por diferentes agentes acabaram salvos fora de design/doubts/ e/ou usando
"Status: Pendente" em vez do contrato canônico "**Status:** Bloqueado",
fazendo check_active_blocks() nunca detectar o bloqueio e o pipeline
"avançar automaticamente" sem pausar de verdade.

Este teste cobre:
1. Regressão do contrato canônico original (doubts/ + "**Status:** Bloqueado").
2. O novo comportamento aditivo (pasta errada + "EXECUÇÃO PAUSADA").
3. Que um Doubt_Artifact já resolvido não é (falsamente) reportado como bloqueio.
"""

import pytest

from shared.tools import design_filesystem as df


@pytest.fixture
def design_root(tmp_path, monkeypatch):
    root = tmp_path / "design"
    monkeypatch.setattr(df, "DESIGN_DIR", root)
    monkeypatch.setattr(df, "ADK_DIR", tmp_path)
    return root


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_contrato_canonico_continua_funcionando(design_root):
    """Regressão: doubt em doubts/ com '**Status:** Bloqueado' — como antes."""
    _write(
        design_root / "doubts" / "Doubt_Artifact_HU-001_20260101.md",
        "# Doubt\n\n**Status:** Bloqueado\n",
    )

    result = df.check_active_blocks(caller="teste")

    assert result["status"] == "ok"
    assert result["has_blocks"] is True
    assert result["blocks"][0]["folder"] == "doubt"


def test_doubt_em_pasta_errada_agora_e_detectado(design_root):
    """Fix: doubt salvo em diagrams/ (pasta errada) ainda é detectado."""
    _write(
        design_root / "diagrams" / "Doubt_Artifact_Clarification.md",
        "> EXECUÇÃO PAUSADA — INTERVENÇÃO NECESSÁRIA\n\nStatus: Pendente\n",
    )

    result = df.check_active_blocks(caller="teste")

    assert result["has_blocks"] is True
    assert result["blocks"][0]["folder"] == "diagrams"


def test_doubt_em_pasta_nao_mapeada_validation_e_detectado(design_root):
    """Fix: doubt salvo em design/validation/ (pasta que nem existia no
    mapa de diretorios) agora e detectado, sem precisar virar destino
    oficial de escrita."""
    _write(
        design_root / "validation" / "Doubt_Artifact_Bloqueio_Validator.md",
        "> EXECUÇÃO PAUSADA — INTERVENÇÃO NECESSÁRIA\n\nStatus: Pendente\n",
    )

    result = df.check_active_blocks(caller="teste")

    assert result["has_blocks"] is True
    assert result["blocks"][0]["folder"] == "validation"


def test_doubt_resolvido_nao_e_reportado_como_bloqueio(design_root):
    """Nao deve haver falso positivo: um doubt ja resolvido (sem o
    cabecalho de pausa e sem o status canonico de bloqueio) nao conta."""
    _write(
        design_root / "doubts" / "Doubt_Artifact_HU-002_20260101.md",
        "# Doubt\n\n**Status:** Resolvido\n",
    )

    result = df.check_active_blocks(caller="teste")

    assert result["has_blocks"] is False
    assert result["blocks"] == []


def test_sem_nenhum_doubt_retorna_sem_bloqueio(design_root):
    result = df.check_active_blocks(caller="teste")

    assert result["status"] == "ok"
    assert result["has_blocks"] is False
    assert result["blocks"] == []


def test_mesmo_arquivo_nao_e_contado_duas_vezes(design_root):
    """Sanidade: garante que o dedup por path resolvido funciona (nenhum
    arquivo aparece em mais de uma pasta escaneada simultaneamente)."""
    _write(
        design_root / "doubts" / "Doubt_Artifact_HU-003_20260101.md",
        "**Status:** Bloqueado\n",
    )

    result = df.check_active_blocks(caller="teste")

    assert len(result["blocks"]) == 1
