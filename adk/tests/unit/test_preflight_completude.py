"""Testes do gate estrutural que precede o harness.

Contexto: numa run real de 8 tasks, o coder encerrava o turno após um arquivo e
o harness rodou 37 vezes — ~13 delas sobre um workspace com um arquivo novo ou
nenhum, pagando build, subida de serviço e testes para reproduzir uma falha já
conhecida. O gate recusa essas rodadas antes de gastar LLM e sandbox.

O escopo é restrito às condições que o harness TAMBÉM reprovaria no estágio 1,
onde falso positivo é impossível — por isso o gate não tem teto de tentativas
nem nenhum parâmetro de tolerância: ele nunca trava uma implementação legítima.
"""

import importlib
import json

import pytest

from shared.execution.completude import verificar_completude


def _workspace(tmp_path, arquivos: dict[str, str]):
    raiz = tmp_path / "src"
    raiz.mkdir(parents=True, exist_ok=True)
    for nome, conteudo in arquivos.items():
        destino = raiz / nome
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(conteudo, encoding="utf-8")
    return raiz


_RUN_JSON_VALIDO = json.dumps(
    {
        "schema_version": "1",
        "surface": "service",
        "build": ["pip install -r requirements.txt"],
        "run": "uvicorn app.main:app --port 8000",
        "port": 8000,
    }
)


def test_run_json_ausente_bloqueia(tmp_path):
    raiz = _workspace(tmp_path, {"app/main.py": "print('x')"})

    resultado = verificar_completude(raiz)

    assert not resultado.completo
    assert any("run.json" in bloqueio for bloqueio in resultado.bloqueios)


def test_run_json_incoerente_bloqueia(tmp_path):
    """Reusa a validação do próprio manifesto: surface=service exige run e port."""
    raiz = _workspace(
        tmp_path,
        {
            "run.json": json.dumps({"schema_version": "1", "surface": "service"}),
            "app/main.py": "print('x')",
        },
    )

    resultado = verificar_completude(raiz)

    assert any(
        "incoerente" in bloqueio or "inválido" in bloqueio
        for bloqueio in resultado.bloqueios
    )


def test_apenas_arquivos_meta_bloqueia(tmp_path):
    """O caso real: primeira iteração com PLAN.md e mais nada."""
    raiz = _workspace(
        tmp_path,
        {
            "run.json": _RUN_JSON_VALIDO,
            "PLAN.md": "# plano",
            "README.md": "# leia",
            "requirements.txt": "fastapi",
        },
    )

    resultado = verificar_completude(raiz)

    assert any("código" in bloqueio for bloqueio in resultado.bloqueios)


def test_workspace_implementavel_passa(tmp_path):
    raiz = _workspace(
        tmp_path,
        {"run.json": _RUN_JSON_VALIDO, "PLAN.md": "# plano", "app/main.py": "print('x')"},
    )

    assert verificar_completude(raiz).completo


def test_workspace_inexistente_bloqueia(tmp_path):
    """Antes do primeiro turno do coder não há nada a executar."""
    resultado = verificar_completude(tmp_path / "nao_existe")

    assert not resultado.completo
    assert resultado.arquivos == ()


# ---------------------------------------------------------------------------
# Callback no executor
# ---------------------------------------------------------------------------


@pytest.fixture
def executor(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    modulo = importlib.import_module(
        "src.agents.workflow_coding_review.executor.agent"
    )
    return importlib.reload(modulo)


class _Ctx:
    def __init__(self, state):
        self.state = state


def _coder_ws(arquivos: dict[str, str]):
    from shared.workspace import get_agent_workspace

    raiz = get_agent_workspace("cr_coder")
    for nome, conteudo in arquivos.items():
        destino = raiz / nome
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(conteudo, encoding="utf-8")
    return raiz


def test_callback_recusa_e_publica_execution_result(executor):
    """O detalhe que falharia em silêncio: o output_key NÃO é gravado aqui.

    Um before_agent_callback que devolve Content faz o ADK retornar antes do
    _run_async_impl — onde o output_key seria salvo. Sem a escrita explícita, o
    coder receberia o ErrorReport da rodada anterior.
    """
    _coder_ws({"PLAN.md": "# plano"})
    state = {"task_id": "TASK-001"}

    retorno = executor.recusar_execucao_incompleta(_Ctx(state))

    assert retorno is not None
    texto = retorno.parts[0].text
    assert state["execution_result"] == texto
    assert texto.startswith("IMPLEMENTAÇÃO INCOMPLETA")
    assert "run.json" in texto and "PLAN.md" in texto


def test_recusa_nao_e_confundida_com_estagnacao(executor):
    """`STATUS: bloqueado` na 1ª linha faria o TaskIterator encerrar a task."""
    from src.agents.workflow_coding_review.task_iterator import _e_estagnacao

    _coder_ws({"PLAN.md": "# plano"})
    state = {"task_id": "TASK-001"}
    executor.recusar_execucao_incompleta(_Ctx(state))

    assert not _e_estagnacao(state["execution_result"])


def test_callback_libera_workspace_completo(executor):
    _coder_ws({"run.json": _RUN_JSON_VALIDO, "app/main.py": "x"})

    assert executor.recusar_execucao_incompleta(_Ctx({"task_id": "TASK-001"})) is None


def test_gate_nao_cede_enquanto_faltar_o_minimo(executor):
    """Sem run.json o harness falharia no estágio 1 sempre — não há por que ceder."""
    _coder_ws({"PLAN.md": "# plano"})
    state = {"task_id": "TASK-001"}

    for _ in range(5):
        assert executor.recusar_execucao_incompleta(_Ctx(state)) is not None
