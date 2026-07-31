"""Tools de execução Docker do cr_executor (workflow_coding_review).

Builda e executa em container Docker isolado o código produzido pelo
cr_coder, e reporta o resultado (build/runtime/homologação HTTP) para que
o LoopAgent decida se encerra (exit_loop) ou volta ao coder.
"""

import logging
import shutil
import textwrap
import time
from pathlib import Path
from typing import Optional

import docker
from docker.errors import BuildError, ContainerError, APIError
from google.adk.tools import ToolContext

from shared.workspace import get_agent_workspace, get_workspace_root

logger = logging.getLogger(__name__)

_CODER_WS = str(get_agent_workspace("cr_coder"))
_EXEC_WS = str(get_agent_workspace("cr_executor"))
_WORKSPACE_ROOT = str(get_workspace_root())

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
_HEALTHCHECK_ENDPOINT = "/docs"  # FastAPI sempre gera /docs (Swagger UI)
_OPENAPI_ENDPOINT = "/openapi.json"  # Schema de rotas para descobrir rota principal
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


def _discover_main_route(base_url: str, http_mod) -> Optional[str]:
    """Descobre a rota principal da app via /openapi.json.

    Estratégia:
    1. Busca /openapi.json (FastAPI sempre gera)
    2. Filtra rotas GET excluindo /docs, /openapi.json, /redoc
    3. Prioriza "/" (raiz), depois a primeira rota com GET
    4. Retorna None se não encontrar rota candidata (API pura sem HTML)
    """
    _SKIP_ROUTES = {"/docs", "/docs/oauth2-redirect", "/openapi.json", "/redoc"}

    try:
        resp = http_mod.get(
            f"{base_url}{_OPENAPI_ENDPOINT}",
            timeout=_HTTP_HEALTHCHECK_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.warning("[CR EXECUTOR] Não foi possível obter /openapi.json")
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
        logger.warning(f"[CR EXECUTOR] Erro ao descobrir rota principal: {e}")
        return "/"  # fallback: tenta raiz


# ===========================================================================
# Tools do Executor
# ===========================================================================

def tool_executar_em_docker(tool_context: ToolContext) -> dict:
    """Builda e executa o código do coder em container Docker isolado.

    Fluxo:
    1. Copia workspace do coder para diretório de build temporário.
    2. Usa Dockerfile do coder (ou gera fallback se ausente).
    3. Builda imagem Docker.
    4. Roda container com limites de recurso e timeout.
    5. Captura logs (stdout + stderr).
    6. Persiste relatório em coder/execution/.

    Returns:
        dict com chaves:
        - status: "sucesso" | "falha_build" | "falha_runtime" | "erro"
        - logs_build: str (logs do docker build)
        - logs_runtime: str (stdout/stderr do container)
        - entrypoint: str (entrypoint detectado)
        - dockerfile: str (conteúdo do Dockerfile usado)
        - report_path: str (caminho do relatório salvo)
        - duracao_segundos: float
        - mensagem: str
    """
    src_dir = Path(_CODER_WS)
    exec_dir = Path(_EXEC_WS)
    build_dir = exec_dir / "build"
    report_path = exec_dir / "execution_report.md"
    t0 = time.time()

    # ---- Validação ----
    if not src_dir.exists() or not any(src_dir.rglob("*.py")):
        msg = "Nenhum arquivo Python encontrado no workspace do coder."
        _write_report(report_path, f"# Relatório de Execução\n\n**Status:** ERRO\n\n{msg}\n")
        tool_context.state["_last_exec_status"] = "erro"
        return {
            "status": "erro",
            "logs_build": "",
            "logs_runtime": "",
            "entrypoint": "",
            "dockerfile": "",
            "report_path": str(report_path),
            "duracao_segundos": round(time.time() - t0, 2),
            "mensagem": msg,
        }

    # ---- Preparar diretório de build (cópia isolada) ----
    if build_dir.exists():
        shutil.rmtree(build_dir)
    shutil.copytree(src_dir, build_dir, dirs_exist_ok=True)

    # ---- Dockerfile (do coder ou fallback) ----
    dockerfile_path = build_dir / "Dockerfile"
    if not dockerfile_path.exists():
        dockerfile_content = _generate_dockerfile(build_dir)
        dockerfile_path.write_text(dockerfile_content, encoding="utf-8")
        logger.warning(
            "[CR EXECUTOR] Dockerfile NÃO encontrado no workspace do coder. "
            "Gerado automaticamente como fallback."
        )
    else:
        dockerfile_content = dockerfile_path.read_text(encoding="utf-8")
        logger.info("[CR EXECUTOR] Dockerfile do coder encontrado e reutilizado.")

    entrypoint = _detect_entrypoint(build_dir)

    # ---- Docker build ----
    try:
        client = docker.from_env()
    except Exception as e:
        msg = f"Não foi possível conectar ao Docker daemon: {e}"
        _write_report(report_path, f"# Relatório de Execução\n\n**Status:** ERRO\n\n{msg}\n")
        tool_context.state["_last_exec_status"] = "erro"
        return {
            "status": "erro",
            "logs_build": "",
            "logs_runtime": "",
            "entrypoint": entrypoint,
            "dockerfile": dockerfile_content,
            "report_path": str(report_path),
            "duracao_segundos": round(time.time() - t0, 2),
            "mensagem": msg,
        }

    build_logs = ""
    try:
        logger.info(f"[CR EXECUTOR] Iniciando build da imagem '{_IMAGE_TAG}'...")
        image, build_log_gen = client.images.build(
            path=str(build_dir),
            tag=_IMAGE_TAG,
            rm=True,
            forcerm=True,
            timeout=_BUILD_TIMEOUT,
        )
        build_log_lines = []
        for chunk in build_log_gen:
            line = chunk.get("stream", "").strip()
            if line:
                build_log_lines.append(line)
            err = chunk.get("error", "")
            if err:
                build_log_lines.append(f"ERROR: {err}")
        build_logs = "\n".join(build_log_lines)
        logger.info("[CR EXECUTOR] Build concluído com sucesso.")
    except BuildError as e:
        build_logs = str(e)
        logger.error(f"[CR EXECUTOR] Falha no build: {e}")
        report = textwrap.dedent(f"""\
            # Relatório de Execução

            **Status:** FALHA_BUILD
            **Entrypoint detectado:** `{entrypoint}`

            ## Dockerfile
            ```dockerfile
            {dockerfile_content}
            ```

            ## Logs de Build
            ```
            {build_logs}
            ```
        """)
        _write_report(report_path, report)
        tool_context.state["_last_exec_status"] = "falha_build"
        return {
            "status": "falha_build",
            "logs_build": build_logs,
            "logs_runtime": "",
            "entrypoint": entrypoint,
            "dockerfile": dockerfile_content,
            "report_path": str(report_path),
            "duracao_segundos": round(time.time() - t0, 2),
            "mensagem": "Falha ao construir a imagem Docker.",
        }
    except APIError as e:
        msg = f"Erro da API Docker no build: {e}"
        _write_report(report_path, f"# Relatório de Execução\n\n**Status:** ERRO\n\n{msg}\n")
        tool_context.state["_last_exec_status"] = "erro"
        return {
            "status": "erro",
            "logs_build": str(e),
            "logs_runtime": "",
            "entrypoint": entrypoint,
            "dockerfile": dockerfile_content,
            "report_path": str(report_path),
            "duracao_segundos": round(time.time() - t0, 2),
            "mensagem": msg,
        }

    # ---- Docker run + Teste de Homologação ----
    runtime_logs = ""
    run_status = "sucesso"
    run_msg = "Container executado com sucesso."
    host_port = _HOST_PORT

    _cleanup_container(client, _CONTAINER_NAME)

    try:
        logger.info(f"[CR EXECUTOR] Iniciando container '{_CONTAINER_NAME}'...")
        container = client.containers.run(
            image=_IMAGE_TAG,
            name=_CONTAINER_NAME,
            detach=True,
            mem_limit=_MEMORY_LIMIT,
            cpu_quota=_CPU_QUOTA,
            ports={"8000/tcp": ("0.0.0.0", _HOST_PORT)},
            environment={
                "DATABASE_URL": "sqlite:///./data/app.db",
                "UPLOAD_DIR": "/app/uploads",
            },
        )

        # ---- Fase 1: Aguardar container sair de "created" ----
        deadline = time.time() + _HEALTHCHECK_TIMEOUT
        container_started = False
        while time.time() < deadline:
            container.reload()
            if container.status == "running":
                container_started = True
                break
            if container.status in ("exited", "dead"):
                break
            time.sleep(0.5)

        if not container_started:
            # Container nem iniciou
            runtime_logs = container.logs(timestamps=True).decode("utf-8", errors="replace")
            run_status = "falha_runtime"
            exit_info = container.attrs.get("State", {})
            exit_code = exit_info.get("ExitCode", "?")
            run_msg = (
                f"Container não iniciou. "
                f"Status: {container.status}, ExitCode: {exit_code}"
            )
            logger.warning(f"[CR EXECUTOR] {run_msg}")
        else:
            # ---- Fase 2: Grace period + re-check de estabilidade ----
            logger.info("[CR EXECUTOR] Container iniciado. Aguardando estabilização...")
            time.sleep(_STARTUP_GRACE_PERIOD)

            container.reload()
            runtime_logs = container.logs(timestamps=True).decode("utf-8", errors="replace")

            if container.status != "running":
                # Container crashou durante startup (ex: ImportError, NameError)
                run_status = "falha_runtime"
                exit_info = container.attrs.get("State", {})
                exit_code = exit_info.get("ExitCode", "?")
                run_msg = (
                    f"Container crashou durante inicialização (após {_STARTUP_GRACE_PERIOD}s). "
                    f"Status: {container.status}, ExitCode: {exit_code}"
                )
                logger.warning(f"[CR EXECUTOR] {run_msg}")
            else:
                # ---- Fase 3: HTTP Healthcheck (teste de homologação) ----
                import requests as http_requests

                base_url = f"http://localhost:{_HOST_PORT}"
                healthcheck_url = f"{base_url}{_HEALTHCHECK_ENDPOINT}"
                logger.info(f"[CR EXECUTOR] Teste de homologação: GET {healthcheck_url}")

                # Fase 3a: Verificar que FastAPI está vivo (retry loop em /docs)
                hc_alive = False
                last_error_msg = ""
                for attempt in range(1, _HEALTHCHECK_RETRIES + 1):
                    try:
                        resp = http_requests.get(
                            healthcheck_url,
                            timeout=_HTTP_HEALTHCHECK_TIMEOUT,
                        )
                        if resp.status_code < 400:
                            hc_alive = True
                            logger.info(
                                f"[CR EXECUTOR] App viva: HTTP {resp.status_code} "
                                f"(tentativa {attempt}/{_HEALTHCHECK_RETRIES})"
                            )
                            break
                        else:
                            last_error_msg = (
                                f"App respondeu com HTTP {resp.status_code} em {healthcheck_url}."
                            )
                            break  # HTTP errors são definitivos
                    except http_requests.ConnectionError:
                        last_error_msg = (
                            f"App não respondeu (connection refused em {healthcheck_url})."
                        )
                        logger.info(
                            f"[CR EXECUTOR] Tentativa {attempt}/{_HEALTHCHECK_RETRIES}: "
                            f"connection refused, retrying..."
                        )
                        container.reload()
                        if container.status != "running":
                            last_error_msg = (
                                f"Container parou durante healthcheck "
                                f"(status: {container.status})."
                            )
                            break
                        if attempt < _HEALTHCHECK_RETRIES:
                            time.sleep(_HEALTHCHECK_RETRY_INTERVAL)
                    except http_requests.Timeout:
                        last_error_msg = (
                            f"App não respondeu em {_HTTP_HEALTHCHECK_TIMEOUT}s (timeout)."
                        )
                        if attempt < _HEALTHCHECK_RETRIES:
                            time.sleep(_HEALTHCHECK_RETRY_INTERVAL)
                    except Exception as e:
                        last_error_msg = f"Erro inesperado no healthcheck: {e}"
                        break

                if not hc_alive:
                    run_status = "falha_runtime"
                    run_msg = last_error_msg
                    logger.warning(f"[CR EXECUTOR] {run_msg}")
                    container.reload()
                    runtime_logs = container.logs(timestamps=True).decode("utf-8", errors="replace")
                else:
                    # Fase 3b: Descobrir rota principal via /openapi.json e testá-la
                    main_route = _discover_main_route(base_url, http_requests)
                    if main_route:
                        main_url = f"{base_url}{main_route}"
                        logger.info(f"[CR EXECUTOR] Teste funcional: GET {main_url}")
                        try:
                            main_resp = http_requests.get(
                                main_url, timeout=_HTTP_HEALTHCHECK_TIMEOUT
                            )
                            if main_resp.status_code < 400:
                                run_status = "sucesso"
                                run_msg = (
                                    f"App respondendo com sucesso em {base_url} "
                                    f"(rota principal '{main_route}' → HTTP {main_resp.status_code}). "
                                    f"Container mantido em execução."
                                )
                                logger.info(
                                    f"[CR EXECUTOR] Homologação funcional OK: "
                                    f"{main_route} → HTTP {main_resp.status_code}"
                                )
                            elif main_resp.status_code >= 500:
                                run_status = "falha_runtime"
                                # Extrair corpo do erro para feedback ao coder
                                error_body = main_resp.text[:2000]
                                run_msg = (
                                    f"Rota principal '{main_route}' retornou HTTP "
                                    f"{main_resp.status_code} (Server Error).\n"
                                    f"Erro: {error_body}"
                                )
                                logger.warning(f"[CR EXECUTOR] {run_msg[:200]}")
                                runtime_logs = container.logs(timestamps=True).decode(
                                    "utf-8", errors="replace"
                                )
                            else:
                                # 4xx — rota existe mas não funciona (pode ser auth, etc.)
                                # Consideramos sucesso parcial — app está rodando
                                run_status = "sucesso"
                                run_msg = (
                                    f"App respondendo em {base_url} "
                                    f"(rota '{main_route}' → HTTP {main_resp.status_code}, "
                                    f"pode requerer input). Container mantido em execução."
                                )
                                logger.info(f"[CR EXECUTOR] {run_msg}")
                        except Exception as e:
                            run_status = "falha_runtime"
                            run_msg = f"Erro ao testar rota principal '{main_route}': {e}"
                            logger.warning(f"[CR EXECUTOR] {run_msg}")
                            runtime_logs = container.logs(timestamps=True).decode(
                                "utf-8", errors="replace"
                            )
                    else:
                        # Não encontrou rota principal — app é API pura, /docs basta
                        run_status = "sucesso"
                        run_msg = (
                            f"App respondendo em {base_url} "
                            f"(/docs OK, nenhuma rota HTML detectada). "
                            f"Container mantido em execução."
                        )
                        logger.info(f"[CR EXECUTOR] {run_msg}")

    except ContainerError as e:
        run_status = "falha_runtime"
        runtime_logs = str(e)
        run_msg = f"Erro ao executar container: {e}"
        logger.error(f"[CR EXECUTOR] {run_msg}")
    except APIError as e:
        run_status = "erro"
        runtime_logs = str(e)
        run_msg = f"Erro da API Docker no run: {e}"
        logger.error(f"[CR EXECUTOR] {run_msg}")

    # ---- Decisão: manter ou derrubar container ----
    if run_status == "sucesso":
        # Container rodando e homologado → MANTER para o humano testar
        logger.info(
            f"[CR EXECUTOR] Container MANTIDO em execução para testes manuais. "
            f"Acesse em: http://localhost:{_HOST_PORT}"
        )
    else:
        # Falha → limpar container para não poluir o ambiente
        try:
            c = client.containers.get(_CONTAINER_NAME)
            c.stop(timeout=5)
            c.remove(force=True)
            logger.info("[CR EXECUTOR] Container com falha parado e removido.")
        except Exception:
            pass

    duracao = round(time.time() - t0, 2)

    # ---- Relatório final ----
    status_label = {
        "sucesso": "SUCESSO",
        "falha_runtime": "FALHA_RUNTIME",
        "falha_build": "FALHA_BUILD",
        "erro": "ERRO",
    }.get(run_status, run_status.upper())

    access_url = f"http://localhost:{_HOST_PORT}"
    container_info = ""
    if run_status == "sucesso":
        container_info = (
            f"\n**Container ativo:** `{_CONTAINER_NAME}`\n"
            f"**Acesso:** {access_url}\n"
            f"**Para parar:** `docker stop {_CONTAINER_NAME} && docker rm {_CONTAINER_NAME}`\n"
        )

    report = textwrap.dedent(f"""\
        # Relatório de Execução Docker

        **Status:** {status_label}
        **Entrypoint detectado:** `{entrypoint}`
        **Duração:** {duracao}s
        **Mensagem:** {run_msg}
        {container_info}
        ## Dockerfile
        ```dockerfile
        {dockerfile_content}
        ```

        ## Logs de Build
        ```
        {build_logs[-3000:] if len(build_logs) > 3000 else build_logs}
        ```

        ## Logs de Runtime
        ```
        {runtime_logs[-5000:] if len(runtime_logs) > 5000 else runtime_logs}
        ```
    """)
    _write_report(report_path, report)

    # Armazenar status no session state para o guarded exit_loop
    tool_context.state["_last_exec_status"] = run_status

    return {
        "status": run_status,
        "logs_build": build_logs[-2000:] if len(build_logs) > 2000 else build_logs,
        "logs_runtime": runtime_logs[-3000:] if len(runtime_logs) > 3000 else runtime_logs,
        "entrypoint": entrypoint,
        "dockerfile": dockerfile_content,
        "report_path": str(report_path),
        "duracao_segundos": duracao,
        "mensagem": run_msg,
        "container_name": _CONTAINER_NAME if run_status == "sucesso" else "",
        "access_url": access_url,
    }


def tool_verificar_docker() -> dict:
    """Verifica se o Docker daemon está acessível e pronto.

    Returns:
        dict com:
        - disponivel: bool
        - versao: str (versão do Docker)
        - erro: str ou None
    """
    try:
        client = docker.from_env()
        version_info = client.version()
        return {
            "disponivel": True,
            "versao": version_info.get("Version", "desconhecida"),
            "erro": None,
        }
    except Exception as e:
        return {
            "disponivel": False,
            "versao": "",
            "erro": str(e),
        }


def tool_listar_arquivos_coder() -> dict:
    """Lista todos os arquivos no workspace do coder (coder/src/).

    Returns:
        dict com:
        - arquivos: list[str] (caminhos relativos)
        - total: int
    """
    src_dir = Path(_CODER_WS)
    if not src_dir.exists():
        return {"arquivos": [], "total": 0}
    files = sorted(
        str(p.relative_to(src_dir))
        for p in src_dir.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )
    return {"arquivos": files, "total": len(files)}


def tool_exit_loop_se_sucesso(tool_context: ToolContext) -> dict:
    """Encerra o loop SOMENTE se a última execução Docker foi bem-sucedida.

    Esta ferramenta SUBSTITUI exit_loop e impõe uma trava de segurança:
    - Se a última execução teve status "sucesso" → encerra o loop (escalate).
    - Caso contrário → BLOQUEIA a saída e retorna erro.

    O LLM pode chamar esta ferramenta a qualquer momento, mas ela só terá
    efeito quando a execução Docker realmente teve sucesso.

    Returns:
        dict com:
        - encerrado: bool (True se loop foi encerrado)
        - motivo: str
    """
    status = tool_context.state.get("_last_exec_status", "")

    if status == "sucesso":
        tool_context.actions.escalate = True
        logger.info("[CR EXECUTOR] exit_loop PERMITIDO — execução bem-sucedida.")
        return {
            "encerrado": True,
            "motivo": "Execução Docker bem-sucedida. Loop encerrado.",
        }
    else:
        logger.warning(
            f"[CR EXECUTOR] exit_loop BLOQUEADO — último status: '{status}'. "
            f"O loop DEVE continuar para o coder corrigir."
        )
        return {
            "encerrado": False,
            "motivo": (
                f"BLOQUEADO: última execução teve status '{status}' (não é 'sucesso'). "
                f"O loop NÃO pode ser encerrado. Reporte o erro normalmente — "
                f"o coder receberá seu relatório e corrigirá o código."
            ),
        }
