"""Helpers determinísticos do harness de execução em Docker.

Concentra a lógica pura de build/run/cleanup de container e descoberta de rota
usada pelo executor do workflow coding_review. Extraído de
`src/agents/workflow_coding_review/cr_executor.py` (refatoração sem mudança de
comportamento) para permitir reuso pelas próximas fatias do harness.

As funções aqui são determinísticas e não conhecem o agente/LLM: recebem
caminhos/clientes e retornam dados. Nenhuma lógica foi alterada na extração.
"""

import logging
from pathlib import Path

import docker

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes Docker
# ---------------------------------------------------------------------------
_IMAGE_TAG = "cr-executor-app:latest"
_CONTAINER_NAME = "cr-executor-run"
_HOST_PORT = 8000  # porta fixa no host — permite README hardcodar URL
_BUILD_TIMEOUT = 300  # segundos
_HEALTHCHECK_TIMEOUT = 15  # segundos para container sair de "created"
_STARTUP_GRACE_PERIOD = 5  # segundos para o app inicializar dentro do container
_HTTP_HEALTHCHECK_TIMEOUT = 10  # timeout do GET de homologação
_HEALTHCHECK_RETRIES = 3  # tentativas de healthcheck HTTP
_HEALTHCHECK_RETRY_INTERVAL = 2  # segundos entre retries
_MEMORY_LIMIT = "512m"
_CPU_QUOTA = 50000  # 50 % de 1 core


# ===========================================================================
# Helpers internos
# ===========================================================================

def _write_report(report_path: Path, content: str) -> None:
    """Persiste relatório de execução."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(content, encoding="utf-8")
    logger.info(f"[CR EXECUTOR] Relatório salvo: {report_path}")


def _cleanup_container(client: docker.DockerClient, name: str) -> None:
    """Remove container existente (se houver) para evitar conflitos."""
    try:
        old = client.containers.get(name)
        old.remove(force=True)
    except docker.errors.NotFound:
        pass
    except Exception as e:
        logger.warning(f"[CR EXECUTOR] Falha ao remover container '{name}': {e}")
