"""Testes dos perfis de execução (`shared/execution/profile.py`).

Cobertura:
- select_profile: retorna o perfil correto por superfície; superfície inválida levanta;
- características declarativas de cada perfil (S/C/B): starts_service, validates_http,
  critical_stages — em especial que só S tem inicializacao_aplicacao como crítico;
- surface_for_product_type: mapeamento e degradação conservadora para 'none'.
"""

import pytest

from shared.execution.profile import (
    REGISTRY,
    ExecutionProfile,
    select_profile,
    surface_for_product_type,
)

_INICIALIZACAO = "inicializacao_aplicacao"


# ---------------------------------------------------------------------------
# select_profile
# ---------------------------------------------------------------------------

def test_select_profile_por_superficie():
    assert select_profile("service").name == "S"
    assert select_profile("command").name == "C"
    assert select_profile("none").name == "B"


def test_select_profile_superficie_invalida():
    with pytest.raises(ValueError, match="desconhecida"):
        select_profile("serverless")


def test_registry_cobre_as_tres_superficies():
    assert set(REGISTRY) == {"service", "command", "none"}
    assert all(isinstance(p, ExecutionProfile) for p in REGISTRY.values())


# ---------------------------------------------------------------------------
# Características declarativas dos perfis
# ---------------------------------------------------------------------------

def test_perfil_service():
    p = select_profile("service")
    assert p.starts_service is True
    assert p.validates_http is True
    assert _INICIALIZACAO in p.critical_stages


def test_perfil_command():
    p = select_profile("command")
    assert p.starts_service is False
    assert p.validates_http is False
    assert _INICIALIZACAO not in p.critical_stages


def test_perfil_none():
    p = select_profile("none")
    assert p.starts_service is False
    assert p.validates_http is False
    assert _INICIALIZACAO not in p.critical_stages


def test_apenas_service_tem_inicializacao_critica():
    """Só o perfil S pode falhar criticamente na inicialização (estágio 4)."""
    com_inicializacao = [
        p.name for p in REGISTRY.values() if _INICIALIZACAO in p.critical_stages
    ]
    assert com_inicializacao == ["S"]


def test_preparacao_e_implantacao_criticas_em_todos():
    for p in REGISTRY.values():
        assert "preparacao_ambiente" in p.critical_stages
        assert "implantacao_artefato" in p.critical_stages


def test_profile_e_imutavel():
    p = select_profile("service")
    with pytest.raises(Exception):
        p.starts_service = False  # frozen dataclass


# ---------------------------------------------------------------------------
# surface_for_product_type
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "product_type,esperado",
    [
        ("web_app", "service"),
        ("api_service", "service"),
        ("cli", "command"),
        ("data_pipeline", "command"),
        ("library", "none"),
        ("desktop_app", "none"),
        ("mobile_app", "none"),
        ("outro", "none"),
        ("a definir", "none"),
    ],
)
def test_surface_for_product_type_mapeamento(product_type, esperado):
    assert surface_for_product_type(product_type) == esperado


def test_surface_for_product_type_case_insensitive():
    assert surface_for_product_type("Web_App") == "service"
    assert surface_for_product_type("  API_SERVICE  ") == "service"


def test_surface_for_product_type_desconhecido_degrada_para_none():
    assert surface_for_product_type("quantum_widget") == "none"


def test_surface_for_product_type_vazio_degrada_para_none():
    assert surface_for_product_type("") == "none"
