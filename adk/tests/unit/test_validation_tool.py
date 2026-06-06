"""
Testes unitários para validation_tool.py

Execute com:
    pytest tests/unit/test_validation_tool.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared.tools.validation_tool import ler_artefatos_gerados


@pytest.fixture
def artefatos(tmp_path, monkeypatch):
    """Cria estrutura de artefatos de teste."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ADK_DOCS_DIR", "docs")
    
    raiz = tmp_path / "docs" / "Time_1_Requisitos"
    (raiz / "HUs").mkdir(parents=True)
    (raiz / "RFs").mkdir(parents=True)
    (raiz / "RNFs").mkdir(parents=True)
    
    (raiz / "HUs" / "HU-001.md").write_text("# HU-001\nConteúdo HU-001")
    (raiz / "RFs" / "RF-001.md").write_text("# RF-001\nConteúdo RF-001")
    (raiz / "RFs" / "RF-002.md").write_text("# RF-002\nConteúdo RF-002")
    (raiz / "RNFs" / "RNF-001.md").write_text("# RNF-001\nConteúdo RNF-001")
    
    return tmp_path


class TestLerArtefatosGerados:
    
    def test_le_todos_artefatos_sem_parametros(self, artefatos):
        """Sem parâmetros, deve ler todos os artefatos."""
        result = ler_artefatos_gerados()
        assert "Total de artefatos lidos: 4" in result
        assert "HU-001" in result
        assert "RF-001" in result
        assert "RF-002" in result
        assert "RNF-001" in result
    
    def test_le_apenas_ids_especificos(self, artefatos):
        """Com IDs, deve ler apenas os especificados."""
        result = ler_artefatos_gerados(ids="HU-001,RF-002")
        assert "Total de artefatos lidos: 2" in result
        assert "HU-001" in result
        assert "RF-002" in result
        assert "RF-001" not in result
        assert "RNF-001" not in result
    
    def test_ids_nao_encontrados(self, artefatos):
        """IDs inexistentes devem ser reportados."""
        result = ler_artefatos_gerados(ids="HU-999,RF-888")
        assert "Nenhum artefato encontrado" in result
        assert "HU-999" in result
        assert "RF-888" in result
    
    def test_ids_parcialmente_encontrados(self, artefatos):
        """Deve ler os encontrados e reportar os não encontrados."""
        result = ler_artefatos_gerados(ids="HU-001,RF-999")
        assert "Total de artefatos lidos: 1" in result
        assert "HU-001" in result
        assert "IDs não encontrados: RF-999" in result
    
    def test_filtra_por_tipo(self, artefatos):
        """Filtro por tipo deve funcionar quando IDs não fornecidos."""
        result = ler_artefatos_gerados(tipo="RF")
        assert "Total de artefatos lidos: 2" in result
        assert "RF-001" in result
        assert "RF-002" in result
        assert "HU-001" not in result
    
    def test_ids_tem_prioridade_sobre_tipo(self, artefatos):
        """Quando IDs fornecidos, tipo deve ser ignorado."""
        result = ler_artefatos_gerados(tipo="RF", ids="HU-001")
        assert "Total de artefatos lidos: 1" in result
        assert "HU-001" in result
        assert "RF-001" not in result
