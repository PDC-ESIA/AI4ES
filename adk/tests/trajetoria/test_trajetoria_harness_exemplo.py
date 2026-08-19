"""Exemplo de teste de trajetória (Camada 2).

Diferente de um teste de infraestrutura (Camada 1), que verificaria só o
resultado final do harness (`overall_status == "sucesso"`), este teste
verifica a TRAJETÓRIA: a sequência de estágios que o harness percorre.
Serve de referência para novos testes desta camada — ver
`tests/README.md` para o guia completo.

Reaproveita os stubs de Docker/HTTP de `test_harness_poc.py`
(agora expostos como fixtures `docker_mock`/`mock_response` em
`tests/trajetoria/conftest.py`) e a fixture `workspace_fixture`.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from shared.tools.coding_tools.harness_execucao import executar_harness_validacao

_TASK_ID = "TASK-TRAJETORIA-001"


def _preparar_workspace(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Monta um workspace mínimo com uma app FastAPI e uma Task de exemplo."""
    coder = tmp_path / "coder" / "src"
    execution = tmp_path / "coder" / "execution"
    tasks = tmp_path / "coder" / "tasks"
    for d in (coder, execution, tasks):
        d.mkdir(parents=True, exist_ok=True)

    (coder / "main.py").write_text(
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n\n"
        "@app.get('/')\n"
        "def home():\n"
        "    return {'ok': True}\n",
        encoding="utf-8",
    )
    (coder / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")

    (tasks / f"{_TASK_ID}.json").write_text(
        json.dumps(
            {
                "id": _TASK_ID,
                "description": "Expor uma rota raiz que responde 200.",
                "acceptance_criteria": ["A rota GET / deve responder 200"],
                "contract": {},
            }
        ),
        encoding="utf-8",
    )
    return coder, execution, tasks


def test_harness_percorre_estagios_na_ordem_esperada(
    tmp_path, docker_mock, mock_response, trace_collector,
):
    """A trajetória do harness deve seguir preparação → deploy → testes → relatório.

    Além de checar o `overall_status` (o que já é feito na Camada 1), aqui
    registramos cada estágio no `trace_collector` e validamos a ORDEM
    relativa — é essa ordem que garante que o veredito final (Camada 1/2 de
    validação do implementation_validator) só é emitido depois de coletar
    evidências reais, nunca antes.
    """
    coder, execution, tasks = _preparar_workspace(tmp_path)

    with (
        patch("docker.from_env", return_value=docker_mock),
        patch("requests.get", return_value=mock_response),
        patch("shared.tools.coding_tools.harness_execucao.time.sleep"),
    ):
        report = executar_harness_validacao(
            _TASK_ID,
            1,
            coder_base_dir=coder,
            execution_base_dir=execution,
            tasks_base_dir=tasks,
        )

    for stage in report["stages"]:
        trace_collector.record(
            agente="harness_execucao",
            acao=f"stage:{stage['stage']}",
            status="ok" if stage["status"] == "sucesso" else "erro",
            metadata={"evidence_keys": sorted(stage.get("evidence", {}).keys())},
            raw=stage,
        )

    # `assert_order` compara a sequência de AGENTES; aqui todos os eventos
    # são do mesmo agente (harness_execucao) e o que varia é a AÇÃO, então
    # validamos a ordem das ações diretamente pelos índices no trace.
    acoes_na_ordem = [e.acao for e in trace_collector.events]
    assert acoes_na_ordem.index("stage:preparacao_ambiente") < acoes_na_ordem.index(
        "stage:implantacao_artefato"
    )
    assert acoes_na_ordem.index("stage:implantacao_artefato") < acoes_na_ordem.index(
        "stage:testes_automatizados"
    )
    assert acoes_na_ordem.index("stage:testes_automatizados") < acoes_na_ordem.index(
        "stage:geracao_relatorio"
    )
    assert report["overall_status"] == "sucesso"
