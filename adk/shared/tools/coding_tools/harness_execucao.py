"""Harness de Execução — orquestração determinística dos 9 estágios de validação.

Este módulo expõe uma única tool determinística, `executar_harness_validacao`,
que executa em Python puro (a ordem NÃO depende de LLM) os nove estágios que
levam o artefato do coder de "arquivos no workspace" até um `ExecutionReport`
consolidado e persistido.

Princípio central: o harness **apenas descreve o que aconteceu e coleta
evidências**. Ele nunca decide se um critério de aceite foi atendido — esse
julgamento pertence ao validador (implementation_validator). Por isso o
`ExecutionReport` não carrega nenhum campo de decisão.

Reaproveita as ferramentas já existentes do repositório:
- `shared/tools/harness_docker.py` — build/run/cleanup de container e rota.
- `shared/tools/log_parser_tool.py` — parsing dos logs de build e runtime.
- `shared/tools/pytest_runner.py` — execução da suíte de testes automatizados.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import docker
import requests
from docker.errors import APIError, BuildError
from google.adk.tools import ToolContext

from shared.tools.coding_tools import harness_docker as hd
from shared.tools.log_parser_tool import parse_log_text
from shared.workspace import get_agent_workspace

logger = logging.getLogger(__name__)

# Estágios críticos (por valor de StageName): se falharem, os estágios que deles
# dependem são pulados. Mantidos como strings para NÃO exigir o import dos
# schemas no topo do módulo — ver a nota de "import tardio" no fim do arquivo,
# que evita um ciclo de import com o pacote `src.agents.executor`.
_CRITICAL_STAGES = (
    "preparacao_ambiente",
    "implantacao_artefato",
    "inicializacao_aplicacao",
)

# Manifesto de execução opcional gravado pelo coder na raiz do workspace.
# Declara, de forma agnóstica de linguagem, COMO o harness deve validar a
# entrega: o modo (service|command), a porta/rota de healthcheck (service) e os
# comandos de execução/teste (command). Ausente → defaults retrocompatíveis
# (service + Python + porta 8000), preservando o comportamento histórico.
_MANIFEST_NAME = ".ai4se_run.json"

# Modos de entrega suportados pelo harness (espelham o enum da Task).
_MODE_SERVICE = "service"  # sobe e fica ouvindo → validação por healthcheck HTTP
_MODE_COMMAND = "command"  # roda e termina → validação por exit code + saída/testes

# Teto para a execução de um artefato em modo 'command' (segundos).
_COMMAND_TIMEOUT = 120


def _carregar_manifesto(coder_dir: Path) -> dict:
    """Lê o manifesto de execução do workspace do coder (best-effort).

    Retorna {} quando o arquivo não existe ou é inválido — nesse caso o harness
    opera nos defaults retrocompatíveis (service + Python). Nunca levanta: um
    manifesto malformado degrada para o default em vez de abortar a execução.
    """
    path = coder_dir / _MANIFEST_NAME
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        logger.warning("[HARNESS] Manifesto %s inválido; usando defaults.", path)
        return {}


# ===========================================================================
# Contexto compartilhado entre estágios
# ===========================================================================

class _HarnessContext:
    """Estado mutável carregado entre os estágios (determinístico, sem LLM)."""

    def __init__(self, task_id: str, coder_dir: Path, exec_dir: Path, tasks_dir: Path):
        self.task_id = task_id
        self.coder_dir = coder_dir
        self.exec_dir = exec_dir
        self.tasks_dir = tasks_dir

        # Preenchidos ao longo dos estágios
        self.acceptance_criteria: list[str] = []
        self.contract: dict = {}
        self.dockerfile: str = ""
        self.build_dir: Optional[Path] = None
        self.docker_client = None
        self.container = None
        self.build_logs: str = ""
        self.runtime_logs: str = ""
        self.base_url: str = f"http://localhost:{hd._HOST_PORT}"
        self.main_route: Optional[str] = None

        # Configuração de execução — derivada do manifesto (.ai4se_run.json) ou
        # dos defaults retrocompatíveis (service + Python + porta 8000).
        self.delivery_mode: str = _MODE_SERVICE
        self.language: str = ""
        self.service_port: int = hd._HOST_PORT          # porta interna do container (service)
        self.healthcheck_path: str = hd._HEALTHCHECK_ENDPOINT
        self.run_cmd: Optional[str] = None              # override do comando (command)
        self.test_cmd: Optional[str] = None             # comando de teste declarado
        self.success_exit_codes: list[int] = [0]        # exit codes aceitos (command)
        self.env: dict = {}                             # env vars extra do manifesto
        self.command_exit_code: Optional[int] = None    # exit code observado (command)

        # Flags de dependência entre estágios
        self.env_ok: bool = False       # estágio 1
        self.deploy_ok: bool = False     # estágio 2
        self.app_ok: bool = False        # estágio 4


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pulado(stage: StageName, motivo: str) -> StageResult:
    """StageResult padrão para um estágio abortado por pré-requisito não atendido."""
    return StageResult(
        stage=stage,
        status=StageStatus.PULADO,
        duration_seconds=0.0,
        summary=motivo,
        evidence={},
        error_code=None,
    )


# ===========================================================================
# Estágio 1 — Preparação do ambiente [crítico]
# ===========================================================================

def _estagio_preparacao(ctx: _HarnessContext) -> StageResult:
    t0 = time.time()
    task_file = ctx.tasks_dir / f"{ctx.task_id}.json"

    if not task_file.is_file():
        return StageResult(
            stage=StageName.PREPARACAO_AMBIENTE,
            status=StageStatus.ERRO,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Task '{ctx.task_id}' não encontrada em {task_file}.",
            evidence={"task_file": str(task_file)},
            error_code="TASK_NAO_ENCONTRADA",
        )

    try:
        task = json.loads(task_file.read_text(encoding="utf-8"))
    except Exception as e:
        return StageResult(
            stage=StageName.PREPARACAO_AMBIENTE,
            status=StageStatus.ERRO,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Falha ao ler/parsear a Task: {e}",
            evidence={"task_file": str(task_file)},
            error_code="TASK_INVALIDA",
        )

    ctx.acceptance_criteria = list(task.get("acceptance_criteria", []))
    ctx.contract = task.get("contract", {}) or {}

    # Modo de entrega declarado pela Task (arquiteto). O manifesto do coder pode
    # confirmá-lo/refiná-lo; a Task é a fonte primária do modo.
    modo_task = task.get("delivery_mode")

    # Configuração de execução: manifesto do coder > modo da Task > defaults.
    manifesto = _carregar_manifesto(ctx.coder_dir)
    modo = manifesto.get("delivery_mode") or modo_task or _MODE_SERVICE
    ctx.delivery_mode = modo if modo in (_MODE_SERVICE, _MODE_COMMAND) else _MODE_SERVICE
    ctx.language = str(manifesto.get("language", "") or "")
    ctx.env = dict(manifesto.get("env", {}) or {})

    service_cfg = manifesto.get("service", {}) or {}
    ctx.service_port = int(service_cfg.get("port", hd._HOST_PORT) or hd._HOST_PORT)
    ctx.healthcheck_path = str(
        service_cfg.get("healthcheck_path") or hd._HEALTHCHECK_ENDPOINT
    )

    run_cfg = manifesto.get("run", {}) or {}
    ctx.run_cmd = run_cfg.get("cmd") or None
    codes = run_cfg.get("success_exit_codes")
    if isinstance(codes, list) and codes:
        ctx.success_exit_codes = [int(c) for c in codes]

    test_cfg = manifesto.get("test", {}) or {}
    ctx.test_cmd = test_cfg.get("cmd") or None

    # Valida o workspace do coder: deve conter algum arquivo de código-fonte.
    # (Antes exigíamos *.py; agora qualquer linguagem é aceita — a validação de
    # que o artefato de fato roda cabe aos estágios de implantação/execução.)
    arquivos = [
        p for p in ctx.coder_dir.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    ]
    if not ctx.coder_dir.exists() or not arquivos:
        return StageResult(
            stage=StageName.PREPARACAO_AMBIENTE,
            status=StageStatus.ERRO,
            duration_seconds=round(time.time() - t0, 3),
            summary="Nenhum arquivo de código encontrado no workspace do coder.",
            evidence={"coder_dir": str(ctx.coder_dir)},
            error_code="SRC_VAZIO",
        )

    # Resolve Dockerfile. Se o coder forneceu um, usa-o (qualquer stack). O
    # fallback determinístico só sabe gerar um Dockerfile Python/web (service);
    # em modo 'command' sem Dockerfile do coder não há como adivinhar o runtime.
    dockerfile_path = ctx.coder_dir / "Dockerfile"
    if dockerfile_path.is_file():
        ctx.dockerfile = dockerfile_path.read_text(encoding="utf-8")
        origem_dockerfile = "coder"
    elif ctx.delivery_mode == _MODE_SERVICE:
        ctx.dockerfile = hd._generate_dockerfile(ctx.coder_dir)
        origem_dockerfile = "fallback"
    else:
        return StageResult(
            stage=StageName.PREPARACAO_AMBIENTE,
            status=StageStatus.ERRO,
            duration_seconds=round(time.time() - t0, 3),
            summary=(
                "Modo 'command' exige um Dockerfile fornecido pelo coder "
                "(o fallback só cobre serviços web Python)."
            ),
            evidence={"coder_dir": str(ctx.coder_dir), "delivery_mode": ctx.delivery_mode},
            error_code="DOCKERFILE_AUSENTE",
        )

    ctx.env_ok = True
    return StageResult(
        stage=StageName.PREPARACAO_AMBIENTE,
        status=StageStatus.SUCESSO,
        duration_seconds=round(time.time() - t0, 3),
        summary=(
            f"Ambiente preparado: Task carregada ({len(ctx.acceptance_criteria)} "
            f"critérios), modo '{ctx.delivery_mode}', Dockerfile de origem "
            f"'{origem_dockerfile}'."
        ),
        evidence={
            "task_file": str(task_file),
            "acceptance_criteria": ctx.acceptance_criteria,
            "dockerfile_origem": origem_dockerfile,
            "delivery_mode": ctx.delivery_mode,
            "language": ctx.language,
        },
        error_code=None,
    )


# ===========================================================================
# Helpers de execução de container (compartilhados entre estágios)
# ===========================================================================

def _env_base(ctx: _HarnessContext) -> dict:
    """Env base para a execução do container; manifesto estende/sobrescreve.

    As chaves default são inócuas para artefatos que não as usam (modo
    'command'), e preservam o comportamento histórico do serviço web Python.
    """
    environment = {
        "DATABASE_URL": "sqlite:///./data/app.db",
        "UPLOAD_DIR": "/app/uploads",
    }
    environment.update(ctx.env)
    return environment


def _rodar_container_ate_fim(
    ctx: _HarnessContext, command, container_name: str, timeout: int
):
    """Roda a imagem já construída com `command` até o processo terminar.

    Compartilhado pelo modo 'command' (execução do artefato) e pelo estágio de
    testes em modo 'command' (execução da suíte declarada em test.cmd). Faz o
    polling do container até ele sair — evita as exceções de timeout do SDK e
    mantém o container para coleta de logs — e devolve o exit code + logs para o
    chamador montar o StageResult.

    Retorna a tupla (exit_code, logs, container, erro), onde `erro` é None em
    término normal ou uma tupla (summary, error_code) quando o container não
    pôde subir (ERRO_RUN) ou estourou o timeout (COMANDO_TIMEOUT).
    """
    client = ctx.docker_client
    hd._cleanup_container(client, container_name)
    try:
        container = client.containers.run(
            image=hd._IMAGE_TAG,
            name=container_name,
            detach=True,
            mem_limit=hd._MEMORY_LIMIT,
            cpu_quota=hd._CPU_QUOTA,
            environment=_env_base(ctx),
            command=command,  # None → usa o CMD do Dockerfile
        )
    except Exception as e:
        return None, "", None, (f"erro ao subir o container: {e}", "ERRO_RUN")

    deadline = time.time() + timeout
    finished = False
    while time.time() < deadline:
        container.reload()
        if container.status in ("exited", "dead"):
            finished = True
            break
        time.sleep(0.5)

    logs = container.logs(timestamps=True).decode("utf-8", errors="replace")
    if not finished:
        try:
            container.kill()
        except Exception:
            pass
        return (
            None,
            logs,
            container,
            (f"comando não terminou dentro de {timeout}s (timeout).", "COMANDO_TIMEOUT"),
        )

    exit_code = container.attrs.get("State", {}).get("ExitCode")
    return exit_code, logs, container, None


# ===========================================================================
# Estágio 2 — Implantação do artefato [crítico]
# ===========================================================================

def _estagio_implantacao(ctx: _HarnessContext) -> StageResult:
    t0 = time.time()

    # Diretório de build isolado (cópia do workspace do coder)
    build_dir = ctx.exec_dir / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    shutil.copytree(ctx.coder_dir, build_dir, dirs_exist_ok=True)
    (build_dir / "Dockerfile").write_text(ctx.dockerfile, encoding="utf-8")
    ctx.build_dir = build_dir

    try:
        client = docker.from_env()
    except Exception as e:
        return StageResult(
            stage=StageName.IMPLANTACAO_ARTEFATO,
            status=StageStatus.ERRO,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Não foi possível conectar ao Docker daemon: {e}",
            evidence={},
            error_code="DOCKER_INDISPONIVEL",
        )
    ctx.docker_client = client

    # ---- Build ----
    try:
        _image, build_log_gen = client.images.build(
            path=str(build_dir),
            tag=hd._IMAGE_TAG,
            rm=True,
            forcerm=True,
            timeout=hd._BUILD_TIMEOUT,
        )
        linhas = []
        for chunk in build_log_gen:
            stream = chunk.get("stream", "").strip()
            if stream:
                linhas.append(stream)
            err = chunk.get("error", "")
            if err:
                linhas.append(f"ERROR: {err}")
        ctx.build_logs = "\n".join(linhas)
    except BuildError as e:
        ctx.build_logs = str(e)
        return StageResult(
            stage=StageName.IMPLANTACAO_ARTEFATO,
            status=StageStatus.FALHA,
            duration_seconds=round(time.time() - t0, 3),
            summary="Falha ao construir a imagem Docker.",
            evidence={"build_logs_tail": ctx.build_logs[-2000:]},
            error_code="FALHA_BUILD",
        )
    except APIError as e:
        ctx.build_logs = str(e)
        return StageResult(
            stage=StageName.IMPLANTACAO_ARTEFATO,
            status=StageStatus.ERRO,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Erro da API Docker no build: {e}",
            evidence={},
            error_code="ERRO_API_BUILD",
        )

    # ---- Run ----
    hd._cleanup_container(client, hd._CONTAINER_NAME)

    if ctx.delivery_mode == _MODE_COMMAND:
        return _run_command_mode(ctx, t0)

    # Env base (harmless para command); manifesto pode sobrescrever/estender.
    environment = _env_base(ctx)

    # ---- Modo 'service': sobe container detached e mapeia a porta ----
    try:
        container = client.containers.run(
            image=hd._IMAGE_TAG,
            name=hd._CONTAINER_NAME,
            detach=True,
            mem_limit=hd._MEMORY_LIMIT,
            cpu_quota=hd._CPU_QUOTA,
            ports={f"{ctx.service_port}/tcp": ("0.0.0.0", hd._HOST_PORT)},
            environment=environment,
        )
    except Exception as e:
        return StageResult(
            stage=StageName.IMPLANTACAO_ARTEFATO,
            status=StageStatus.ERRO,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Erro ao subir o container: {e}",
            evidence={"build_logs_tail": ctx.build_logs[-2000:]},
            error_code="ERRO_RUN",
        )
    ctx.container = container

    # Aguarda o container sair de "created" e ficar "running"
    deadline = time.time() + hd._HEALTHCHECK_TIMEOUT
    started = False
    while time.time() < deadline:
        container.reload()
        if container.status == "running":
            started = True
            break
        if container.status in ("exited", "dead"):
            break
        time.sleep(0.5)

    if not started:
        exit_code = container.attrs.get("State", {}).get("ExitCode", "?")
        ctx.runtime_logs = container.logs(timestamps=True).decode("utf-8", errors="replace")
        return StageResult(
            stage=StageName.IMPLANTACAO_ARTEFATO,
            status=StageStatus.FALHA,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Container não iniciou (status={container.status}, exit={exit_code}).",
            evidence={"container_status": container.status, 
                      "exit_code": exit_code,
                       "runtime_logs_tail": ctx.runtime_logs[-3000:], 
                       },
            error_code="CONTAINER_NAO_INICIOU",
        )

    ctx.deploy_ok = True
    return StageResult(
        stage=StageName.IMPLANTACAO_ARTEFATO,
        status=StageStatus.SUCESSO,
        duration_seconds=round(time.time() - t0, 3),
        summary=f"Imagem construída e container '{hd._CONTAINER_NAME}' em execução.",
        evidence={"image_tag": hd._IMAGE_TAG, "container_name": hd._CONTAINER_NAME},
        error_code=None,
    )


def _run_command_mode(ctx: _HarnessContext, t0: float) -> StageResult:
    """Executa o artefato em modo 'command': roda até terminar e captura o exit.

    Diferente do modo 'service' (container fica ouvindo e é sondado por HTTP),
    aqui o container roda o comando de entrega (CMD do Dockerfile ou `run.cmd`
    do manifesto) e ESPERA-SE que termine. O harness apenas coleta o exit code e
    a saída — o julgamento (exit esperado?) fica no estágio de inicialização.
    """
    exit_code, logs, container, erro = _rodar_container_ate_fim(
        ctx, ctx.run_cmd, hd._CONTAINER_NAME, _COMMAND_TIMEOUT
    )
    ctx.container = container
    ctx.runtime_logs = logs

    if erro is not None:
        summary, error_code = erro
        # Falha ao subir o container é erro de infra (ERRO); timeout é falha do
        # próprio artefato (FALHA).
        status = StageStatus.ERRO if error_code == "ERRO_RUN" else StageStatus.FALHA
        return StageResult(
            stage=StageName.IMPLANTACAO_ARTEFATO,
            status=status,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Modo 'command': {summary}",
            evidence={
                "build_logs_tail": ctx.build_logs[-2000:],
                "runtime_logs_tail": (logs or "")[-3000:],
            },
            error_code=error_code,
        )

    ctx.command_exit_code = exit_code
    ctx.deploy_ok = True
    return StageResult(
        stage=StageName.IMPLANTACAO_ARTEFATO,
        status=StageStatus.SUCESSO,
        duration_seconds=round(time.time() - t0, 3),
        summary=(
            f"Imagem construída e comando executado até o fim "
            f"(exit={ctx.command_exit_code})."
        ),
        evidence={
            "image_tag": hd._IMAGE_TAG,
            "container_name": hd._CONTAINER_NAME,
            "exit_code": ctx.command_exit_code,
        },
        error_code=None,
    )


# ===========================================================================
# Estágio 3 — Coleta dos logs de implantação (build)
# ===========================================================================

def _estagio_coleta_logs_implantacao(ctx: _HarnessContext) -> StageResult:
    if not ctx.env_ok:
        return _pulado(
            StageName.COLETA_LOGS_IMPLANTACAO,
            "Abortado: preparação do ambiente falhou (build não foi tentado).",
        )
    t0 = time.time()
    parsed = parse_log_text(ctx.build_logs)
    erros = [e for e in parsed if e.get("level") in ("ERROR", "CRITICAL", "FATAL")]
    return StageResult(
        stage=StageName.COLETA_LOGS_IMPLANTACAO,
        status=StageStatus.SUCESSO,
        duration_seconds=round(time.time() - t0, 3),
        summary=f"Logs de build coletados: {len(parsed)} linhas, {len(erros)} de erro.",
        evidence={
            "linhas_parseadas": len(parsed),
            "erros": erros[:10],
            "build_logs_tail": ctx.build_logs[-2000:],
        },
        error_code=None,
    )


# ===========================================================================
# Estágio 4 — Inicialização da aplicação [crítico]
# ===========================================================================

def _estagio_inicializacao(ctx: _HarnessContext) -> StageResult:
    if not ctx.deploy_ok:
        return _pulado(
            StageName.INICIALIZACAO_APLICACAO,
            "Abortado: implantação do artefato não foi bem-sucedida.",
        )
    t0 = time.time()

    # Modo 'command': não há servidor a sondar. O "inicializar" já aconteceu na
    # implantação (o comando rodou até o fim); aqui só julgamos o exit code.
    if ctx.delivery_mode == _MODE_COMMAND:
        exit_code = ctx.command_exit_code
        if exit_code in ctx.success_exit_codes:
            ctx.app_ok = True
            return StageResult(
                stage=StageName.INICIALIZACAO_APLICACAO,
                status=StageStatus.SUCESSO,
                duration_seconds=round(time.time() - t0, 3),
                summary=f"Comando terminou com exit code esperado ({exit_code}).",
                evidence={
                    "exit_code": exit_code,
                    "success_exit_codes": ctx.success_exit_codes,
                    "runtime_logs_tail": ctx.runtime_logs[-3000:],
                },
                error_code=None,
            )
        return StageResult(
            stage=StageName.INICIALIZACAO_APLICACAO,
            status=StageStatus.FALHA,
            duration_seconds=round(time.time() - t0, 3),
            summary=(
                f"Comando terminou com exit code {exit_code}, fora dos "
                f"esperados {ctx.success_exit_codes}."
            ),
            evidence={
                "exit_code": exit_code,
                "success_exit_codes": ctx.success_exit_codes,
                "runtime_logs_tail": ctx.runtime_logs[-3000:],
            },
            error_code="COMANDO_EXIT_NAO_ESPERADO",
        )

    # Modo 'service': healthcheck HTTP (comportamento histórico).
    # Grace period para a app subir dentro do container
    time.sleep(hd._STARTUP_GRACE_PERIOD)

    healthcheck_url = f"{ctx.base_url}{ctx.healthcheck_path}"
    alive = False
    ultimo_erro = ""
    status_code = None
    for tentativa in range(1, hd._HEALTHCHECK_RETRIES + 1):
        try:
            resp = requests.get(healthcheck_url, timeout=hd._HTTP_HEALTHCHECK_TIMEOUT)
            status_code = resp.status_code
            if resp.status_code < 400:
                alive = True
                break
            ultimo_erro = f"App respondeu HTTP {resp.status_code} em {healthcheck_url}."
            break
        except requests.RequestException as e:
            ultimo_erro = f"App não respondeu ({e})."
            if tentativa < hd._HEALTHCHECK_RETRIES:
                time.sleep(hd._HEALTHCHECK_RETRY_INTERVAL)

    if not alive:
        return StageResult(
            stage=StageName.INICIALIZACAO_APLICACAO,
            status=StageStatus.FALHA,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Aplicação não inicializou corretamente. {ultimo_erro}",
            evidence={"healthcheck_url": healthcheck_url, "ultimo_erro": ultimo_erro},
            error_code="APP_NAO_INICIALIZOU",
        )

    ctx.app_ok = True
    ctx.main_route = hd._discover_main_route(ctx.base_url, requests)
    return StageResult(
        stage=StageName.INICIALIZACAO_APLICACAO,
        status=StageStatus.SUCESSO,
        duration_seconds=round(time.time() - t0, 3),
        summary=f"Aplicação respondendo em {healthcheck_url} (HTTP {status_code}).",
        evidence={"healthcheck_url": healthcheck_url, "main_route": ctx.main_route},
        error_code=None,
    )


# ===========================================================================
# Estágio 5 — Coleta dos logs de execução (runtime)
# ===========================================================================

def _estagio_coleta_logs_execucao(ctx: _HarnessContext) -> StageResult:
    if not ctx.deploy_ok:
        return _pulado(
            StageName.COLETA_LOGS_EXECUCAO,
            "Abortado: nenhum container em execução para coletar logs.",
        )
    t0 = time.time()
    # Em modo 'command' os logs já foram capturados na implantação (o container
    # terminou); ainda assim tentamos reler do container (exited → .logs() ok).
    # Se não há container (defensivo), preservamos o que já foi coletado.
    if ctx.container is not None:
        try:
            ctx.runtime_logs = ctx.container.logs(
                timestamps=True
            ).decode("utf-8", errors="replace")
        except Exception as e:
            ctx.runtime_logs = ctx.runtime_logs or ""
            logger.warning(f"[HARNESS] Falha ao coletar logs de runtime: {e}")

    parsed = parse_log_text(ctx.runtime_logs)
    erros = [e for e in parsed if e.get("level") in ("ERROR", "CRITICAL", "FATAL")]
    return StageResult(
        stage=StageName.COLETA_LOGS_EXECUCAO,
        status=StageStatus.SUCESSO,
        duration_seconds=round(time.time() - t0, 3),
        summary=f"Logs de runtime coletados: {len(parsed)} linhas, {len(erros)} de erro.",
        evidence={
            "linhas_parseadas": len(parsed),
            "erros": erros[:10],
            "runtime_logs_tail": ctx.runtime_logs[-3000:],
        },
        error_code=None,
    )


# ===========================================================================
# Estágio 6 — Execução dos testes automatizados
# ===========================================================================

def _localizar_suite(coder_dir: Path) -> Optional[Path]:
    """Localiza um arquivo de suíte de testes no workspace do coder."""
    candidatos = sorted(
        p for p in coder_dir.rglob("test_*.py") if "__pycache__" not in p.parts
    )
    candidatos += sorted(
        p for p in coder_dir.rglob("*_test.py") if "__pycache__" not in p.parts
    )
    return candidatos[0] if candidatos else None


# --- Execução da suíte DENTRO do container implantado ---------------------
#
# A versão anterior delegava ao `executar_pytest_tool` do QA, que enclausurava
# o path da suíte no workspace do qa_agent (rebase → ERR_MODULO_NAO_ENCONTRADO)
# e acoplava o harness ao estado global daquela tool. Agora o harness roda o
# pytest ele mesmo, contra o artefato realmente implantado em /app (ver
# Dockerfile: WORKDIR /app + COPY . /app/). Continua apenas coletando
# evidência — nenhum veredito, nenhum contador global, nenhum doubt artifact.

_TESTS_TIMEOUT = 60  # segundos — teto para a execução da suíte no container
_APP_WORKDIR = "/app"
_REPORT_JSON_IN = f"{_APP_WORKDIR}/.harness_pytest_report.json"
_COV_JSON_IN = f"{_APP_WORKDIR}/.harness_cov.json"

# Container efêmero para a suíte em modo 'command' (o container do artefato já
# terminou; a suíte roda numa nova instância da mesma imagem).
_TEST_CONTAINER_NAME = f"{hd._CONTAINER_NAME}-tests"

_PLAIN_PASSOU_RE = re.compile(r"(\d+) passed")
_PLAIN_FALHOU_RE = re.compile(r"(\d+) failed")
_PLAIN_ERRO_RE = re.compile(r"(\d+) error")


def _exec_no_container(container, comando: str) -> tuple[Optional[int], str, str]:
    """Executa um comando shell dentro do container; retorna (exit_code, stdout, stderr).

    Usa `/bin/sh -c` para habilitar `timeout`, redirecionamento e encadeamento.
    Não trata exceções: quem chama decide como reportá-las (o estágio as
    converte num StageResult de ERRO).
    """
    res = container.exec_run(
        ["/bin/sh", "-c", comando], workdir=_APP_WORKDIR, demux=True
    )
    saida = res.output if isinstance(res.output, tuple) else (res.output, None)
    stdout = (saida[0] or b"").decode("utf-8", errors="replace")
    stderr = (saida[1] or b"").decode("utf-8", errors="replace")
    return res.exit_code, stdout, stderr


def _pytest_disponivel(container) -> bool:
    """Garante `pytest` executável no container; tenta instalar se ausente.

    A instalação em runtime depende de rede no container. Se falhar, retorna
    False e o estágio degrada de forma honesta (PULADO/PYTEST_INDISPONIVEL) —
    NÃO cai para o host, para não reintroduzir a divergência host↔container.
    """
    code, _, _ = _exec_no_container(container, "python -m pytest --version")
    if code == 0:
        return True
    _exec_no_container(
        container, "pip install --no-cache-dir pytest pytest-json-report pytest-cov"
    )
    code, _, _ = _exec_no_container(container, "python -m pytest --version")
    return code == 0


def _rodar_pytest_no_container(
    container, alvo: str
) -> tuple[Optional[int], str, str, str]:
    """Roda a suíte no container. Tenta o modo 'json' (com plugins de report/cov);
    se as opções não forem reconhecidas (pytest exit 4 = erro de uso, plugins
    ausentes), cai para o modo 'plain' (só stdout).

    Retorna (exit_code, stdout, stderr, modo).
    """
    alvo_q = shlex.quote(alvo)
    cmd_json = (
        f"timeout {_TESTS_TIMEOUT} python -m pytest {alvo_q} "
        f"--json-report --json-report-file={_REPORT_JSON_IN} "
        f"--cov={_APP_WORKDIR} --cov-report=json:{_COV_JSON_IN} "
        f"-q -p no:cacheprovider"
    )
    code, out, err = _exec_no_container(container, cmd_json)
    if code == 4:  # opção desconhecida → plugins ausentes → fallback texto
        cmd_plain = (
            f"timeout {_TESTS_TIMEOUT} python -m pytest {alvo_q} -q -p no:cacheprovider"
        )
        code, out, err = _exec_no_container(container, cmd_plain)
        return code, out, err, "plain"
    return code, out, err, "json"


def _parse_report_json(container) -> dict:
    """Lê e resume o report.json do pytest-json-report de dentro do container."""
    _, raw, _ = _exec_no_container(container, f"cat {_REPORT_JSON_IN}")
    data = json.loads(raw)
    summary = data.get("summary", {}) or {}
    testes = data.get("tests", []) or []
    falhas = [
        {
            "nodeid": t.get("nodeid"),
            "outcome": t.get("outcome"),
            "linha": (t.get("call", {}) or {}).get("crash", {}).get("lineno"),
            "mensagem": (t.get("call", {}) or {}).get("crash", {}).get("message"),
        }
        for t in testes
        if t.get("outcome") not in ("passed", "skipped")
    ]
    return {
        "passaram": summary.get("passed", 0),
        "falharam": summary.get("failed", 0),
        "erros": summary.get("error", 0),
        "pulados": summary.get("skipped", 0),
        "total": summary.get("total", summary.get("collected", 0)),
        "falhas": falhas[:20],
    }


def _parse_cobertura_json(container) -> dict:
    """Lê o coverage.json de dentro do container (best-effort)."""
    try:
        _, raw, _ = _exec_no_container(container, f"cat {_COV_JSON_IN}")
        totals = json.loads(raw).get("totals", {}) or {}
        return {
            "percentual": round(totals.get("percent_covered", 0.0), 2),
            "linhas_cobertas": totals.get("covered_lines", 0),
            "linhas_totais": totals.get("num_statements", 0),
        }
    except Exception:
        return {"percentual": 0.0, "linhas_cobertas": 0, "linhas_totais": 0}


def _parse_stdout_plain(stdout: str) -> dict:
    """Resumo mínimo a partir do stdout do pytest quando não há JSON report."""

    def _n(rx: re.Pattern) -> int:
        m = rx.search(stdout)
        return int(m.group(1)) if m else 0

    passaram, falharam, erros = (
        _n(_PLAIN_PASSOU_RE),
        _n(_PLAIN_FALHOU_RE),
        _n(_PLAIN_ERRO_RE),
    )
    return {
        "passaram": passaram,
        "falharam": falharam,
        "erros": erros,
        "pulados": 0,
        "total": passaram + falharam + erros,
        "falhas": [],
    }


def _estagio_testes(ctx: _HarnessContext) -> StageResult:
    """Estágio 6 — dispatcher da suíte de testes por modo de entrega.

    'service': o container do artefato continua no ar; a suíte roda DENTRO dele
        (exec_run), contra o código realmente implantado em /app.
    'command': o container do artefato já terminou; a suíte declarada em
        test.cmd roda num container efêmero recém-criado a partir da mesma imagem.

    O pré-requisito (app inicializada) é comum aos dois modos e checado aqui.
    """
    if not ctx.app_ok:
        return _pulado(
            StageName.TESTES_AUTOMATIZADOS,
            "Abortado: aplicação não inicializou; testes não executados.",
        )
    if ctx.delivery_mode == _MODE_COMMAND:
        return _estagio_testes_command(ctx)
    return _estagio_testes_service(ctx)


def _estagio_testes_command(ctx: _HarnessContext) -> StageResult:
    """Testes em modo 'command': roda test.cmd num container efêmero.

    Sem test.cmd declarado no manifesto não há suíte a executar (PULADO) — o
    harness não tenta adivinhar um runner por linguagem. Quando há, roda o
    comando declarado numa nova instância da imagem, coleta exit code + saída e
    classifica tecnicamente (0 = passou; ≠0 = falhou). O veredito continua sendo
    do validador; aqui só há evidência.
    """
    t0 = time.time()
    if not ctx.test_cmd:
        return StageResult(
            stage=StageName.TESTES_AUTOMATIZADOS,
            status=StageStatus.PULADO,
            duration_seconds=round(time.time() - t0, 3),
            summary="Modo 'command' sem test.cmd declarado; testes não executados.",
            evidence={"delivery_mode": ctx.delivery_mode},
            error_code=None,
        )

    exit_code, logs, _container, erro = _rodar_container_ate_fim(
        ctx, ctx.test_cmd, _TEST_CONTAINER_NAME, _TESTS_TIMEOUT
    )
    if erro is not None:
        summary, error_code = erro
        # Timeout é falha da suíte; falha ao subir o container é erro de execução.
        if error_code == "COMANDO_TIMEOUT":
            status, error_code = StageStatus.FALHA, "TESTES_TIMEOUT"
        else:
            status = StageStatus.ERRO
        return StageResult(
            stage=StageName.TESTES_AUTOMATIZADOS,
            status=status,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Testes (command): {summary}",
            evidence={"test_cmd": ctx.test_cmd, "saida_tail": (logs or "")[-3000:]},
            error_code=error_code,
        )

    status = StageStatus.SUCESSO if exit_code == 0 else StageStatus.FALHA
    error_code = None if exit_code == 0 else "TESTES_FALHARAM"
    return StageResult(
        stage=StageName.TESTES_AUTOMATIZADOS,
        status=status,
        duration_seconds=round(time.time() - t0, 3),
        summary=(
            f"Suíte de testes (test.cmd) executada em container efêmero "
            f"(exit={exit_code})."
        ),
        evidence={
            "test_cmd": ctx.test_cmd,
            "exit_code": exit_code,
            "saida_tail": (logs or "")[-3000:],
        },
        error_code=error_code,
    )


def _estagio_testes_service(ctx: _HarnessContext) -> StageResult:
    """Estágio 6 (service) — executa a suíte de testes DENTRO do container vivo.

    Localiza a suíte no workspace do coder (host), traduz o caminho para o
    interior do container (`/app/...`) e roda o pytest lá dentro. Apenas coleta
    evidência: a decisão sobre o que as falhas significam é do validador.
    """
    t0 = time.time()

    suite = _localizar_suite(ctx.coder_dir)
    if suite is None:
        return StageResult(
            stage=StageName.TESTES_AUTOMATIZADOS,
            status=StageStatus.PULADO,
            duration_seconds=round(time.time() - t0, 3),
            summary="Nenhuma suíte de testes encontrada no workspace do coder.",
            evidence={"suite": None},
            error_code=None,
        )

    # Path host → path no container (Dockerfile: WORKDIR /app + COPY . /app/).
    rel = suite.relative_to(ctx.coder_dir)
    alvo = f"{_APP_WORKDIR}/{rel.as_posix()}"

    try:
        if not _pytest_disponivel(ctx.container):
            return StageResult(
                stage=StageName.TESTES_AUTOMATIZADOS,
                status=StageStatus.PULADO,
                duration_seconds=round(time.time() - t0, 3),
                summary=(
                    "pytest indisponível no container e não foi possível "
                    "instalá-lo (sem rede?). Testes não executados."
                ),
                evidence={"suite": str(suite), "alvo_container": alvo},
                error_code="PYTEST_INDISPONIVEL",
            )

        exit_code, stdout, stderr, modo = _rodar_pytest_no_container(ctx.container, alvo)
    except Exception as e:
        return StageResult(
            stage=StageName.TESTES_AUTOMATIZADOS,
            status=StageStatus.ERRO,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Falha ao executar pytest no container: {e}",
            evidence={"suite": str(suite), "alvo_container": alvo},
            error_code="EXEC_FALHOU",
        )

    # Resumo estruturado (JSON report quando disponível; stdout como fallback).
    if modo == "json":
        try:
            resumo = _parse_report_json(ctx.container)
        except Exception:
            resumo = _parse_stdout_plain(stdout)
        cobertura = _parse_cobertura_json(ctx.container)
    else:
        resumo = _parse_stdout_plain(stdout)
        cobertura = {"percentual": 0.0, "linhas_cobertas": 0, "linhas_totais": 0}

    # Classificação técnica (SEM veredito) a partir do exit code do pytest:
    #   0 = tudo passou | 1 = houve falhas | 5 = nada coletado
    #   124 = timeout (coreutils) | 2/3/4 = interrompido/erro interno/uso incorreto
    if exit_code == 5:
        return StageResult(
            stage=StageName.TESTES_AUTOMATIZADOS,
            status=StageStatus.PULADO,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Suíte '{suite.name}' não coletou nenhum teste.",
            evidence={"suite": str(suite), "alvo_container": alvo, "modo": modo},
            error_code=None,
        )
    if exit_code == 0:
        status, error_code = StageStatus.SUCESSO, None
    elif exit_code == 124:
        status, error_code = StageStatus.FALHA, "TESTES_TIMEOUT"
    elif exit_code == 1:
        status, error_code = StageStatus.FALHA, "TESTES_FALHARAM"
    else:
        status, error_code = StageStatus.ERRO, "PYTEST_ERRO_EXECUCAO"

    tail = (stdout or "")[-3000:]
    if stderr:
        tail += f"\n--- stderr ---\n{stderr[-1000:]}"

    return StageResult(
        stage=StageName.TESTES_AUTOMATIZADOS,
        status=status,
        duration_seconds=round(time.time() - t0, 3),
        summary=(
            f"Suíte '{suite.name}' executada no container "
            f"(modo={modo}, exit={exit_code}): {resumo['passaram']} passaram, "
            f"{resumo['falharam']} falharam, {resumo['erros']} erros."
        ),
        evidence={
            "suite": str(suite),
            "alvo_container": alvo,
            "modo": modo,
            "exit_code": exit_code,
            "resumo": resumo,
            "cobertura": cobertura,
            "saida_tail": tail,
        },
        error_code=error_code,
    )


# ===========================================================================
# Estágio 7 — Execução das validações do Work Item (só coleta evidência)
# ===========================================================================

_PATH_RE = re.compile(r"(/[\w\-/{}]*)")
_VERBO_HTTP_RE = re.compile(r"\b(GET|POST|PUT|DELETE|PATCH)\b", re.IGNORECASE)


def _coletar_evidencia_criterio(
    criterion: str, base_url: str, main_route: Optional[str]
) -> CriterionEvidence:
    """Deriva uma checagem determinística para um critério, SEM julgá-lo.

    Nunca decide se o critério foi atendido — apenas registra o que foi
    verificado e o que foi observado. A conclusão é do validador.

    A única checagem que o harness sabe derivar com segurança é um GET sem
    payload. Critérios que mencionam POST/PUT/PATCH/DELETE exigiriam inventar
    corpo/headers — adivinhação que o harness não faz. Nesses casos o critério
    é marcado como NÃO verificável (evidência honesta), em vez de executar um
    GET desalinhado e rotulá-lo de verificável, o que poderia induzir o
    validador a conclusões erradas (ex.: um 405 em rota POST é o comportamento
    esperado para um GET, não uma falha do critério).
    """
    path_match = _PATH_RE.search(criterion)
    verbos = {m.upper() for m in _VERBO_HTTP_RE.findall(criterion)}
    verbos_nao_checaveis = verbos - {"GET"}

    # Verbo com payload/efeito colateral → sem checagem determinística derivável.
    if verbos_nao_checaveis:
        listado = ", ".join(sorted(verbos_nao_checaveis))
        return CriterionEvidence(
            criterion=criterion,
            check_performed=(
                f"Nenhuma checagem determinística derivável: critério requer "
                f"{listado} (payload/efeito colateral não inferível pelo harness)."
            ),
            observed="Requer avaliação do validador a partir das evidências coletadas.",
            checkable=False,
        )

    if path_match or verbos:
        rota = path_match.group(1) if path_match else (main_route or "/")
        if not rota or rota == "/":
            rota = main_route or "/"
        try:
            resp = requests.get(f"{base_url}{rota}", timeout=hd._HTTP_HEALTHCHECK_TIMEOUT)
            observed = f"GET {rota} → HTTP {resp.status_code}"
        except Exception as e:
            observed = f"GET {rota} → falha de conexão: {e}"
        return CriterionEvidence(
            criterion=criterion,
            check_performed=f"Requisição HTTP GET {rota}",
            observed=observed,
            checkable=True,
        )

    # Critério semântico demais para checagem determinística
    return CriterionEvidence(
        criterion=criterion,
        check_performed="Nenhuma checagem determinística derivável (critério semântico).",
        observed="Requer avaliação do validador a partir das evidências coletadas.",
        checkable=False,
    )


def _evidencia_criterio_command(
    criterion: str, exit_code: Optional[int]
) -> CriterionEvidence:
    """Evidência de um critério em modo 'command' (sem servidor a sondar).

    O harness não sobe um serviço HTTP neste modo, então não há checagem
    determinística derivável por rota/verbo. A evidência aponta o exit code
    observado e os logs de runtime já coletados; o julgamento de cada critério
    cabe ao validador. Marcado como NÃO verificável — honesto por construção.
    """
    return CriterionEvidence(
        criterion=criterion,
        check_performed=(
            "Nenhuma checagem HTTP aplicável (modo 'command'): validação do "
            "critério cabe ao validador a partir do exit code e dos logs."
        ),
        observed=(
            f"Execução em modo 'command' finalizou com exit={exit_code}; "
            "saída disponível nos logs de runtime."
        ),
        checkable=False,
    )


def _estagio_validacoes_work_item(
    ctx: _HarnessContext,
) -> tuple[StageResult, list[CriterionEvidence]]:
    if not ctx.app_ok:
        return (
            _pulado(
                StageName.VALIDACOES_WORK_ITEM,
                "Abortado: aplicação não inicializou; evidências não coletadas.",
            ),
            [],
        )
    t0 = time.time()
    if ctx.delivery_mode == _MODE_COMMAND:
        evidencias = [
            _evidencia_criterio_command(c, ctx.command_exit_code)
            for c in ctx.acceptance_criteria
        ]
    else:
        evidencias = [
            _coletar_evidencia_criterio(c, ctx.base_url, ctx.main_route)
            for c in ctx.acceptance_criteria
        ]
    checaveis = sum(1 for e in evidencias if e.checkable)
    result = StageResult(
        stage=StageName.VALIDACOES_WORK_ITEM,
        status=StageStatus.SUCESSO,
        duration_seconds=round(time.time() - t0, 3),
        summary=(
            f"Evidência coletada para {len(evidencias)} critérios "
            f"({checaveis} verificáveis automaticamente). Nenhum julgamento emitido."
        ),
        evidence={"total_criterios": len(evidencias), "verificaveis": checaveis},
        error_code=None,
    )
    return result, evidencias


# ===========================================================================
# Estágios 8 e 9 — Consolidação e geração do relatório
# ===========================================================================

def _agregar_status(stages: list[StageResult]) -> StageStatus:
    """Deriva o status técnico agregado (não é veredito de aprovação)."""
    por_estagio = {s.stage.value: s.status for s in stages}
    if any(s.status == StageStatus.ERRO for s in stages):
        return StageStatus.ERRO
    for critico in _CRITICAL_STAGES:
        if por_estagio.get(critico) in (StageStatus.FALHA, StageStatus.PULADO):
            return StageStatus.FALHA
    return StageStatus.SUCESSO


def _serializar_json_atomico(path: Path, data: dict) -> None:
    """Escreve o JSON sobrescrevendo atomicamente (arquivo temp + os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _render_markdown(report: ExecutionReport) -> str:
    """Renderiza o ExecutionReport em markdown legível (sem veredito)."""
    linhas = [
        f"# Relatório de Execução — {report.work_item_id}",
        "",
        f"- **Iteração:** {report.iteration}",
        f"- **Gerado em:** {report.generated_at}",
        f"- **Status técnico agregado:** {report.overall_status.value}",
        f"- **Duração total:** {report.total_duration_seconds}s",
        "",
        "## Estágios",
        "",
        "| # | Estágio | Status | Duração (s) | Resumo |",
        "| - | ------- | ------ | ----------- | ------ |",
    ]
    for i, s in enumerate(report.stages, start=1):
        resumo = s.summary.replace("|", "\\|")
        linhas.append(
            f"| {i} | {s.stage.value} | {s.status.value} | {s.duration_seconds} | {resumo} |"
        )
    linhas += ["", "## Evidências por critério de aceite", ""]
    if report.criteria_evidence:
        linhas += [
            "| Critério | Verificação | Observado | Verificável |",
            "| -------- | ----------- | --------- | ----------- |",
        ]
        for e in report.criteria_evidence:
            linhas.append(
                f"| {e.criterion} | {e.check_performed} | {e.observed} | {e.checkable} |"
            )
    else:
        linhas.append("_Nenhuma evidência coletada (estágio de validação não executado)._")
    return "\n".join(linhas) + "\n"


# ===========================================================================
# Tool pública — orquestra os 9 estágios
# ===========================================================================

def executar_harness_validacao(
    task_id: str,
    iteration: int = 1,
    *,
    coder_base_dir=None,
    execution_base_dir=None,
    tasks_base_dir=None,
    tool_context: ToolContext | None = None,
) -> dict:
    """Executa o harness de validação (9 estágios) sobre o artefato do coder.

    A orquestração é determinística: a ordem e as decisões de aborto NÃO
    dependem de nenhum LLM. Cada estágio produz um `StageResult`; estágios
    críticos (preparação, implantação, inicialização) abortam os estágios que
    deles dependem quando falham. O harness apenas coleta evidências — nunca
    decide se um critério de aceite foi atendido (isso cabe ao validador).

    Args:
        task_id: Identificador da Task/Work Item a validar.
        iteration: Iteração do loop de execução (para rastreio entre tentativas).
        coder_base_dir: Sobrescreve o diretório do código do coder (injeção em testes).
        execution_base_dir: Sobrescreve o diretório de saída da execução.
        tasks_base_dir: Sobrescreve o diretório onde ficam as Tasks em JSON.
        tool_context: Injetado pela FunctionTool do ADK quando o parâmetro é
            declarado. Opcional — chamadas diretas (testes, PoC) não o passam.
            Quando presente, grava o caminho absoluto do report gravado em
            `tool_context.state["report_path"]`, tornando a evidência resolvível
            pelo validador sem depender do eco do LLM.

    Returns:
        dict: `ExecutionReport.model_dump(mode="json")` — apenas evidências,
        sem nenhum veredito.
    """
    t_inicio = time.time()

    coder_dir = Path(coder_base_dir) if coder_base_dir else get_agent_workspace("cr_coder")
    exec_dir = Path(execution_base_dir) if execution_base_dir else get_agent_workspace("cr_executor")
    tasks_dir = Path(tasks_base_dir) if tasks_base_dir else get_agent_workspace("cr_context_engineer")

    ctx = _HarnessContext(task_id, coder_dir, exec_dir, tasks_dir)

    stages: list[StageResult] = []
    criteria_evidence: list[CriterionEvidence] = []

    # ---- Estágios 1..5 ----
    stages.append(_estagio_preparacao(ctx))
    stages.append(_estagio_implantacao(ctx) if ctx.env_ok
                  else _pulado(StageName.IMPLANTACAO_ARTEFATO,
                               "Abortado: preparação do ambiente falhou."))
    stages.append(_estagio_coleta_logs_implantacao(ctx))
    stages.append(_estagio_inicializacao(ctx))
    stages.append(_estagio_coleta_logs_execucao(ctx))

    # ---- Estágio 6 ----
    stages.append(_estagio_testes(ctx))

    # ---- Estágio 7 ----
    r7, criteria_evidence = _estagio_validacoes_work_item(ctx)
    stages.append(r7)

    # ---- Estágio 8 — Consolidação ----
    t8 = time.time()
    overall = _agregar_status(stages)
    stages.append(StageResult(
        stage=StageName.CONSOLIDACAO_EVIDENCIAS,
        status=StageStatus.SUCESSO,
        duration_seconds=round(time.time() - t8, 3),
        summary=f"Evidências consolidadas de {len(stages)} estágios anteriores.",
        evidence={"overall_status": overall.value},
        error_code=None,
    ))

    # ---- Estágio 9 — Geração do relatório ----
    t9 = time.time()
    report_json_path = exec_dir / f"{task_id}.report.json"
    report_md_path = exec_dir / f"{task_id}.report.md"
    stages.append(StageResult(
        stage=StageName.GERACAO_RELATORIO,
        status=StageStatus.SUCESSO,
        duration_seconds=round(time.time() - t9, 3),
        summary=f"Relatório serializado em {report_json_path.name} e {report_md_path.name}.",
        evidence={"report_json": str(report_json_path), "report_md": str(report_md_path)},
        error_code=None,
    ))

    report = ExecutionReport(
        work_item_id=task_id,
        iteration=iteration,
        generated_at=_now_iso(),
        acceptance_criteria=ctx.acceptance_criteria,
        overall_status=overall,
        stages=stages,
        criteria_evidence=criteria_evidence,
        report_path=str(report_json_path),
        total_duration_seconds=round(time.time() - t_inicio, 3),
    )

    payload = report.model_dump(mode="json")
    _serializar_json_atomico(report_json_path, payload)
    report_md_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.write_text(_render_markdown(report), encoding="utf-8")

    # Grava o caminho do report no session state (fonte determinística para o
    # validador). Só quando há contexto — chamadas diretas (testes/PoC) o omitem.
    if tool_context is not None:
        tool_context.state["report_path"] = str(report_json_path.resolve())
        tool_context.state["task_id"] = task_id

    return payload


def executar_harness_tool(
    task_id: str,
    iteration: int = 1,
    tool_context: ToolContext | None = None,
) -> dict:
    """Entrypoint do harness exposto ao LLM (via FunctionTool).

    Os diretórios de trabalho são SEMPRE os do workspace do fluxo — o LLM
    não os controla. A função `executar_harness_validacao` mantém os
    parâmetros `*_base_dir` para injeção em testes/PoC, fora do schema da tool.
    """
    return executar_harness_validacao(
        task_id, iteration, tool_context=tool_context,
    )


# ---------------------------------------------------------------------------
# Import tardio dos schemas (quebra de ciclo de import)
# ---------------------------------------------------------------------------
# Os schemas vivem em `src.agents.executor.schemas`, mas o pacote
# `src.agents.executor` agora importa o agente executor no seu __init__, e esse
# agente importa ESTE módulo (via `executar_harness_validacao`). Importar os
# schemas no topo dispararia o __init__ do pacote antes desta função existir,
# criando um ciclo. Fazendo o import no fim do arquivo — depois que todas as
# funções já foram definidas — o ciclo se resolve em qualquer ordem de import:
# quando o __init__ do executor voltar aqui, `executar_harness_validacao` já
# estará definida. As classes ficam como globais do módulo, resolvidas em tempo
# de chamada pelas funções acima.
from src.agents.executor.schemas import (  # noqa: E402
    CriterionEvidence,
    ExecutionReport,
    StageName,
    StageResult,
    StageStatus,
)