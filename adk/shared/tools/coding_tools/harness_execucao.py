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
- `shared/tools/probe.py` — cliente HTTP injetado no container (liveness/rotas).
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import docker
from docker.errors import APIError, BuildError
from google.adk.tools import ToolContext

from shared.tools import probe
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
        self.tech_stack: list[str] = []
        self.acceptance_criteria: list[str] = []
        self.contract: dict = {}
        self.dockerfile: str = ""
        self.dockerfile_resolvido: Optional[str] = None  # entregue pelo chamador
        self.dockerfile_origem_resolvida: Optional[str] = None
        self.comando_teste_resolvido: Optional[str] = None  # entregue pelo chamador
        self.comando_teste_origem_resolvida: Optional[str] = None
        self.build_dir: Optional[Path] = None
        self.docker_client = None
        self.container = None
        self.build_logs: str = ""
        self.runtime_logs: str = ""

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

    # Resolve Dockerfile. Quando o chamador (ExecutorOrchestrator) já resolveu —
    # priorizando o do coder, senão via LLM — usa direto (o harness NÃO recheca o
    # workspace do coder nesse caso). Em chamada direta (teste/PoC), sem chamador
    # externo, olha o coder ele mesmo; sem Dockerfile nenhum, falha honesta — o
    # harness não gera fallback embutido.
    if ctx.dockerfile_resolvido is not None:
        ctx.dockerfile = ctx.dockerfile_resolvido
        origem_dockerfile = ctx.dockerfile_origem_resolvida or "externo"
    else:
        dockerfile_path = ctx.coder_dir / "Dockerfile"
        if dockerfile_path.is_file():
            ctx.dockerfile = dockerfile_path.read_text(encoding="utf-8")
            origem_dockerfile = "coder"
        else:
            return StageResult(
                stage=StageName.PREPARACAO_AMBIENTE,
                status=StageStatus.ERRO,
                duration_seconds=round(time.time() - t0, 3),
                summary=(
                    "Nenhum Dockerfile: não fornecido pelo chamador e ausente no "
                    "workspace do coder."
                ),
                evidence={"coder_dir": str(ctx.coder_dir)},
                error_code="DOCKERFILE_AUSENTE",
            )

    ctx.env_ok = True
    return StageResult(
        stage=StageName.PREPARACAO_AMBIENTE,
        status=StageStatus.SUCESSO,
        duration_seconds=round(time.time() - t0, 3),
        summary=(
            f"Ambiente preparado: Task carregada ({len(ctx.acceptance_criteria)} "
            f"critérios), Dockerfile de origem '{origem_dockerfile}'."
        ),
        evidence={
            "task_file": str(task_file),
            "acceptance_criteria": ctx.acceptance_criteria,
            "dockerfile_origem": origem_dockerfile,
        },
        error_code=None,
    )


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
            evidence={
                "build_logs_tail": ctx.build_logs[-2000:],
                "dockerfile_usado": ctx.dockerfile,
            },
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
    try:
        container = client.containers.run(
            image=hd._IMAGE_TAG,
            name=hd._CONTAINER_NAME,
            detach=True,
            mem_limit=hd._MEMORY_LIMIT,
            cpu_quota=hd._CPU_QUOTA,
            environment={
                "DATABASE_URL": "sqlite:///./data/app.db",
                "UPLOAD_DIR": "/app/uploads",
            },
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

_EXPOSE_RE = re.compile(r"^\s*EXPOSE\s+(\d+)", re.IGNORECASE | re.MULTILINE)


def _porta_interna(dockerfile: str) -> int:
    """Porta que a app escuta DENTRO do container, lida do EXPOSE do Dockerfile.

    O probe roda de dentro do container, então a porta relevante é a interna
    (declarada via EXPOSE), não a publicada no host. Fallback para
    `hd._HOST_PORT` APENAS quando o Dockerfile não declara EXPOSE nenhum —
    preserva o comportamento de hoje sem fixar de novo a suposição de 8000. Em
    múltiplos EXPOSE, usa o primeiro (a porta HTTP primária, por convenção).
    """
    m = _EXPOSE_RE.search(dockerfile or "")
    return int(m.group(1)) if m else hd._HOST_PORT


def _estagio_inicializacao(ctx: _HarnessContext) -> StageResult:
    if not ctx.deploy_ok:
        return _pulado(
            StageName.INICIALIZACAO_APLICACAO,
            "Abortado: implantação do artefato não foi bem-sucedida.",
        )
    t0 = time.time()

    # Grace period para a app subir dentro do container
    time.sleep(hd._STARTUP_GRACE_PERIOD)

    # Liveness DE DENTRO do container, via probe: a porta que importa é a interna
    # (EXPOSE), não a publicada no host. "Vivo" = qualquer resposta HTTP (erro de
    # transporte nulo), inclusive 4xx/5xx — a porta respondeu, a app subiu. Não
    # depende mais de /docs (hd._HEALTHCHECK_ENDPOINT) existir.
    porta = _porta_interna(ctx.dockerfile)
    base_interno = f"http://localhost:{porta}"
    requisicao = [{
        "method": "GET",
        "path": "/",
        "timeout_ms": hd._HTTP_HEALTHCHECK_TIMEOUT * 1000,
    }]

    alive = False
    ultimo_erro = ""
    status_code = None
    for tentativa in range(1, hd._HEALTHCHECK_RETRIES + 1):
        try:
            resultados = probe.executar_probe(ctx.container, requisicao, base_interno)
        except probe.ProbeError as e:
            # Falha MECÂNICA do probe (binário ausente, arquitetura não suportada,
            # put_archive recusado) — categoria DIFERENTE de "a app não subiu".
            # Re-tentar não resolve; encerra já, com error_code próprio para a
            # distinção ficar visível.
            return StageResult(
                stage=StageName.INICIALIZACAO_APLICACAO,
                status=StageStatus.ERRO,
                duration_seconds=round(time.time() - t0, 3),
                summary=f"Falha ao checar liveness via probe: {e}",
                evidence={"base_url_interno": base_interno, "erro_probe": str(e)},
                error_code="PROBE_FALHOU",
            )

        resultado = resultados[0] if resultados else {}
        status_code = resultado.get("status")
        if resultado.get("error") is None:
            alive = True
            break
        ultimo_erro = f"App não respondeu em {base_interno}/ ({resultado.get('error')})."
        if tentativa < hd._HEALTHCHECK_RETRIES:
            time.sleep(hd._HEALTHCHECK_RETRY_INTERVAL)

    if not alive:
        return StageResult(
            stage=StageName.INICIALIZACAO_APLICACAO,
            status=StageStatus.FALHA,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Aplicação não inicializou corretamente. {ultimo_erro}",
            evidence={"base_url_interno": base_interno, "ultimo_erro": ultimo_erro},
            error_code="APP_NAO_INICIALIZOU",
        )

    ctx.app_ok = True
    return StageResult(
        stage=StageName.INICIALIZACAO_APLICACAO,
        status=StageStatus.SUCESSO,
        duration_seconds=round(time.time() - t0, 3),
        summary=f"Aplicação respondendo em {base_interno}/ (HTTP {status_code}).",
        evidence={"base_url_interno": base_interno},
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
    try:
        ctx.runtime_logs = ctx.container.logs(timestamps=True).decode("utf-8", errors="replace")
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

# O comando que roda a suíte é resolvido pela LLM (test_command_resolver) e
# entregue ao harness já pronto — o harness só o executa contra o artefato
# implantado em /app e classifica pelo exit code. `_exec_no_container` é
# genérico: não conhece test runner nem stack nenhuma.

# Workdir do artefato no container (Dockerfile: WORKDIR /app + COPY . /app/).
_APP_WORKDIR = "/app"

# Teto para o comando de teste no container (segundos).
_TESTES_TIMEOUT = 120


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


def _estagio_testes(ctx: _HarnessContext) -> StageResult:
    """Estágio 6 — executa o comando de teste DENTRO do container implantado.

    O comando é resolvido FORA do harness (LLM, via ExecutorOrchestrator) e
    entregue em `ctx.comando_teste_resolvido`. O harness só o roda contra o
    artefato em /app e classifica pelo exit code — sem conhecer o test runner.
    Apenas coleta evidência: o que as falhas significam é do validador.
    """
    if not ctx.app_ok:
        return _pulado(
            StageName.TESTES_AUTOMATIZADOS,
            "Abortado: aplicação não inicializou; testes não executados.",
        )
    comando = ctx.comando_teste_resolvido
    if not comando:
        # None/"" cobre "ninguém passou comando" e "resolução falhou/recusada
        # pelo filtro" — evidência honesta, sem error_code (não é falha do harness).
        return _pulado(
            StageName.TESTES_AUTOMATIZADOS,
            "Nenhum comando de teste resolvido; testes não executados.",
        )
    t0 = time.time()

    try:
        exit_code, stdout, stderr = _exec_no_container(
            ctx.container, f"timeout {_TESTES_TIMEOUT} {comando}"
        )
    except Exception as e:
        return StageResult(
            stage=StageName.TESTES_AUTOMATIZADOS,
            status=StageStatus.ERRO,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Falha ao executar o comando de teste no container: {e}",
            evidence={
                "comando": comando,
                "comando_origem": ctx.comando_teste_origem_resolvida,
            },
            error_code="EXEC_FALHOU",
        )

    # Classificação pelo exit code (sem parsing de contagem):
    #   0 = passou | 124 = timeout (coreutils) | 126/127 = comando não encontrado
    #   / não executável (sinal de retry) | qualquer outro != 0 = testes falharam.
    if exit_code == 0:
        status, error_code = StageStatus.SUCESSO, None
    elif exit_code == 124:
        status, error_code = StageStatus.FALHA, "TESTES_TIMEOUT"
    elif exit_code in (126, 127):
        status, error_code = StageStatus.FALHA, "COMANDO_NAO_ENCONTRADO"
    else:
        status, error_code = StageStatus.FALHA, "TESTES_FALHARAM"

    tail = (stdout or "")[-3000:]
    if stderr:
        tail += f"\n--- stderr ---\n{stderr[-1000:]}"

    return StageResult(
        stage=StageName.TESTES_AUTOMATIZADOS,
        status=status,
        duration_seconds=round(time.time() - t0, 3),
        summary=f"Comando de teste executado no container (exit={exit_code}): '{comando}'.",
        evidence={
            "comando": comando,
            "comando_origem": ctx.comando_teste_origem_resolvida,
            "exit_code": exit_code,
            "saida_tail": tail,
        },
        error_code=error_code,
    )


# ===========================================================================
# Estágio 7 — Execução das validações do Work Item (só coleta evidência)
# ===========================================================================

_PATH_RE = re.compile(r"(/[\w\-/{}]*)")
_VERBO_HTTP_RE = re.compile(r"\b(GET|POST|PUT|DELETE|PATCH)\b", re.IGNORECASE)
_PARAM_SEG_RE = re.compile(r"\{[^/}]+\}")

# Nomes de campo genéricos aceitos como identificador de um recurso criado/listado
# — conjunto pequeno e SEM semântica de negócio (ver spec C2c §2/§3.3).
_CAMPOS_ID = ("id", "_id", "uuid")

# Timeout das requisições de evidência (ms), no mesmo teto do liveness.
_EVIDENCIA_TIMEOUT_MS = hd._HTTP_HEALTHCHECK_TIMEOUT * 1000


def _probe_uma(container, base_interno: str, metodo: str, rota: str):
    """Dispara UMA requisição via probe (sem body/headers — nunca inventa payload).

    Devolve `(resultado, erro_mecanico)`:
      - `resultado`: o dict do probe (pode ter `error` de transporte preenchido);
      - `erro_mecanico`: str quando `probe.ProbeError` (falha do MECANISMO do
        probe — binário/arquitetura/put_archive), categoria DIFERENTE de um erro
        de transporte de requisição.
    Só uma das duas posições é significativa por chamada.
    """
    try:
        resultados = probe.executar_probe(
            container,
            [{"method": metodo, "path": rota, "timeout_ms": _EVIDENCIA_TIMEOUT_MS}],
            base_interno,
        )
    except probe.ProbeError as e:
        return None, str(e)
    return (resultados[0] if resultados else {}), None


def _coletar_evidencia_criterio(
    criterion: str, container, base_interno: str
) -> CriterionEvidence:
    """Deriva uma checagem determinística para um critério, SEM julgá-lo.

    Nunca decide se o critério foi atendido — apenas registra o que foi verificado
    e o que foi observado. A conclusão é do validador.

    A única checagem que o harness sabe derivar com segurança é um GET sem payload,
    e SÓ quando o critério traz um path explícito. Critérios que mencionam
    POST/PUT/PATCH/DELETE exigiriam inventar corpo/headers (adivinhação que o
    harness não faz); critérios sem path explícito não têm rota a testar — ambos
    viram NÃO verificáveis (evidência honesta), sem chutar a rota raiz.

    A requisição roda DE DENTRO do container, via probe, contra a porta interna
    (mesmo modelo do Estágio 4) — não pela porta publicada (que deixou de existir).
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

    if path_match:
        rota = path_match.group(1)
        resultado, mecanico = _probe_uma(container, base_interno, "GET", rota)
        if mecanico is not None:
            observed = f"GET {rota} → falha do probe: {mecanico}"
        elif resultado.get("error"):
            observed = f"GET {rota} → falha de transporte: {resultado['error']}"
        else:
            observed = f"GET {rota} → HTTP {resultado.get('status')}"
        return CriterionEvidence(
            criterion=criterion,
            check_performed=f"Requisição HTTP GET {rota} (via probe, porta interna).",
            observed=observed,
            checkable=True,
        )

    # Critério sem path explícito (com ou sem verbo) → sem rota a testar.
    return CriterionEvidence(
        criterion=criterion,
        check_performed="Nenhuma checagem determinística derivável (sem rota explícita / semântico demais).",
        observed="Requer avaliação do validador a partir das evidências coletadas.",
        checkable=False,
    )


# --- Evidência por interface declarada (contract.interfaces) — três ramos -----

def _extrair_verbo_rota(texto: str) -> tuple[Optional[str], Optional[str]]:
    """Extrai o primeiro verbo HTTP e a primeira rota — mesma extração dos critérios."""
    verbos = _VERBO_HTTP_RE.findall(texto)
    verbo = verbos[0].upper() if verbos else None
    path_match = _PATH_RE.search(texto)
    rota = path_match.group(1) if path_match else None
    return verbo, rota


def _param_no_ultimo_segmento(rota: str) -> bool:
    segs = [s for s in rota.split("/") if s]
    return bool(segs) and bool(re.fullmatch(r"\{[^/}]+\}", segs[-1]))


def _rota_pai(rota: str) -> str:
    """Rota sem o último segmento — `/items/{id}` → `/items` (`/{id}` → `/`)."""
    segs = [s for s in rota.split("/") if s]
    pai = "/".join(segs[:-1])
    return "/" + pai if pai else "/"


def _substituir_ultimo_param(rota: str, valor: str) -> str:
    """Troca o último segmento `{...}` pelo valor real do ID."""
    segs = rota.split("/")
    for i in range(len(segs) - 1, -1, -1):
        if re.fullmatch(r"\{[^/}]+\}", segs[i]):
            segs[i] = valor
            break
    return "/".join(segs)


def _extrair_id(body: str) -> Optional[str]:
    """Extrai um identificador genérico do corpo JSON, sem semântica de negócio.

    Objeto de topo: procura `id`/`_id`/`uuid` direto. Lista/array: usa o primeiro
    item. None se nada casar (nunca inventa um valor).
    """
    try:
        dado = json.loads(body or "")
    except Exception:
        return None
    return _id_de(dado)


def _id_de(dado) -> Optional[str]:
    if isinstance(dado, dict):
        for campo in _CAMPOS_ID:
            valor = dado.get(campo)
            if isinstance(valor, (str, int)) and not isinstance(valor, bool):
                return str(valor)
        return None
    if isinstance(dado, list) and dado:
        return _id_de(dado[0])
    return None


def _evidencia_interface(
    interface: str, ramo: str, metodo: str, rota: str, resultado, mecanico, prefixo: str = ""
) -> InterfaceEvidence:
    """Monta a InterfaceEvidence a partir do resultado bruto de UMA requisição."""
    if mecanico is not None:
        observed = f"{metodo} {rota} → falha do probe: {mecanico}"
    elif resultado.get("error"):
        observed = f"{metodo} {rota} → falha de transporte: {resultado['error']}"
    else:
        corpo = (resultado.get("body") or "")[:500]
        observed = f"{metodo} {rota} → HTTP {resultado.get('status')}"
        if corpo:
            observed += f"; corpo: {corpo}"
    pref = f"{prefixo} " if prefixo else ""
    return InterfaceEvidence(
        interface=interface,
        checkable=True,
        branch=ramo,
        check_performed=f"{pref}Requisição {metodo} {rota} (via probe, porta interna).".strip(),
        observed=observed,
    )


def _interface_nao_checavel(interface: str, motivo: str) -> InterfaceEvidence:
    return InterfaceEvidence(
        interface=interface,
        checkable=False,
        branch=None,
        check_performed=f"Nenhuma checagem derivável: {motivo}.",
        observed="Requer avaliação do validador a partir das demais evidências do report.",
    )


def _resolver_id_grupo(
    container, base_interno: str, rota_pai: str, verbos: list, rotas: list
) -> tuple[Optional[str], Optional[str], str]:
    """Resolve UM id real da rota pai — Ramo 1 (POST/criar) ou Ramo 2 (GET/listar).

    Nunca inventa valor. Devolve `(id, ramo, motivo)`: id/ramo preenchidos em
    sucesso; id=None + motivo objetivo quando nenhum ramo resolveu.
    """
    # A rota pai precisa estar CONCRETA. Se ela mesma ainda carrega um {...}
    # (parâmetro ANINHADO — ex.: pai '/users/{user_id}/comments' de
    # '/users/{user_id}/comments/{comment_id}'), casar/disparar contra ela
    # mandaria o placeholder literal na URL, produzindo evidência de uma rota que
    # nunca existiu. Resolver esse parâmetro intermediário seria uma capacidade
    # nova (fora de escopo) — aqui tratamos como "sem interface correlata
    # resolvível", o mesmo caminho de quando nada é declarado na rota pai.
    if _PARAM_SEG_RE.search(rota_pai):
        return None, None, (
            f"rota pai '{rota_pai}' ainda depende de outro parâmetro não "
            f"resolvido (parâmetro aninhado) — nenhuma interface de "
            f"criação/listagem utilizável sem inventar valor"
        )

    tentativas = []
    tem_post = any(verbos[j] == "POST" and rotas[j] == rota_pai for j in range(len(verbos)))
    tem_get = any(verbos[j] == "GET" and rotas[j] == rota_pai for j in range(len(verbos)))

    # Ramo 1 — criar e capturar ID (POST na rota pai, sem body inventado).
    if tem_post:
        resultado, mecanico = _probe_uma(container, base_interno, "POST", rota_pai)
        if mecanico is not None:
            tentativas.append(f"POST {rota_pai}: falha do probe ({mecanico})")
        elif resultado.get("error"):
            tentativas.append(f"POST {rota_pai}: {resultado['error']}")
        else:
            ident = _extrair_id(resultado.get("body", ""))
            if ident is not None:
                return ident, "criacao_id", ""
            tentativas.append(f"POST {rota_pai}: sem ID extraível (HTTP {resultado.get('status')})")

    # Ramo 2 — descobrir via listagem (GET na rota pai).
    if tem_get:
        resultado, mecanico = _probe_uma(container, base_interno, "GET", rota_pai)
        if mecanico is not None:
            tentativas.append(f"GET {rota_pai}: falha do probe ({mecanico})")
        elif resultado.get("error"):
            tentativas.append(f"GET {rota_pai}: {resultado['error']}")
        else:
            ident = _extrair_id(resultado.get("body", ""))
            if ident is not None:
                return ident, "listagem_id", ""
            tentativas.append(f"GET {rota_pai}: sem ID extraível (HTTP {resultado.get('status')})")

    if not tentativas:
        return None, None, (
            f"nenhuma interface de criação (POST) ou listagem (GET) declarada em "
            f"'{rota_pai}' para obter um ID real"
        )
    return None, None, f"não foi possível obter um ID real em '{rota_pai}' — {'; '.join(tentativas)}"


def _coletar_evidencias_interfaces(
    container, base_interno: str, interfaces: list
) -> list[InterfaceEvidence]:
    """Evidência por interface declarada — os três ramos (spec C2c §3.3).

    Stream independente de criteria_evidence. Nunca inventa valor de parâmetro nem
    payload; nunca julga "atende/não atende" — só coleta evidência bruta.
    """
    raws = [str(x) for x in interfaces]
    parsed = [_extrair_verbo_rota(r) for r in raws]
    verbos = [p[0] for p in parsed]
    rotas = [p[1] for p in parsed]

    evid: list = [None] * len(raws)
    grupos: dict = {}  # rota_pai -> [índices dos alvos com param no último segmento]

    for i, raw in enumerate(raws):
        verbo, rota = verbos[i], rotas[i]
        if not verbo or not rota:
            evid[i] = _interface_nao_checavel(
                raw, "verbo e/ou rota não identificáveis na interface declarada"
            )
        elif not _PARAM_SEG_RE.search(rota):
            # Ramo 3 — alcançabilidade pura (qualquer verbo, sem body/headers).
            resultado, mecanico = _probe_uma(container, base_interno, verbo, rota)
            evid[i] = _evidencia_interface(raw, "alcancabilidade", verbo, rota, resultado, mecanico)
        elif _param_no_ultimo_segmento(rota):
            grupos.setdefault(_rota_pai(rota), []).append(i)
        else:
            # Parâmetro fora do último segmento — não resolvível sem inventar valor.
            evid[i] = _interface_nao_checavel(
                raw, f"parâmetro de path fora do último segmento em '{rota}'"
            )

    for pai, indices in grupos.items():
        ident, ramo, motivo = _resolver_id_grupo(container, base_interno, pai, verbos, rotas)
        # Não-destrutivos (GET/PUT/PATCH) antes de DELETE, p/ não invalidar o ID.
        for i in sorted(indices, key=lambda k: 1 if verbos[k] == "DELETE" else 0):
            if ident is None:
                evid[i] = _interface_nao_checavel(raws[i], motivo)
            else:
                rota_alvo = _substituir_ultimo_param(rotas[i], ident)
                resultado, mecanico = _probe_uma(container, base_interno, verbos[i], rota_alvo)
                evid[i] = _evidencia_interface(
                    raws[i], ramo, verbos[i], rota_alvo, resultado, mecanico,
                    prefixo=f"[ID '{ident}' via {ramo}]",
                )

    return evid  # ordem original das interfaces declaradas


def _estagio_validacoes_work_item(
    ctx: _HarnessContext,
) -> tuple[StageResult, list[CriterionEvidence], list[InterfaceEvidence]]:
    if not ctx.app_ok:
        return (
            _pulado(
                StageName.VALIDACOES_WORK_ITEM,
                "Abortado: aplicação não inicializou; evidências não coletadas.",
            ),
            [],
            [],
        )
    t0 = time.time()
    base_interno = f"http://localhost:{_porta_interna(ctx.dockerfile)}"

    evidencias = [
        _coletar_evidencia_criterio(c, ctx.container, base_interno)
        for c in ctx.acceptance_criteria
    ]
    interface_evid = _coletar_evidencias_interfaces(
        ctx.container, base_interno, ctx.contract.get("interfaces") or []
    )

    checaveis = sum(1 for e in evidencias if e.checkable)
    checaveis_if = sum(1 for e in interface_evid if e.checkable)
    result = StageResult(
        stage=StageName.VALIDACOES_WORK_ITEM,
        status=StageStatus.SUCESSO,
        duration_seconds=round(time.time() - t0, 3),
        summary=(
            f"Evidência coletada para {len(evidencias)} critérios ({checaveis} "
            f"verificáveis) e {len(interface_evid)} interfaces ({checaveis_if} "
            f"verificáveis). Nenhum julgamento emitido."
        ),
        evidence={
            "total_criterios": len(evidencias),
            "verificaveis": checaveis,
            "total_interfaces": len(interface_evid),
            "verificaveis_interfaces": checaveis_if,
        },
        error_code=None,
    )
    return result, evidencias, interface_evid


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

    linhas += ["", "## Evidências por interface declarada", ""]
    if report.interface_evidence:
        linhas += [
            "| Interface | Ramo | Verificação | Observado | Verificável |",
            "| --------- | ---- | ----------- | --------- | ----------- |",
        ]
        for e in report.interface_evidence:
            interface = e.interface.replace("|", "\\|")
            ramo = (e.branch or "-").replace("|", "\\|")
            check = e.check_performed.replace("|", "\\|")
            obs = e.observed.replace("|", "\\|")
            linhas.append(f"| {interface} | {ramo} | {check} | {obs} | {e.checkable} |")
    else:
        linhas.append("_Nenhuma interface declarada em contract.interfaces._")
    return "\n".join(linhas) + "\n"


def ler_tech_stack(tool_context: ToolContext | None) -> list[str]:
    """Lê a stack declarada pelo context_engineer em `session.state`.

    O caminho do dado é `state["tasks"]["macro_context"]["tech_stack"]` — a
    saída estruturada (`TasksOutput`) que o `cr_context_engineer` já grava via
    `output_key="tasks"`. Nada é escrito aqui: o harness apenas consome.

    Tolerante a ausência: chamadas diretas (testes/PoC) não passam contexto, e
    a chave pode não existir ou vir malformada. Em qualquer desses casos
    devolve `[]` — decidir o que fazer com uma stack desconhecida não é
    responsabilidade deste módulo.
    """
    if tool_context is None:
        return []

    try:
        tech_stack = tool_context.state["tasks"]["macro_context"]["tech_stack"]
    except (KeyError, TypeError, IndexError):
        return []

    if not isinstance(tech_stack, list) or not all(isinstance(t, str) for t in tech_stack):
        logger.warning(f"[HARNESS] tech_stack em formato inesperado: {tech_stack!r}")
        return []

    return tech_stack


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
    dockerfile: Optional[str] = None,
    dockerfile_origem: Optional[str] = None,
    comando_teste: Optional[str] = None,
    comando_teste_origem: Optional[str] = None,
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
            Quando presente, lê a stack declarada pelo context_engineer em
            `tool_context.state["tasks"]` e grava o caminho absoluto do report
            em `tool_context.state["report_path"]`, tornando a evidência
            resolvível pelo validador sem depender do eco do LLM.

    Returns:
        dict: `ExecutionReport.model_dump(mode="json")` — apenas evidências,
        sem nenhum veredito.
    """
    t_inicio = time.time()

    coder_dir = Path(coder_base_dir) if coder_base_dir else get_agent_workspace("cr_coder")
    exec_dir = Path(execution_base_dir) if execution_base_dir else get_agent_workspace("cr_executor")
    tasks_dir = Path(tasks_base_dir) if tasks_base_dir else get_agent_workspace("cr_context_engineer")

    ctx = _HarnessContext(task_id, coder_dir, exec_dir, tasks_dir)
    ctx.tech_stack = ler_tech_stack(tool_context)
    ctx.dockerfile_resolvido = dockerfile
    ctx.dockerfile_origem_resolvida = dockerfile_origem
    ctx.comando_teste_resolvido = comando_teste
    ctx.comando_teste_origem_resolvida = comando_teste_origem

    stages: list[StageResult] = []
    criteria_evidence: list[CriterionEvidence] = []
    interface_evidence: list[InterfaceEvidence] = []

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
    r7, criteria_evidence, interface_evidence = _estagio_validacoes_work_item(ctx)
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
        interface_evidence=interface_evidence,
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
    InterfaceEvidence,
    StageName,
    StageResult,
    StageStatus,
)