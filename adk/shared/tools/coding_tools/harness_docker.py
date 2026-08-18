"""Helpers HTTP determinísticos do harness de execução.

Após o desacoplamento de tecnologias (issue #370), o build/run/cleanup do
artefato passou a ser responsabilidade da abstração de sandbox
(`shared/execution/sandbox.py`), dirigida pelo manifesto `run.json`. Este módulo
retém apenas os helpers de *homologação HTTP* de um serviço já no ar:
constantes de healthcheck e a descoberta best-effort da rota principal.

As funções aqui são determinísticas e não conhecem o agente/LLM: recebem
URL/módulo HTTP e retornam dados.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes de homologação HTTP (perfil service)
# ---------------------------------------------------------------------------
_STARTUP_GRACE_PERIOD = 5  # segundos para o serviço inicializar antes do 1º GET
_HTTP_HEALTHCHECK_TIMEOUT = 10  # timeout do GET de homologação
_HEALTHCHECK_RETRIES = 3  # tentativas de healthcheck HTTP
_HEALTHCHECK_RETRY_INTERVAL = 2  # segundos entre retries
_OPENAPI_ENDPOINT = "/openapi.json"  # schema de rotas p/ descobrir rota principal


# ===========================================================================
# Descoberta de rota principal (best-effort, via OpenAPI quando disponível)
# ===========================================================================

def _discover_main_route(base_url: str, http_mod) -> Optional[str]:
    """Descobre a rota principal da app via /openapi.json.

    Estratégia (best-effort, degrada para "/" quando o schema não existe):
    1. Busca /openapi.json (serviços que o expõem — ex.: FastAPI)
    2. Filtra rotas GET excluindo /docs, /openapi.json, /redoc
    3. Prioriza "/" (raiz), depois a primeira rota com GET
    4. Retorna None se não encontrar rota GET candidata (API pura sem HTML)
    """
    _SKIP_ROUTES = {"/docs", "/docs/oauth2-redirect", "/openapi.json", "/redoc"}

    try:
        resp = http_mod.get(
            f"{base_url}{_OPENAPI_ENDPOINT}",
            timeout=_HTTP_HEALTHCHECK_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.warning("[HARNESS] Não foi possível obter /openapi.json")
            return "/"  # fallback: tenta raiz

        schema = resp.json()
        paths = schema.get("paths", {})

        # Coletar rotas GET que não são internas
        get_routes = []
        for path, methods in paths.items():
            if path in _SKIP_ROUTES:
                continue
            if "get" in methods:
                get_routes.append(path)

        if not get_routes:
            return None  # app não tem GET routes (improvável mas possível)

        # Priorizar raiz
        if "/" in get_routes:
            return "/"

        # Retorna a primeira rota GET (ordem de declaração no código)
        return get_routes[0]

    except Exception as e:
        logger.warning(f"[HARNESS] Erro ao descobrir rota principal: {e}")
        return "/"  # fallback: tenta raiz
