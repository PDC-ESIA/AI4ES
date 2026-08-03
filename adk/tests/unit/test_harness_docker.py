"""Tests para os helpers determinísticos do harness Docker.

Cobre as funções puras extraídas para `shared/tools/harness_docker.py`
(detecção de entrypoint/requirements, geração de Dockerfile fallback e
descoberta de rota principal). Relocado de test_cr_executor.py quando o
executor deixou de rodar Docker diretamente (passou a compor o harness).
"""

from unittest.mock import MagicMock

from shared.tools import harness_docker as hd


# ===========================================================================
# _detect_entrypoint
# ===========================================================================

def test_detect_entrypoint_app_main(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")
    assert hd._detect_entrypoint(tmp_path) == "app/main.py"


def test_detect_entrypoint_main_py_raiz(tmp_path):
    (tmp_path / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")
    assert hd._detect_entrypoint(tmp_path) == "main.py"


def test_detect_entrypoint_busca_fastapi_em_rglob(tmp_path):
    (tmp_path / "src" / "server").mkdir(parents=True)
    (tmp_path / "src" / "server" / "api.py").write_text("from fastapi import FastAPI")
    assert "api.py" in hd._detect_entrypoint(tmp_path)


def test_detect_entrypoint_fallback_main(tmp_path):
    (tmp_path / "utils.py").write_text("# nada aqui")
    assert hd._detect_entrypoint(tmp_path) == "main.py"


# ===========================================================================
# _detect_requirements
# ===========================================================================

def test_detect_requirements_encontra_na_raiz(tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi\nuvicorn")
    assert hd._detect_requirements(tmp_path) == "requirements.txt"


def test_detect_requirements_encontra_em_subdir(tmp_path):
    (tmp_path / "requirements").mkdir()
    (tmp_path / "requirements" / "base.txt").write_text("fastapi")
    assert hd._detect_requirements(tmp_path) == "requirements/base.txt"


def test_detect_requirements_retorna_none_se_ausente(tmp_path):
    assert hd._detect_requirements(tmp_path) is None


# ===========================================================================
# _generate_dockerfile
# ===========================================================================

def test_generate_dockerfile_com_requirements(tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi\nuvicorn[standard]")
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")

    dockerfile = hd._generate_dockerfile(tmp_path)
    assert "COPY requirements.txt" in dockerfile
    assert "pip install" in dockerfile
    assert "EXPOSE 8000" in dockerfile
    assert "uvicorn" in dockerfile
    assert "app.main:app" in dockerfile


def test_generate_dockerfile_sem_requirements_fallback(tmp_path):
    (tmp_path / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")

    dockerfile = hd._generate_dockerfile(tmp_path)
    assert "fastapi" in dockerfile
    assert "uvicorn" in dockerfile
    assert "jinja2" in dockerfile


def test_generate_dockerfile_com_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='myapp'")
    (tmp_path / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")

    dockerfile = hd._generate_dockerfile(tmp_path)
    assert "COPY pyproject.toml" in dockerfile
    assert "pip install" in dockerfile


# ===========================================================================
# _discover_main_route
# ===========================================================================

def _mock_http(json_data):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_data
    http = MagicMock()
    http.get.return_value = resp
    return http


def test_discover_main_route_prioriza_raiz():
    http = _mock_http({
        "paths": {
            "/": {"get": {}},
            "/users": {"get": {}},
            "/docs": {"get": {}},
            "/openapi.json": {"get": {}},
        }
    })
    assert hd._discover_main_route("http://localhost:8000", http) == "/"


def test_discover_main_route_ignora_docs():
    http = _mock_http({
        "paths": {
            "/docs": {"get": {}},
            "/openapi.json": {"get": {}},
            "/redoc": {"get": {}},
            "/register": {"get": {}},
        }
    })
    assert hd._discover_main_route("http://localhost:8000", http) == "/register"


def test_discover_main_route_sem_get_routes():
    http = _mock_http({
        "paths": {
            "/docs": {"get": {}},
            "/openapi.json": {"get": {}},
            "/api/items": {"post": {}},
        }
    })
    assert hd._discover_main_route("http://localhost:8000", http) is None


def test_discover_main_route_fallback_on_error():
    http = MagicMock()
    http.get.side_effect = Exception("connection error")
    assert hd._discover_main_route("http://localhost:8000", http) == "/"


# ===========================================================================
# Constante de porta fixa
# ===========================================================================

def test_host_port_is_fixed_8000():
    assert hd._HOST_PORT == 8000
