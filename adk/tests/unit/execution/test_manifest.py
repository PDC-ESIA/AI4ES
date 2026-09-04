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


# ---------------------------------------------------------------------------
# acceptance_tests — mapa critério → testes (só a FORMA é tratada aqui)
# ---------------------------------------------------------------------------

def test_acceptance_tests_default_vazio():
    m = RunManifest(surface="none", test=["pytest -q"])
    assert m.acceptance_tests == {}


def test_acceptance_tests_preserva_mapa_bem_formado():
    m = RunManifest(
        surface="none",
        test=["pytest -q"],
        acceptance_tests={"CA-01": ["t/a.py::x"], "CA-02": ["t/b.py::y", "t/b.py::z"]},
    )
    assert m.acceptance_tests == {
        "CA-01": ["t/a.py::x"],
        "CA-02": ["t/b.py::y", "t/b.py::z"],
    }


def test_acceptance_task_id_define_namespace_do_mapa():
    m = RunManifest(
        surface="none",
        test=["pytest -q"],
        acceptance_task_id="TASK-002",
        acceptance_tests={"CA-01": ["t/a.py::x"]},
    )

    assert m.acceptance_task_id == "TASK-002"

    
def test_acceptance_task_id_remove_espacos_externos():
    m = RunManifest(
        surface="none",
        test=["pytest -q"],
        acceptance_task_id="  TASK-002  ",
        acceptance_tests={"CA-01": ["t/a.py::x"]},
    )

    assert m.acceptance_task_id == "TASK-002"


@pytest.mark.parametrize("valor", [42, True, [], {}, "", "   ", None])
def test_acceptance_task_id_malformado_nao_invalida_manifesto(valor):
    """Erro no bookkeeping descarta cobertura, sem impedir build e testes."""
    m = RunManifest(
        surface="none",
        test=["pytest -q"],
        acceptance_task_id=valor,
        acceptance_tests={"CA-01": ["t/a.py::x"]},
    )

    assert m.acceptance_task_id is None
    assert m.acceptance_tests == {"CA-01": ["t/a.py::x"]}


def test_acceptance_tests_aceita_teste_unico_fora_de_lista():
    """Erro comum de LLM; absorver custa nada e evita perder cobertura real."""
    m = RunManifest(
        surface="none", test=["pytest -q"], acceptance_tests={"CA-01": "t/a.py::x"}
    )
    assert m.acceptance_tests == {"CA-01": ["t/a.py::x"]}


@pytest.mark.parametrize(
    "valor", ["texto", 42, ["CA-01"], None]
)
def test_acceptance_tests_malformado_nao_invalida_o_manifesto(valor):
    """O mapa é bookkeeping: recusá-lo abortaria o estágio 1 (crítico).

    Sem esta tolerância, um erro de anotação zeraria a nota técnica do coder —
    punindo tecnicamente algo que não é defeito do artefato.
    """
    m = RunManifest(surface="none", test=["pytest -q"], acceptance_tests=valor)
    assert m.acceptance_tests == {}


def test_acceptance_tests_descarta_entradas_inaproveitaveis_mantendo_o_resto():
    m = RunManifest(
        surface="none",
        test=["pytest -q"],
        acceptance_tests={
            "CA-01": ["t/a.py::x"],
            "CA-02": [],
            "CA-03": ["  ", ""],
            "CA-04": 42,
            "CA-05": [7, "t/b.py::y", None],
        },
    )
    assert m.acceptance_tests == {"CA-01": ["t/a.py::x"], "CA-05": ["t/b.py::y"]}


def test_load_manifest_le_acceptance_tests_do_disco(tmp_path):
    p = tmp_path / "run.json"
    p.write_text(
        json.dumps(
            {
                "surface": "service",
                "run": "uvicorn app:app",
                "port": 8000,
                "test": ["pytest -q"],
                "acceptance_tests": {"CA-01": ["tests/test_a.py::test_x"]},
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p)
    assert m.acceptance_tests == {"CA-01": ["tests/test_a.py::test_x"]}


def test_load_manifest_com_acceptance_tests_invalido_nao_levanta(tmp_path):
    p = tmp_path / "run.json"
    p.write_text(
        json.dumps(
            {
                "surface": "none",
                "test": ["pytest -q"],
                "acceptance_tests": "CA-01",
            }
        ),
        encoding="utf-8",
    )
    assert load_manifest(p).acceptance_tests == {}


def test_load_manifest_com_acceptance_task_id_invalido_nao_levanta(tmp_path):
    p = tmp_path / "run.json"
    p.write_text(
        json.dumps(
            {
                "surface": "none",
                "test": ["pytest -q"],
                "acceptance_task_id": 42,
                "acceptance_tests": {"CA-01": ["tests/test_a.py::test_x"]},
            }
        ),
        encoding="utf-8",
    )

    manifesto = load_manifest(p)
    assert manifesto.acceptance_task_id is None
    assert manifesto.acceptance_tests == {"CA-01": ["tests/test_a.py::test_x"]}
