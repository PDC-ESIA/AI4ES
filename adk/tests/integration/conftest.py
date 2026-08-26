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
  base nelas (nunca no status técnico isolado) — coberto hoje pelos testes
  em `tests/coder_isolado/trajetoria/`, que também definem as fixtures de
  trace/mocks de Docker (`tests/coder_isolado/conftest.py`).

O artefato central desta camada é o **trace**: a sequência de eventos
observados durante a execução, organizada em duas camadas (ver
`tests/fixtures/trace_helpers.py`). Os testes que permanecem diretamente
aqui (`test_hitl_e2e.py`, `test_integration_orchestrator_qa.py`) validam
o orchestrator e não usam trace_collector — por isso essa fixture não
está mais neste conftest (ver `tests/coder_isolado/conftest.py`).
"""

from __future__ import annotations

from pathlib import Path

import pytest


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

