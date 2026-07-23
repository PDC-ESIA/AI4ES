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
import requests
from docker.errors import APIError, BuildError

from shared.tools import harness_docker as hd
from shared.tools.log_parser_tool import parse_log_text
from shared.tools.pytest_runner import executar_pytest_tool
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

    # Valida o workspace do coder (deve conter código Python)
    if not ctx.coder_dir.exists() or not any(ctx.coder_dir.rglob("*.py")):
        return StageResult(
            stage=StageName.PREPARACAO_AMBIENTE,
            status=StageStatus.ERRO,
            duration_seconds=round(time.time() - t0, 3),
            summary="Nenhum arquivo Python encontrado no workspace do coder.",
            evidence={"coder_dir": str(ctx.coder_dir)},
            error_code="SRC_VAZIO",
        )

    # Resolve Dockerfile (do coder ou fallback determinístico via harness_docker)
    dockerfile_path = ctx.coder_dir / "Dockerfile"
    if dockerfile_path.is_file():
        ctx.dockerfile = dockerfile_path.read_text(encoding="utf-8")
        origem_dockerfile = "coder"
    else:
        ctx.dockerfile = hd._generate_dockerfile(ctx.coder_dir)
        origem_dockerfile = "fallback"

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
    try:
        container = client.containers.run(
            image=hd._IMAGE_TAG,
            name=hd._CONTAINER_NAME,
            detach=True,
            mem_limit=hd._MEMORY_LIMIT,
            cpu_quota=hd._CPU_QUOTA,
            ports={"8000/tcp": ("0.0.0.0", hd._HOST_PORT)},
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
            evidence={"container_status": container.status, "exit_code": exit_code},
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

def _estagio_inicializacao(ctx: _HarnessContext) -> StageResult:
    if not ctx.deploy_ok:
        return _pulado(
            StageName.INICIALIZACAO_APLICACAO,
            "Abortado: implantação do artefato não foi bem-sucedida.",
        )
    t0 = time.time()

    # Grace period para a app subir dentro do container
    time.sleep(hd._STARTUP_GRACE_PERIOD)

    healthcheck_url = f"{ctx.base_url}{hd._HEALTHCHECK_ENDPOINT}"
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

def _localizar_suite(coder_dir: Path) -> Optional[Path]:
    """Localiza um arquivo de suíte de testes no workspace do coder."""
    candidatos = sorted(
        p for p in coder_dir.rglob("test_*.py") if "__pycache__" not in p.parts
    )
    candidatos += sorted(
        p for p in coder_dir.rglob("*_test.py") if "__pycache__" not in p.parts
    )
    return candidatos[0] if candidatos else None


def _estagio_testes(ctx: _HarnessContext) -> StageResult:
    if not ctx.app_ok:
        return _pulado(
            StageName.TESTES_AUTOMATIZADOS,
            "Abortado: aplicação não inicializou; testes não executados.",
        )
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

    resultado = executar_pytest_tool(str(suite))
    ok = resultado.get("status") == "sucesso"
    return StageResult(
        stage=StageName.TESTES_AUTOMATIZADOS,
        status=StageStatus.SUCESSO if ok else StageStatus.FALHA,
        duration_seconds=round(time.time() - t0, 3),
        summary=(
            f"Suíte '{suite.name}' executada: "
            f"{resultado.get('resultado_resumo', resultado.get('status'))}."
        ),
        evidence={"suite": str(suite), "pytest": resultado},
        error_code=None if ok else "TESTES_FALHARAM",
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
    """
    path_match = _PATH_RE.search(criterion)
    tem_http = bool(_VERBO_HTTP_RE.search(criterion))

    if path_match or tem_http:
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
    iteration: int = 0,
    *,
    coder_base_dir=None,
    execution_base_dir=None,
    tasks_base_dir=None,
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

    return payload


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
