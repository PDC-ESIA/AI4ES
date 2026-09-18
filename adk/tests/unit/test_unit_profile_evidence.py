"""Valida as evidências versionadas dos perfis unitários."""

import json
import re
from pathlib import Path

import pytest

_RESULTS = (
    Path(__file__).resolve().parents[3]
    / "docs/Time_3_Testes/evidencias/evidencias_unit_profiles/runs"
    / "handoff-final-20260831/results"
)
_PROFILES = (
    "python-pytest",
    "node-vitest",
    "node-jest",
    "node-node-test",
    "node-mocha",
    "java-junit",
    "go-testing",
)
_ABSOLUTE_PATH = re.compile(r'":\s*"(?:[A-Za-z]:\\\\|/(?:home|Users)/)')


@pytest.mark.parametrize("profile_id", _PROFILES)
def test_evidencia_unitaria_e_valida_portavel_e_bem_sucedida(profile_id):
    raw = (_RESULTS / profile_id / "evidence.json").read_text(encoding="utf-8-sig")
    evidence = json.loads(raw)

    assert evidence["status"] == "sucesso"
    assert evidence["case"]["profile_id"] == profile_id
    assert evidence["inspection"]["perfil"]["profile_id"] == profile_id
    assert evidence["normalized_result"]["total"] >= 2
    assert not _ABSOLUTE_PATH.search(raw)
