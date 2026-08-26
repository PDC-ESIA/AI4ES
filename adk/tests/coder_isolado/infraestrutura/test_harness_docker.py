"""Tests para os helpers HTTP determinísticos do harness.

Após o desacoplamento de tecnologias (issue #370), `harness_docker.py` retém
apenas a homologação HTTP de um serviço já no ar: constantes de healthcheck e a
descoberta best-effort da rota principal via /openapi.json. Build/run/cleanup
migraram para a abstração de sandbox (`shared/execution/sandbox.py`).
"""

from unittest.mock import MagicMock

from shared.tools.coding_tools import harness_docker as hd


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


def test_discover_main_route_status_nao_200_fallback_raiz():
    resp = MagicMock()
    resp.status_code = 404
    http = MagicMock()
    http.get.return_value = resp
    assert hd._discover_main_route("http://localhost:8000", http) == "/"


# ===========================================================================
# Constantes de homologação HTTP
# ===========================================================================

def test_constantes_healthcheck_expostas():
    assert hd._STARTUP_GRACE_PERIOD == 5
    assert hd._HTTP_HEALTHCHECK_TIMEOUT == 10
    assert hd._HEALTHCHECK_RETRIES == 3
    assert hd._HEALTHCHECK_RETRY_INTERVAL == 2
    assert hd._OPENAPI_ENDPOINT == "/openapi.json"
