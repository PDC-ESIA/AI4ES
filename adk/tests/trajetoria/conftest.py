"""conftest.py — Camada 2 (trajetória).

Enquanto a Camada 1 valida "o código faz o que deveria", esta camada valida
"o agente decidiu chamar as coisas certas, na ordem certa" (trajectory
evaluation, no vocabulário do MASEval e da survey de avaliação de agentes
LLM). Isso cobre, por exemplo:

- o Orchestrator dispara os 4 pipelines (requirements → design →
  coding_review → qa) na ordem esperada;
- um HITL checkpoint pausa a execução e retoma corretamente após a
  decisão humana;
- o harness de execução persiste evidências e o validador só aprova com
  base nelas (nunca no status técnico isolado).

O artefato central desta camada é o **trace**: a sequência de eventos
observados durante a execução, organizada em duas camadas (ver
`tests/fixtures/trace_helpers.py`):

- **raw layer**: o evento como foi emitido (Event do ADK, resposta de
  LLM, dict de retorno de tool).
- **canonical layer**: projeção normalizada e estável (`agente`, `acao`,
  `status`, `timestamp`, `metadata`) usada nas asserções.

Integração com Langfuse: o projeto já depende de `langfuse` (observabilidade
de produção), mas os testes NÃO chamam o serviço Langfuse real — o
`trace_collector` abaixo replica a mesma forma canônica que o Langfuse
usaria (spans com nome, status e metadata), para que os traces coletados
em teste sejam facilmente comparáveis/exportáveis para um trace real de
produção, sem acoplar a suite a uma conta/API key do Langfuse.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from tests.fixtures.trace_helpers import TraceCollector


# ---------------------------------------------------------------------------
# Coleta de trace estruturado
# ---------------------------------------------------------------------------

@pytest.fixture
def trace_collector(tmp_path: Path, request: pytest.FixtureRequest):
    """`TraceCollector` com dump automático em JSON ao final do teste.

    O JSON (canonical + raw layer) é escrito em
    ``tmp_path/traces/<nome_do_teste>.json`` mesmo se o teste falhar,
    facilitando debug de trajetórias inesperadas. Para inspecionar
    manualmente: rode com ``pytest --basetemp=.pytest_traces`` e o
    arquivo fica preservado após a execução.
    """
    collector = TraceCollector()
    yield collector

    destino = tmp_path / "traces" / f"{request.node.name}.json"
    collector.dump(destino)


@pytest.fixture
def workspace_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Workspace isolado por teste, substituindo `workspace_output` global.

    Equivalente ao `tmp_workspace` usado em `test_integration_orchestrator_qa.py`,
    promovido a fixture compartilhada da camada: cria a raiz do workspace com
    o marker esperado por `shared.workspace` e aponta `WORKSPACE_OUTPUT_DIR`
    para dentro do `tmp_path` do teste.
    """
    from shared import workspace as _workspace_mod

    ws = tmp_path / "workspace_output"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / ".ai4se_workspace").write_text("marker", encoding="utf-8")

    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws))
    monkeypatch.setattr(_workspace_mod, "_DEFAULT_WORKSPACE", str(ws))
    return ws


# ---------------------------------------------------------------------------
# Mocks de infraestrutura externa (Docker, HTTP) usados pelo harness
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_response():
    """`MagicMock` de uma resposta HTTP 200 com corpo OpenAPI mínimo.

    Usado para simular `requests.get(...)` contra o app FastAPI que roda
    dentro do container, sem subir rede real.
    """
    resposta = MagicMock()
    resposta.status_code = 200
    resposta.json.return_value = {"paths": {"/": {"get": {}}}}
    resposta.text = "OK"
    return resposta


@pytest.fixture
def docker_mock():
    """Cliente Docker stubado com um fluxo de execução "feliz" completo.

    Cobre build (sucesso), `containers.run` (container "running", exit 0)
    e `exec_run` respondendo aos comandos que o estágio de testes do
    harness dispara (`pytest --version`, `cat report.json`, `cat cov.json`,
    `python -m pytest`). Para simular falhas, sobrescreva
    `client.images.build.side_effect` no próprio teste.
    """
    import docker as _docker_sdk

    client = MagicMock()
    client.images.build.return_value = (
        MagicMock(),
        [{"stream": "Successfully built abc123"}],
    )

    container = MagicMock()
    container.status = "running"
    container.attrs = {"State": {"ExitCode": 0}}
    container.logs.return_value = b"2026-01-01T00:00:00 INFO [app] Uvicorn running"
    container.exec_run.side_effect = _fake_exec_run
    client.containers.run.return_value = container
    client.containers.get.side_effect = _docker_sdk.errors.NotFound("sem container")
    return client


class _ExecResult:
    """Resultado sintético de `container.exec_run(...)`."""

    def __init__(self, exit_code: int, output: bytes) -> None:
        self.exit_code = exit_code
        self.output = output


def _fake_exec_run(cmd: Any, workdir: str | None = None, demux: bool = False) -> _ExecResult:
    """Simula os comandos disparados pelo estágio de testes automatizados do harness."""
    shell = cmd[-1] if isinstance(cmd, (list, tuple)) else cmd

    def out(s: str) -> bytes:
        return s.encode()

    if "pytest --version" in shell:
        return _ExecResult(0, out("pytest 8.2.0"))
    if shell.startswith("cat ") and "report.json" in shell:
        return _ExecResult(0, out(json.dumps(
            {"summary": {"passed": 1, "failed": 0, "error": 0, "skipped": 0, "total": 1},
             "tests": []}
        )))
    if shell.startswith("cat ") and "cov.json" in shell:
        return _ExecResult(0, out(json.dumps(
            {"totals": {"percent_covered": 100.0, "covered_lines": 5, "num_statements": 5}}
        )))
    if "python -m pytest" in shell:
        return _ExecResult(0, out("1 passed in 0.01s"))
    return _ExecResult(0, out(""))
