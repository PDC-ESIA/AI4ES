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
from typing import Optional

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

def _detect_entrypoint(src_dir: Path) -> str:
    """Detecta o entrypoint principal da aplicação no workspace do coder."""
    candidates = [
        "app/main.py",
        "main.py",
        "src/main.py",
        "src/app/main.py",
        "app.py",
        "server.py",
        "run.py",
        "manage.py",
    ]
    for c in candidates:
        if (src_dir / c).is_file():
            return c
    for py in src_dir.rglob("*.py"):
        try:
            content = py.read_text(encoding="utf-8", errors="ignore")
            if "FastAPI" in content or "uvicorn" in content:
                return str(py.relative_to(src_dir))
        except Exception:
            continue
    return "main.py"


def _detect_requirements(src_dir: Path) -> Optional[str]:
    """Retorna caminho relativo do requirements.txt se existir."""
    for name in ("requirements.txt", "requirements/base.txt", "requirements/prod.txt"):
        if (src_dir / name).is_file():
            return name
    return None


def _has_pyproject(src_dir: Path) -> bool:
    return (src_dir / "pyproject.toml").is_file()


def _generate_dockerfile(src_dir: Path) -> str:
    """Gera Dockerfile fallback otimizado para a stack detectada."""
    entrypoint = _detect_entrypoint(src_dir)
    req_file = _detect_requirements(src_dir)
    has_pyproject = _has_pyproject(src_dir)

    module = entrypoint.replace("/", ".").removesuffix(".py")

    lines = [
        "FROM python:3.12-slim",
        "",
        "WORKDIR /app",
        "",
        "ENV PYTHONDONTWRITEBYTECODE=1 \\",
        "    PYTHONUNBUFFERED=1 \\",
        "    PIP_NO_CACHE_DIR=1",
        "",
    ]

    if req_file:
        lines += [
            f"COPY {req_file} /app/{req_file}",
            f"RUN pip install --no-cache-dir -r {req_file}",
            "",
        ]
    elif has_pyproject:
        lines += [
            "COPY pyproject.toml /app/",
            "RUN pip install --no-cache-dir .",
            "",
        ]
    else:
        lines += [
            "RUN pip install --no-cache-dir fastapi uvicorn[standard] jinja2 python-multipart aiofiles sqlalchemy",
            "",
        ]

    lines += [
        "COPY . /app/",
        "",
        "RUN mkdir -p /app/data /app/uploads",
        "",
        "EXPOSE 8000",
        "",
        f'CMD ["python", "-m", "uvicorn", "{module}:app", "--host", "0.0.0.0", "--port", "8000"]',
    ]

    return "\n".join(lines) + "\n"


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
