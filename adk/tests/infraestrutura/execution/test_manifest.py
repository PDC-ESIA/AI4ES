"""Testes do manifesto de execução (`shared/execution/manifest.py`).

Cobertura:
- RunManifest: defaults, validação de coerência surface↔campos, healthcheck default;
- load_manifest: arquivo ausente, JSON inválido, manifesto incoerente, caminho feliz.
"""

import json

import pytest

from shared.execution.manifest import ManifestError, RunManifest, load_manifest


# ---------------------------------------------------------------------------
# RunManifest — modelo e coerência
# ---------------------------------------------------------------------------

def test_service_minimo_valido_com_healthcheck_default():
    """surface=service com run+port é válido; healthcheck default vira '/'."""
    m = RunManifest(surface="service", run="uvicorn app:app", port=8000)
    assert m.healthcheck == "/"
    assert m.sandbox == "direct"  # default
    assert m.schema_version == "1"


def test_service_preserva_healthcheck_explicito():
    m = RunManifest(surface="service", run="run", port=8000, healthcheck="/docs")
    assert m.healthcheck == "/docs"


def test_service_sem_run_rejeitado():
    with pytest.raises(Exception):
        RunManifest(surface="service", port=8000)


def test_service_sem_port_rejeitado():
    with pytest.raises(Exception):
        RunManifest(surface="service", run="run")


def test_command_exige_run():
    with pytest.raises(Exception):
        RunManifest(surface="command")
    # com run é válido
    m = RunManifest(surface="command", run="python cli.py")
    assert m.run == "python cli.py"


def test_none_exige_build_ou_test():
    with pytest.raises(Exception):
        RunManifest(surface="none")
    # com test é válido
    m = RunManifest(surface="none", test=["pytest -q"])
    assert m.test == ["pytest -q"]
    # com build é válido
    m2 = RunManifest(surface="none", build=["make"])
    assert m2.build == ["make"]


def test_surface_invalida_rejeitada():
    with pytest.raises(Exception):
        RunManifest(surface="serverless", run="run", port=8000)


def test_sandbox_invalido_rejeitado():
    with pytest.raises(Exception):
        RunManifest(surface="command", run="run", sandbox="firecracker")


# ---------------------------------------------------------------------------
# load_manifest — carregamento a partir de arquivo
# ---------------------------------------------------------------------------

def test_load_manifest_arquivo_ausente(tmp_path):
    with pytest.raises(ManifestError, match="não encontrado"):
        load_manifest(tmp_path / "run.json")


def test_load_manifest_json_invalido(tmp_path):
    p = tmp_path / "run.json"
    p.write_text("{ not json", encoding="utf-8")
    with pytest.raises(ManifestError, match="não é JSON válido"):
        load_manifest(p)


def test_load_manifest_incoerente(tmp_path):
    p = tmp_path / "run.json"
    p.write_text(json.dumps({"surface": "service", "run": "run"}), encoding="utf-8")
    with pytest.raises(ManifestError, match="incoerente"):
        load_manifest(p)


def test_load_manifest_caminho_feliz(tmp_path):
    p = tmp_path / "run.json"
    p.write_text(
        json.dumps(
            {
                "surface": "service",
                "build": ["pip install -r requirements.txt"],
                "run": "uvicorn app:app --port 8000",
                "test": ["pytest -q"],
                "port": 8000,
                "healthcheck": "/health",
                "env": {"DATABASE_URL": "sqlite:///./app.db"},
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p)
    assert m.surface == "service"
    assert m.port == 8000
    assert m.healthcheck == "/health"
    assert m.build == ["pip install -r requirements.txt"]
    assert m.env["DATABASE_URL"] == "sqlite:///./app.db"
