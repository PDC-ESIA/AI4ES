"""Matriz real, offline e reproduzível dos perfis de integração e E2E."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from shared.testing.multilevel_evidence import (
    E2E_EVIDENCE_PROFILES,
    INTEGRATION_EVIDENCE_CASES,
    collect_e2e_profile_evidence,
    collect_integration_profile_evidence,
)

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("profile_id", sorted(INTEGRATION_EVIDENCE_CASES))
def test_perfil_de_integracao_executa_no_runtime_real(tmp_path, profile_id):
    evidence = collect_integration_profile_evidence(profile_id, tmp_path)

    assert evidence["status"] == "sucesso"
    assert evidence["runtime"]["available"] is True
    assert evidence["inspection"]["perfil"]["profile_id"] == profile_id
    assert evidence["normalized_result"]["status"] == "sucesso"
    assert evidence["normalized_result"]["testes"]["total"] >= 2


@pytest.mark.parametrize("profile_id", E2E_EVIDENCE_PROFILES)
def test_perfil_e2e_executa_chromium_real_em_loopback(profile_id):
    with TemporaryDirectory(prefix="qa-e2e-", dir=Path.cwd()) as temporary:
        evidence = collect_e2e_profile_evidence(profile_id, Path(temporary))

        assert evidence["status"] == "sucesso"
        assert evidence["runtime"]["available"] is True
        assert evidence["execution"]["status"] == "aprovado"
        assert evidence["execution"]["testes_aprovados"] == 1
        assert evidence["normalized_result"]["status"] == "sucesso"
