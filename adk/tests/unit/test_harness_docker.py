"""Tests para os helpers determinísticos do harness Docker.

Cobre o que restou de determinístico em `shared/tools/harness_docker.py`: as
constantes de infraestrutura do container. A detecção de entrypoint/requirements
e a geração de Dockerfile saíram do módulo quando o Dockerfile passou a ser
resolvido por LLM; a descoberta de rota principal saiu junto com o healthcheck
baseado em OpenAPI.
"""

from shared.tools.coding_tools import harness_docker as hd


# ===========================================================================
# Constante de porta fixa
# ===========================================================================

def test_host_port_is_fixed_8000():
    assert hd._HOST_PORT == 8000
