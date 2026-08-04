"""Adapter da stack Python — testes via pytest DENTRO do container implantado.

Encapsula tudo que era específico de Python/pytest no Estágio 6 do harness:
localizar a suíte, garantir o pytest no container, rodar (modo json com
report/cov; fallback plain), parsear o resultado e classificar o exit code. O
harness genérico deixou de conhecer qualquer um desses detalhes — chama apenas
`executar_testes`.

Roda o pytest contra o artefato REALMENTE implantado em `/app` (Dockerfile:
WORKDIR /app + COPY . /app/), não contra o host — mesma decisão de antes, que
evitava a divergência host↔container. Continua só coletando evidência: nenhum
veredito, nenhum contador global.
"""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Any, Optional

from .base import ExecNoContainer, FileMarker, ResultadoTestes, StackAdapter

_TESTS_TIMEOUT = 60  # segundos — teto para a execução da suíte no container

# Caminho onde o artefato do coder é implantado no container (Dockerfile:
# WORKDIR /app + COPY . /app/). É o mesmo contrato que `_exec_no_container` usa
# como workdir no harness; o adapter precisa dele para montar o alvo do pytest e
# os caminhos dos relatórios que grava lá dentro.
_APP_WORKDIR = "/app"
_REPORT_JSON_IN = f"{_APP_WORKDIR}/.harness_pytest_report.json"
_COV_JSON_IN = f"{_APP_WORKDIR}/.harness_cov.json"

_PLAIN_PASSOU_RE = re.compile(r"(\d+) passed")
_PLAIN_FALHOU_RE = re.compile(r"(\d+) failed")
_PLAIN_ERRO_RE = re.compile(r"(\d+) error")


def _localizar_suite(coder_dir: Path) -> Optional[Path]:
    """Localiza um arquivo de suíte de testes no workspace do coder."""
    candidatos = sorted(
        p for p in coder_dir.rglob("test_*.py") if "__pycache__" not in p.parts
    )
    candidatos += sorted(
        p for p in coder_dir.rglob("*_test.py") if "__pycache__" not in p.parts
    )
    return candidatos[0] if candidatos else None


def _pytest_disponivel(exec_no_container: ExecNoContainer, container: Any) -> bool:
    """Garante `pytest` executável no container; tenta instalar se ausente.

    A instalação em runtime depende de rede no container. Se falhar, retorna
    False e o estágio degrada de forma honesta (PULADO/PYTEST_INDISPONIVEL) —
    NÃO cai para o host, para não reintroduzir a divergência host↔container.
    """
    code, _, _ = exec_no_container(container, "python -m pytest --version")
    if code == 0:
        return True
    exec_no_container(
        container, "pip install --no-cache-dir pytest pytest-json-report pytest-cov"
    )
    code, _, _ = exec_no_container(container, "python -m pytest --version")
    return code == 0


def _rodar_pytest_no_container(
    exec_no_container: ExecNoContainer, container: Any, alvo: str
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
    code, out, err = exec_no_container(container, cmd_json)
    if code == 4:  # opção desconhecida → plugins ausentes → fallback texto
        cmd_plain = (
            f"timeout {_TESTS_TIMEOUT} python -m pytest {alvo_q} -q -p no:cacheprovider"
        )
        code, out, err = exec_no_container(container, cmd_plain)
        return code, out, err, "plain"
    return code, out, err, "json"


def _parse_report_json(exec_no_container: ExecNoContainer, container: Any) -> dict:
    """Lê e resume o report.json do pytest-json-report de dentro do container."""
    _, raw, _ = exec_no_container(container, f"cat {_REPORT_JSON_IN}")
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


def _parse_cobertura_json(exec_no_container: ExecNoContainer, container: Any) -> dict:
    """Lê o coverage.json de dentro do container (best-effort)."""
    try:
        _, raw, _ = exec_no_container(container, f"cat {_COV_JSON_IN}")
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


class PythonAdapter(StackAdapter):
    """Stack Python: suíte pytest rodada no container implantado."""

    nome = "python"
    tech_stack_keywords = ("python",)
    file_markers = (FileMarker("requirements.txt"), FileMarker("pyproject.toml"))

    def executar_testes(
        self, exec_no_container: ExecNoContainer, container: Any, coder_dir: Path
    ) -> ResultadoTestes:
        suite = _localizar_suite(coder_dir)
        if suite is None:
            return ResultadoTestes(
                status="pulado",
                summary="Nenhuma suíte de testes encontrada no workspace do coder.",
                error_code=None,
                evidence={"suite": None},
            )

        # Path host → path no container (Dockerfile: WORKDIR /app + COPY . /app/).
        rel = suite.relative_to(coder_dir)
        alvo = f"{_APP_WORKDIR}/{rel.as_posix()}"

        try:
            if not _pytest_disponivel(exec_no_container, container):
                return ResultadoTestes(
                    status="pulado",
                    summary=(
                        "pytest indisponível no container e não foi possível "
                        "instalá-lo (sem rede?). Testes não executados."
                    ),
                    error_code="PYTEST_INDISPONIVEL",
                    evidence={"suite": str(suite), "alvo_container": alvo},
                )

            exit_code, stdout, stderr, modo = _rodar_pytest_no_container(
                exec_no_container, container, alvo
            )
        except Exception as e:
            return ResultadoTestes(
                status="erro",
                summary=f"Falha ao executar pytest no container: {e}",
                error_code="EXEC_FALHOU",
                evidence={"suite": str(suite), "alvo_container": alvo},
            )

        # Resumo estruturado (JSON report quando disponível; stdout como fallback).
        if modo == "json":
            try:
                resumo = _parse_report_json(exec_no_container, container)
            except Exception:
                resumo = _parse_stdout_plain(stdout)
            cobertura = _parse_cobertura_json(exec_no_container, container)
        else:
            resumo = _parse_stdout_plain(stdout)
            cobertura = {"percentual": 0.0, "linhas_cobertas": 0, "linhas_totais": 0}

        # Classificação técnica (SEM veredito) a partir do exit code do pytest:
        #   0 = tudo passou | 1 = houve falhas | 5 = nada coletado
        #   124 = timeout (coreutils) | 2/3/4 = interrompido/erro interno/uso incorreto
        if exit_code == 5:
            return ResultadoTestes(
                status="pulado",
                summary=f"Suíte '{suite.name}' não coletou nenhum teste.",
                error_code=None,
                evidence={"suite": str(suite), "alvo_container": alvo, "modo": modo},
            )
        if exit_code == 0:
            status, error_code = "sucesso", None
        elif exit_code == 124:
            status, error_code = "falha", "TESTES_TIMEOUT"
        elif exit_code == 1:
            status, error_code = "falha", "TESTES_FALHARAM"
        else:
            status, error_code = "erro", "PYTEST_ERRO_EXECUCAO"

        tail = (stdout or "")[-3000:]
        if stderr:
            tail += f"\n--- stderr ---\n{stderr[-1000:]}"

        return ResultadoTestes(
            status=status,
            summary=(
                f"Suíte '{suite.name}' executada no container "
                f"(modo={modo}, exit={exit_code}): {resumo['passaram']} passaram, "
                f"{resumo['falharam']} falharam, {resumo['erros']} erros."
            ),
            error_code=error_code,
            evidence={
                "suite": str(suite),
                "alvo_container": alvo,
                "modo": modo,
                "exit_code": exit_code,
                "resumo": resumo,
                "cobertura": cobertura,
                "saida_tail": tail,
            },
        )
