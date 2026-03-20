import pytest


@pytest.fixture
def artefato_rf_valido():
    return {
        "id_artefato": "RF-001",
        "tipo": "RF",
        "conteudo": "O sistema deve permitir login com e-mail e senha.",
        "modulo": "autenticacao",
        "criticidade": "alta",
    }


@pytest.fixture
def artefato_invalido():
    return {
        "id_artefato": "RF-999",
        "tipo": "RF",
        "conteudo": "",
        "modulo": "",
        "criticidade": "media",
    }


@pytest.fixture
def lista_artefatos_mista(artefato_rf_valido, artefato_invalido):
    return [
        artefato_rf_valido,
        artefato_invalido,
        {
            "id_artefato": "RF-002",
            "tipo": "RF",
            "conteudo": "O sistema deve permitir logout.",
            "modulo": "autenticacao",
            "criticidade": "media",
        },
    ]
