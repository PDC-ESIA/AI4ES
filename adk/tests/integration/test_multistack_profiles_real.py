"""Valida as evidências reais versionadas de integração e E2E."""

import json
import re
from pathlib import Path

import pytest

_RESULTS = (
    Path(__file__).resolve().parents[3]
    / "docs/Time_3_Testes/evidencias/evidencias_multilevel/runs"
    / "handoff-final-20260831/results"
)
_PROFILES = (
    ("integration", "python-integration"),
    ("integration", "node-integration"),
    ("integration", "java-integration"),
    ("integration", "go-integration"),
    ("e2e", "python-e2e"),
    ("e2e", "node-e2e"),
    ("e2e", "java-e2e"),
    ("e2e", "go-e2e"),
)
_ABSOLUTE_PATH = re.compile(r'":\s*"(?:[A-Za-z]:\\\\|/(?:home|Users)/)')

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(("level", "profile_id"), _PROFILES)
def test_evidencia_real_e_valida_portavel_e_bem_sucedida(level, profile_id):
    raw = (_RESULTS / level / profile_id / "evidence.json").read_text(
        encoding="utf-8-sig"
    )
    evidence = json.loads(raw)

    assert evidence["status"] == "sucesso"
    if level == "integration":
        assert evidence["case"]["profile_id"] == profile_id
        assert evidence["normalized_result"]["testes"]["total"] >= 2
    else:
        assert evidence["profile"]["profile_id"] == profile_id
        assert evidence["execution"]["testes_aprovados"] >= 1
    assert evidence["normalized_result"]["status"] == "sucesso"
    assert not _ABSOLUTE_PATH.search(raw)
