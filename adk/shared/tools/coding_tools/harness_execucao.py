"""Harness de Execução — orquestração determinística dos 9 estágios de validação.

Este módulo expõe uma única tool determinística, `executar_harness_validacao`,
que executa em Python puro (a ordem NÃO depende de LLM) os nove estágios que
levam o artefato do coder de "arquivos no workspace" até um `ExecutionReport`
consolidado e persistido.

Princípio central: o harness **apenas descreve o que aconteceu e coleta
evidências**. Ele nunca decide se um critério de aceite foi atendido — esse
julgamento pertence ao validador (implementation_validator). Por isso o
`ExecutionReport` não carrega nenhum campo de decisão.

Arquitetura agnóstica de tecnologia (issue #370): o harness deixou de inferir
stack/entrypoint e de assumir Docker/FastAPI. Agora consome três contratos
declarativos e delega a execução a uma abstração de sandbox plugável:

- `run.json` (manifesto): descreve *comandos* (build/run/test) e a *superfície*
  do produto (service/command/none). Carregado por `shared.execution.manifest`.
- Perfil de execução (`shared.execution.profile`): traduz a superfície em
  comportamento do harness (sobe serviço? valida HTTP? quais estágios são
  críticos?), sem `if product_type == ...` espalhados pelos estágios.
- Sandbox (`shared.execution.sandbox`): executa os comandos de forma isolada —
  `direct` (subprocess efêmero, padrão) ou `docker` (opt-in).
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from google.adk.tools import ToolContext

from shared.execution.manifest import ManifestError, RunManifest, load_manifest
from shared.execution.profile import ExecutionProfile, select_profile
from shared.execution.sandbox import Sandbox, create_sandbox
from shared.tools.coding_tools import harness_docker as hd
from shared.tools.coding_tools.harness_schemas import (
    CriterionEvidence,
    ExecutionReport,
    StageName,
    StageResult,
    StageStatus,
)
from shared.tools.log_parser_tool import parse_log_text
from shared.workspace import get_agent_workspace

logger = logging.getLogger(__name__)

# Nome do manifesto de execução emitido pelo coder na raiz do artefato.
_MANIFEST_FILENAME = "run.json"
# Nome do arquivo de contexto macro persistido pelo context_engineer (product_type).
_MACRO_CONTEXT_FILENAME = "_macro_context.json"

# Tetos de tempo (segundos) por classe de comando do manifesto. Cada comando é
# executado sob o timeout do sandbox; estourá-lo é evidência, não exceção.
_BUILD_TIMEOUT = 300  # build/preparação (pip install, npm ci, compilação…)
_RUN_COMMAND_TIMEOUT = 120  # execução única do `run` no perfil command
_TESTS_TIMEOUT = 120  # cada comando da suíte de testes do manifesto

# Estágios críticos usados quando não há perfil resolvido (falha antes do
# estágio 1 concluir). Perfis fornecem seus próprios `critical_stages`.
_DEFAULT_CRITICAL_STAGES = (
    "preparacao_ambiente",
    "implantacao_artefato",
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
        self.product_type: str = "a definir"
        self.manifest: Optional[RunManifest] = None
        self.profile: Optional[ExecutionProfile] = None
        self.sandbox: Optional[Sandbox] = None
        self.build_logs: str = ""
        self.runtime_logs: str = ""
        self.base_url: str = ""
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


def _cmd_env(ctx: _HarnessContext) -> Optional[dict[str, str]]:
    """Env adicional dos comandos, a partir do manifesto (None quando vazio)."""
    if ctx.manifest and ctx.manifest.env:
        return dict(ctx.manifest.env)
    return None


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

    # ---- Manifesto de execução (run.json) — contrato coder→harness ----
    manifest_path = ctx.coder_dir / _MANIFEST_FILENAME
    if not manifest_path.is_file():
        return StageResult(
            stage=StageName.PREPARACAO_AMBIENTE,
            status=StageStatus.ERRO,
            duration_seconds=round(time.time() - t0, 3),
            summary=(
                f"Manifesto de execução '{_MANIFEST_FILENAME}' ausente no "
                f"workspace do coder ({ctx.coder_dir}). O coder deve emiti-lo."
            ),
            evidence={"manifest_path": str(manifest_path)},
            error_code="MANIFESTO_AUSENTE",
        )
    try:
        ctx.manifest = load_manifest(manifest_path)
    except ManifestError as e:
        return StageResult(
            stage=StageName.PREPARACAO_AMBIENTE,
            status=StageStatus.ERRO,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Manifesto de execução inválido/incoerente: {e}",
            evidence={"manifest_path": str(manifest_path)},
            error_code="MANIFESTO_INVALIDO",
        )

    # ---- Contexto macro (product_type), best-effort ----
    ctx.product_type = _carregar_product_type(ctx.tasks_dir)

    # ---- Perfil de execução derivado da superfície declarada ----
    try:
        ctx.profile = select_profile(ctx.manifest.surface)
    except ValueError as e:
        return StageResult(
            stage=StageName.PREPARACAO_AMBIENTE,
            status=StageStatus.ERRO,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Não foi possível selecionar perfil de execução: {e}",
            evidence={"surface": ctx.manifest.surface},
            error_code="PERFIL_DESCONHECIDO",
        )

    # ---- URL base do serviço (só relevante quando surface=service) ----
    if ctx.manifest.port is not None:
        ctx.base_url = f"http://localhost:{ctx.manifest.port}"

    # ---- Sandbox de execução (direct/docker) preparado com o artefato ----
    try:
        ctx.sandbox = create_sandbox(
            ctx.manifest.sandbox,
            port=ctx.manifest.port,
            workdir_subpath=ctx.manifest.workdir,
        )
        ctx.sandbox.setup(ctx.coder_dir)
    except Exception as e:
        return StageResult(
            stage=StageName.PREPARACAO_AMBIENTE,
            status=StageStatus.ERRO,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Falha ao inicializar o sandbox '{ctx.manifest.sandbox}': {e}",
            evidence={"sandbox": ctx.manifest.sandbox},
            error_code="SANDBOX_INDISPONIVEL",
        )

    ctx.env_ok = True
    return StageResult(
        stage=StageName.PREPARACAO_AMBIENTE,
        status=StageStatus.SUCESSO,
        duration_seconds=round(time.time() - t0, 3),
        summary=(
            f"Ambiente preparado: Task carregada ({len(ctx.acceptance_criteria)} "
            f"critérios), manifesto surface='{ctx.manifest.surface}' "
            f"(perfil {ctx.profile.name}), sandbox '{ctx.manifest.sandbox}'."
        ),
        evidence={
            "task_file": str(task_file),
            "acceptance_criteria": ctx.acceptance_criteria,
            "surface": ctx.manifest.surface,
            "profile": ctx.profile.name,
            "sandbox": ctx.manifest.sandbox,
            "product_type": ctx.product_type,
            "build_commands": list(ctx.manifest.build),
            "run_command": ctx.manifest.run,
            "test_commands": list(ctx.manifest.test),
        },
        error_code=None,
    )


def _carregar_product_type(tasks_dir: Path) -> str:
    """Lê o product_type do `_macro_context.json` (best-effort; 'a definir' se ausente)."""
    macro_path = tasks_dir / _MACRO_CONTEXT_FILENAME
    if not macro_path.is_file():
        return "a definir"
    try:
        macro = json.loads(macro_path.read_text(encoding="utf-8"))
        if isinstance(macro, dict):
            return macro.get("product_type") or "a definir"
    except Exception as e:
        logger.warning(f"[HARNESS] Falha ao ler macro_context: {e}")
    return "a definir"


# ===========================================================================
# Estágio 2 — Implantação do artefato (build + subida de serviço) [crítico]
# ===========================================================================

def _estagio_implantacao(ctx: _HarnessContext) -> StageResult:
    t0 = time.time()
    assert ctx.manifest is not None and ctx.profile is not None and ctx.sandbox is not None

    env = _cmd_env(ctx)
    linhas: list[str] = []

    # ---- Build: executa cada comando do manifesto, em ordem ----
    for cmd in ctx.manifest.build:
        linhas.append(f"$ {cmd}")
        res = ctx.sandbox.exec(cmd, timeout=_BUILD_TIMEOUT, env=env)
        if res.stdout:
            linhas.append(res.stdout)
        if res.stderr:
            linhas.append(res.stderr)
        if res.timed_out or (res.exit_code not in (0, None)):
            ctx.build_logs = "\n".join(linhas)
            motivo = (
                f"Comando de build excedeu {_BUILD_TIMEOUT}s (timeout)."
                if res.timed_out
                else f"Comando de build retornou exit={res.exit_code}."
            )
            return StageResult(
                stage=StageName.IMPLANTACAO_ARTEFATO,
                status=StageStatus.FALHA,
                duration_seconds=round(time.time() - t0, 3),
                summary=f"Falha no build: {motivo} Comando: {cmd!r}.",
                evidence={
                    "comando_falho": cmd,
                    "exit_code": res.exit_code,
                    "timed_out": res.timed_out,
                    "build_logs_tail": ctx.build_logs[-2000:],
                },
                error_code="FALHA_BUILD",
            )

    ctx.build_logs = "\n".join(linhas)

    # ---- Subida de serviço (só perfil S) ----
    servico_iniciado = False
    if ctx.profile.starts_service and ctx.manifest.run:
        try:
            ctx.sandbox.start_service(ctx.manifest.run, env=env)
            servico_iniciado = True
        except Exception as e:
            return StageResult(
                stage=StageName.IMPLANTACAO_ARTEFATO,
                status=StageStatus.ERRO,
                duration_seconds=round(time.time() - t0, 3),
                summary=f"Erro ao iniciar o serviço: {e}",
                evidence={"run_command": ctx.manifest.run,
                          "build_logs_tail": ctx.build_logs[-2000:]},
                error_code="ERRO_START_SERVICE",
            )

    ctx.deploy_ok = True
    resumo = (
        f"Artefato implantado: {len(ctx.manifest.build)} comando(s) de build "
        f"concluído(s)"
    )
    resumo += "; serviço iniciado em segundo plano." if servico_iniciado else "."
    return StageResult(
        stage=StageName.IMPLANTACAO_ARTEFATO,
        status=StageStatus.SUCESSO,
        duration_seconds=round(time.time() - t0, 3),
        summary=resumo,
        evidence={
            "build_commands": list(ctx.manifest.build),
            "servico_iniciado": servico_iniciado,
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
# Estágio 4 — Inicialização da aplicação [crítico p/ perfil S]
# ===========================================================================

def _estagio_inicializacao(ctx: _HarnessContext) -> StageResult:
    if not ctx.deploy_ok:
        return _pulado(
            StageName.INICIALIZACAO_APLICACAO,
            "Abortado: implantação do artefato não foi bem-sucedida.",
        )
    assert ctx.manifest is not None and ctx.profile is not None and ctx.sandbox is not None

    # Perfil B (surface=none): não há comando/serviço de topo a inicializar.
    if ctx.manifest.surface == "none":
        return _pulado(
            StageName.INICIALIZACAO_APLICACAO,
            "Sem superfície de execução de topo (surface=none): nada a inicializar.",
        )

    # Perfil S (service): healthcheck HTTP contra o serviço em segundo plano.
    if ctx.profile.starts_service:
        return _inicializacao_servico(ctx)

    # Perfil C (command): executa o `run` que roda e termina; exit-code é o sinal.
    return _inicializacao_comando(ctx)


def _inicializacao_servico(ctx: _HarnessContext) -> StageResult:
    t0 = time.time()
    time.sleep(hd._STARTUP_GRACE_PERIOD)

    healthcheck = ctx.manifest.healthcheck or "/"
    healthcheck_url = f"{ctx.base_url}{healthcheck}"
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


def _inicializacao_comando(ctx: _HarnessContext) -> StageResult:
    t0 = time.time()
    res = ctx.sandbox.exec(
        ctx.manifest.run, timeout=_RUN_COMMAND_TIMEOUT, env=_cmd_env(ctx)
    )
    # Guarda a saída do comando como log de runtime (coletado no estágio 5).
    ctx.runtime_logs = "\n".join(
        p for p in (res.stdout, res.stderr) if p
    )

    if res.timed_out:
        return StageResult(
            stage=StageName.INICIALIZACAO_APLICACAO,
            status=StageStatus.FALHA,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Comando de execução excedeu {_RUN_COMMAND_TIMEOUT}s (timeout).",
            evidence={"run_command": ctx.manifest.run, "timed_out": True},
            error_code="EXECUCAO_TIMEOUT",
        )
    if res.exit_code not in (0, None):
        return StageResult(
            stage=StageName.INICIALIZACAO_APLICACAO,
            status=StageStatus.FALHA,
            duration_seconds=round(time.time() - t0, 3),
            summary=f"Comando de execução retornou exit={res.exit_code}.",
            evidence={
                "run_command": ctx.manifest.run,
                "exit_code": res.exit_code,
                "saida_tail": ctx.runtime_logs[-3000:],
            },
            error_code="EXECUCAO_FALHOU",
        )

    ctx.app_ok = True
    return StageResult(
        stage=StageName.INICIALIZACAO_APLICACAO,
        status=StageStatus.SUCESSO,
        duration_seconds=round(time.time() - t0, 3),
        summary=f"Comando de execução concluído com sucesso (exit={res.exit_code}).",
        evidence={
            "run_command": ctx.manifest.run,
            "exit_code": res.exit_code,
            "saida_tail": ctx.runtime_logs[-3000:],
        },
        error_code=None,
    )


# ===========================================================================
# Estágio 5 — Coleta dos logs de execução (runtime)
# ===========================================================================

def _estagio_coleta_logs_execucao(ctx: _HarnessContext) -> StageResult:
    if not ctx.deploy_ok:
        return _pulado(
            StageName.COLETA_LOGS_EXECUCAO,
            "Abortado: nada em execução para coletar logs.",
        )
    assert ctx.manifest is not None and ctx.profile is not None and ctx.sandbox is not None
    t0 = time.time()

    # Serviço (S): logs vêm do processo em segundo plano do sandbox. Comando (C):
    # a saída já foi capturada na inicialização (ctx.runtime_logs).
    if ctx.profile.starts_service:
        try:
            ctx.runtime_logs = ctx.sandbox.logs()
        except Exception as e:
            logger.warning(f"[HARNESS] Falha ao coletar logs de runtime: {e}")
            ctx.runtime_logs = ctx.runtime_logs or ""

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
# Estágio 6 — Execução dos testes automatizados (comandos do manifesto)
# ===========================================================================

_PLAIN_PASSOU_RE = re.compile(r"(\d+) passed")
_PLAIN_FALHOU_RE = re.compile(r"(\d+) failed")
_PLAIN_ERRO_RE = re.compile(r"(\d+) error")


def _resumo_saida_testes(saida: str) -> dict:
    """Extrai contadores best-effort da saída dos testes (formato pytest-like)."""

    def _n(rx: re.Pattern) -> int:
        m = rx.search(saida)
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
        "total": passaram + falharam + erros,
    }


def _estagio_testes(ctx: _HarnessContext) -> StageResult:
    """Estágio 6 — executa os comandos `test` do manifesto no sandbox.

    Gatilha em `deploy_ok` (build concluído): a suíte roda contra o artefato
    implantado, independentemente da inicialização da aplicação. Apenas coleta
    evidência — a decisão sobre o que as falhas significam é do validador.
    """
    if not ctx.deploy_ok:
        return _pulado(
            StageName.TESTES_AUTOMATIZADOS,
            "Abortado: implantação não concluída; testes não executados.",
        )
    assert ctx.manifest is not None and ctx.sandbox is not None

    if not ctx.manifest.test:
        return StageResult(
            stage=StageName.TESTES_AUTOMATIZADOS,
            status=StageStatus.PULADO,
            duration_seconds=0.0,
            summary="Manifesto não declara comandos de teste ('test' vazio).",
            evidence={"test_commands": []},
            error_code=None,
        )

    t0 = time.time()
    env = _cmd_env(ctx)
    resultados: list[dict] = []
    any_timeout = False
    any_fail = False
    linhas: list[str] = []

    for cmd in ctx.manifest.test:
        res = ctx.sandbox.exec(cmd, timeout=_TESTS_TIMEOUT, env=env)
        saida = "\n".join(p for p in (res.stdout, res.stderr) if p)
        linhas.append(f"$ {cmd}\n{saida}")
        resultados.append(
            {
                "comando": cmd,
                "exit_code": res.exit_code,
                "timed_out": res.timed_out,
                "resumo": _resumo_saida_testes(saida),
                "saida_tail": saida[-2000:],
            }
        )
        if res.timed_out:
            any_timeout = True
        elif res.exit_code not in (0, None):
            any_fail = True

    if any_timeout:
        status, error_code = StageStatus.FALHA, "TESTES_TIMEOUT"
    elif any_fail:
        status, error_code = StageStatus.FALHA, "TESTES_FALHARAM"
    else:
        status, error_code = StageStatus.SUCESSO, None

    tot_pass = sum(r["resumo"]["passaram"] for r in resultados)
    tot_fail = sum(r["resumo"]["falharam"] for r in resultados)
    tot_err = sum(r["resumo"]["erros"] for r in resultados)
    return StageResult(
        stage=StageName.TESTES_AUTOMATIZADOS,
        status=status,
        duration_seconds=round(time.time() - t0, 3),
        summary=(
            f"{len(resultados)} comando(s) de teste executado(s): "
            f"{tot_pass} passaram, {tot_fail} falharam, {tot_err} erros."
        ),
        evidence={
            "resultados": resultados,
            "saida_tail": "\n".join(linhas)[-3000:],
        },
        error_code=error_code,
    )


# ===========================================================================
# Estágio 7 — Execução das validações do Work Item (só coleta evidência)
# ===========================================================================

_PATH_RE = re.compile(r"(/[\w\-/{}]*)")
_VERBO_HTTP_RE = re.compile(r"\b(GET|POST|PUT|DELETE|PATCH)\b", re.IGNORECASE)


def _evidencia_http(
    criterion: str, base_url: str, main_route: Optional[str]
) -> CriterionEvidence:
    """Deriva uma checagem HTTP determinística para um critério, SEM julgá-lo.

    A única checagem que o harness sabe derivar com segurança é um GET sem
    payload. Critérios que mencionam POST/PUT/PATCH/DELETE exigiriam inventar
    corpo/headers — adivinhação que o harness não faz. Nesses casos o critério
    é marcado como NÃO verificável (evidência honesta).
    """
    path_match = _PATH_RE.search(criterion)
    verbos = {m.upper() for m in _VERBO_HTTP_RE.findall(criterion)}
    verbos_nao_checaveis = verbos - {"GET"}

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

    return CriterionEvidence(
        criterion=criterion,
        check_performed="Nenhuma checagem determinística derivável (critério semântico).",
        observed="Requer avaliação do validador a partir das evidências coletadas.",
        checkable=False,
    )


def _evidencia_nao_http(criterion: str, motivo: str) -> CriterionEvidence:
    """Evidência textual (não verificável automaticamente) para perfis sem HTTP."""
    return CriterionEvidence(
        criterion=criterion,
        check_performed=f"Nenhuma checagem HTTP derivável ({motivo}).",
        observed=(
            "Requer avaliação do validador a partir das evidências de build, "
            "execução e testes coletadas."
        ),
        checkable=False,
    )


def _estagio_validacoes_work_item(
    ctx: _HarnessContext,
) -> tuple[StageResult, list[CriterionEvidence]]:
    if not ctx.deploy_ok or ctx.profile is None:
        return (
            _pulado(
                StageName.VALIDACOES_WORK_ITEM,
                "Abortado: implantação não concluída; evidências não coletadas.",
            ),
            [],
        )
    t0 = time.time()

    # Só o perfil S deriva checagens HTTP, e apenas quando a app está no ar.
    http_ok = ctx.profile.validates_http and ctx.app_ok
    if ctx.profile.validates_http and not ctx.app_ok:
        motivo = "aplicação não inicializou"
    elif not ctx.profile.validates_http:
        motivo = f"perfil {ctx.profile.name} não expõe superfície HTTP"
    else:
        motivo = ""

    evidencias: list[CriterionEvidence] = []
    for c in ctx.acceptance_criteria:
        if http_ok:
            evidencias.append(_evidencia_http(c, ctx.base_url, ctx.main_route))
        else:
            evidencias.append(_evidencia_nao_http(c, motivo))

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

def _agregar_status(
    stages: list[StageResult], critical_stages: tuple[str, ...]
) -> StageStatus:
    """Deriva o status técnico agregado (não é veredito de aprovação).

    Uma suíte declarada que executou e falhou é sempre bloqueante. Os perfis
    continuam decidindo quais estágios de infraestrutura são críticos, mas não
    podem transformar ``TESTES_FALHARAM``/``TESTES_TIMEOUT`` em sucesso técnico:
    isso fazia o validador aprovar a task com nota 0.6 (build e serviço OK,
    zero testes passando) e encerrar o loop antes de qualquer correção.

    ``PULADO`` permanece permitido quando o manifesto não declara testes. A
    obrigatoriedade de existir uma suíte é uma decisão de contrato/DoD distinta;
    esta função garante apenas que uma suíte efetivamente declarada não possa
    falhar silenciosamente.
    """
    por_estagio = {s.stage.value: s.status for s in stages}
    if any(s.status == StageStatus.ERRO for s in stages):
        return StageStatus.ERRO

    if por_estagio.get(StageName.TESTES_AUTOMATIZADOS) == StageStatus.FALHA:
        return StageStatus.FALHA

    for critico in critical_stages:
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
    críticos (definidos pelo perfil de execução) abortam os estágios que deles
    dependem quando falham. O harness apenas coleta evidências — nunca decide se
    um critério de aceite foi atendido (isso cabe ao validador).

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

    try:
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
        critical = ctx.profile.critical_stages if ctx.profile else _DEFAULT_CRITICAL_STAGES
        overall = _agregar_status(stages, critical)
        stages.append(StageResult(
            stage=StageName.CONSOLIDACAO_EVIDENCIAS,
            status=StageStatus.SUCESSO,
            duration_seconds=round(time.time() - t8, 3),
            summary=f"Evidências consolidadas de {len(stages)} estágios anteriores.",
            evidence={"overall_status": overall.value,
                      "critical_stages": list(critical)},
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
    finally:
        # O sandbox é sempre encerrado, mesmo em caso de exceção inesperada:
        # encerra processos em segundo plano e remove diretórios/containers temp.
        if ctx.sandbox is not None:
            try:
                ctx.sandbox.cleanup()
            except Exception as e:
                logger.warning(f"[HARNESS] Falha ao limpar o sandbox: {e}")


def _resolver_task_id(task_id: str, tool_context: ToolContext | None) -> str:
    """Resolve o task_id EFETIVO: o state prevalece sobre o argumento do LLM.

    O `task_id` da vez é escopado por código pelo `TaskIterator`, que o grava em
    `state["task_id"]` antes de invocar o loop da task. Se o LLM chamar a tool
    com outro valor, o valor do state vence — sem isso, a cobertura por task
    voltaria a depender do que o modelo resolve escrever (issue #369).

    Chamadas diretas (testes/PoC) não têm `tool_context`, ou têm um state sem
    `task_id`: nesses casos o argumento recebido é usado como sempre foi.
    """
    if tool_context is None:
        return task_id

    do_state = tool_context.state.get("task_id")
    if not isinstance(do_state, str) or not do_state.strip():
        return task_id

    if do_state != task_id:
        logger.warning(
            "[HARNESS] task_id do argumento (%r) diverge do escopado em "
            "state['task_id'] (%r); o valor do state prevalece.",
            task_id,
            do_state,
        )
    return do_state


def executar_harness_tool(
    task_id: str,
    iteration: int = 1,
    tool_context: ToolContext | None = None,
) -> dict:
    """Entrypoint do harness exposto ao LLM (via FunctionTool).

    Os diretórios de trabalho são SEMPRE os do workspace do fluxo — o LLM
    não os controla. A função `executar_harness_validacao` mantém os
    parâmetros `*_base_dir` para injeção em testes/PoC, fora do schema da tool.

    Pelo mesmo princípio, `task_id` não é escolha do LLM quando há um valor
    escopado no state: ver `_resolver_task_id`.

    """
    return executar_harness_validacao(
        _resolver_task_id(task_id, tool_context),
        iteration,
        tool_context=tool_context,
    )
