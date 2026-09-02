"""Exemplo de teste de trajetória (Camada 2).

Diferente de um teste de infraestrutura (Camada 1), que verificaria só o
resultado final do harness (`overall_status == "sucesso"`), este teste
verifica a TRAJETÓRIA: a sequência de estágios que o harness percorre.
Serve de referência para novos testes desta camada — ver
`tests/README.md` para o guia completo.

Pós-issue #370 (arquitetura agnóstica de tecnologia), o estágio 1 do harness
(`_estagio_preparacao`) exige um manifesto `run.json` explícito na raiz do
artefato do coder — o harness não infere mais stack/Docker/FastAPI a partir
dos arquivos (ver `shared/execution/manifest.py`). Este teste usa
`surface="command"` (perfil C) com `sandbox="direct"` (padrão): o `run` é um
comando único que roda e termina, sem subir serviço nem fazer healthcheck
HTTP (ver `shared/execution/profile.py`). Isso permite exercitar o harness
de ponta a ponta com subprocessos REAIS (via `DirectSandbox`), sem precisar
de Docker nem de rede — por isso os fixtures `docker_mock`/`mock_response`
(vestígios do harness pré-#370, que subia Docker/FastAPI diretamente) não
são mais requisitados aqui: o caminho `command` do harness atual nunca toca
`docker.from_env` nem `requests.get`. Eles continuam definidos em
`tests/coder_isolado/conftest.py` (sem consumidor após esta correção).
"""

from __future__ import annotations

import json
from pathlib import Path

from shared.tools.coding_tools.harness_execucao import executar_harness_validacao

_TASK_ID = "TASK-TRAJETORIA-001"


def _preparar_workspace(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Monta um workspace mínimo com um script de linha de comando, o manifesto
    `run.json` (contrato coder→harness) e uma Task de exemplo."""
    coder = tmp_path / "coder" / "src"
    execution = tmp_path / "coder" / "execution"
    tasks = tmp_path / "coder" / "tasks"
    for d in (coder, execution, tasks):
        d.mkdir(parents=True, exist_ok=True)

    (coder / "main.py").write_text(
        "def main() -> None:\n"
        "    print('Execução concluída com sucesso.')\n\n\n"
        "if __name__ == '__main__':\n"
        "    main()\n",
        encoding="utf-8",
    )

    (coder / "run.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "surface": "command",
                "build": ["python3 -m py_compile main.py"],
                "run": "python3 main.py",
                "test": ["echo '1 passed'"],
                "sandbox": "direct",
            }
        ),
        encoding="utf-8",
    )

    (tasks / f"{_TASK_ID}.json").write_text(
        json.dumps(
            {
                "id": _TASK_ID,
                "description": "Executar o pipeline via linha de comando.",
                "acceptance_criteria": [
                    "O comando principal deve ser executado com sucesso (exit code 0)."
                ],
                "contract": {},
            }
        ),
        encoding="utf-8",
    )
    return coder, execution, tasks


def test_harness_percorre_estagios_na_ordem_esperada(tmp_path, trace_collector):
    """A trajetória do harness deve seguir preparação → deploy → testes → relatório.

    Além de checar o `overall_status` (o que já é feito na Camada 1), aqui
    registramos cada estágio no `trace_collector` e validamos a ORDEM
    relativa — é essa ordem que garante que o veredito final (Camada 1/2 de
    validação do implementation_validator) só é emitido depois de coletar
    evidências reais, nunca antes.
    """
    coder, execution, tasks = _preparar_workspace(tmp_path)

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
