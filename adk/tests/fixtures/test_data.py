"""Dados de exemplo (manifests, tasks) compartilhados entre as camadas de
teste.

Mantém os literais em um único lugar para evitar divergência entre testes
que precisam do "mesmo" manifesto/task de exemplo (ex.: um teste de
infraestrutura e um teste de trajetória sobre o mesmo caso).
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Manifestos de fase (contrato: shared.manifest.PhaseManifest)
# ---------------------------------------------------------------------------

SAMPLE_REQUIREMENTS_MANIFEST: dict[str, Any] = {
    "phase": "requirements",
    "status": "ok",
    "artifacts": [
        {"tipo": "HU", "id": "HU-001", "path": "requirements/HUs/HU-001.md"},
    ],
    "doubts": [],
    "summary": "Requisito da calculadora.",
}

SAMPLE_CODING_MANIFEST: dict[str, Any] = {
    "phase": "coding",
    "status": "ok",
    "artifacts": [
        {"tipo": "codigo", "id": "calculadora", "path": "coder/src/calculadora.py"},
    ],
    "doubts": [],
    "summary": "Código da calculadora entregue.",
}

SAMPLE_QA_MANIFEST: dict[str, Any] = {
    "phase": "qa",
    "status": "ok",
    "artifacts": [
        {"tipo": "input", "id": "calculadora", "path": "tests/inputs/calculadora.json"},
        {"tipo": "teste", "id": "calculadora", "path": "tests/calculadora/test_calculadora.py"},
    ],
    "doubts": [],
    "summary": "Testes gerados e executados com sucesso.",
}

# ---------------------------------------------------------------------------
# Task de exemplo para o harness de execução (Camada 2 / trajetória)
# ---------------------------------------------------------------------------

SAMPLE_TASK: dict[str, Any] = {
    "id": "TASK-SAMPLE-001",
    "description": "Expor uma rota raiz que responde 200.",
    "acceptance_criteria": ["A rota GET / deve responder 200"],
    "contract": {},
}

SAMPLE_TASK_APP_CODE = (
    "from fastapi import FastAPI\n"
    "app = FastAPI()\n\n"
    "@app.get('/')\n"
    "def home():\n"
    "    return {'ok': True}\n"
)