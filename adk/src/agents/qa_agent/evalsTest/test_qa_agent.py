import pytest

from src.agents.qa_agent.tools.receive_requirements import (
    _processar_artefato,
    _processar_todos_em_paralelo,
    _validar_artefato,
    _gerar_doubt_artifact,
)


def test_validar_artefato_valido(artefato_rf_valido):
    assert _validar_artefato(artefato_rf_valido) is None

def test_validar_artefato_sem_conteudo():
    assert _validar_artefato({"id_artefato": "RF-001", "tipo": "RF", "conteudo": "", "modulo": "auth"}) is not None

def test_validar_artefato_sem_modulo():
    assert _validar_artefato({"id_artefato": "RF-001", "tipo": "RF", "conteudo": "desc", "modulo": ""}) is not None

def test_validar_artefato_tipo_desconhecido():
    assert _validar_artefato({"id_artefato": "RF-001", "tipo": "XPTO", "conteudo": "desc", "modulo": "auth"}) is not None

async def test_processar_artefato_valido(artefato_rf_valido):
    resultado = await _processar_artefato(artefato_rf_valido)
    assert resultado["status"] == "sucesso"
    assert resultado["arquivo_gerado"] is not None

async def test_processar_artefato_invalido_gera_doubt(artefato_invalido):
    resultado = await _processar_artefato(artefato_invalido)
    assert resultado["status"] == "bloqueado"
    assert resultado["arquivo_duvida"] is not None

async def test_processar_artefato_vazio_nao_trava():
    resultado = await _processar_artefato({})
    assert resultado["status"] in ("bloqueado", "falha")

async def test_processar_em_paralelo_retorna_todos(lista_artefatos_mista):
    resultados = await _processar_todos_em_paralelo(lista_artefatos_mista)
    assert len(resultados) == len(lista_artefatos_mista)

async def test_artefato_bloqueado_nao_interrompe_outros(lista_artefatos_mista):
    resultados = await _processar_todos_em_paralelo(lista_artefatos_mista)
    status_list = [r["status"] for r in resultados]
    assert "sucesso" in status_list
    assert "bloqueado" in status_list

async def test_doubt_artifact_cria_arquivo():
    from pathlib import Path
    caminho = await _gerar_doubt_artifact("TEST-001", "Motivo de teste")
    assert Path(caminho).exists()
    assert "Doubt_Artifact_TEST-001" in caminho
