"""Testes do gate estrutural que precede o harness.

Contexto: numa run real de 8 tasks, o coder encerrava o turno após um arquivo e
o harness rodou 37 vezes — ~13 delas sobre um workspace com um arquivo novo ou
nenhum, pagando build, subida de serviço e testes para reproduzir uma falha já
conhecida. O gate recusa essas rodadas antes de gastar LLM e sandbox.

Duas propriedades precisam valer sempre: a camada dura nunca deixa passar o que
o harness reprovaria no estágio 1, e a camada branda SEMPRE cede depois do teto
— senão uma divergência de nomenclatura no contrato travaria a task inteira.
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
    {"schema_version": "1", "surface": "service", "build": ["pip install -r requirements.txt"],
     "run": "uvicorn app.main:app --port 8000", "port": 8000}
)


# ---------------------------------------------------------------------------
# Camada dura — pré-condições que o harness também exige
# ---------------------------------------------------------------------------

def test_run_json_ausente_bloqueia(tmp_path):
    raiz = _workspace(tmp_path, {"app/main.py": "print('x')"})

    resultado = verificar_completude(raiz)

    assert not resultado.completo
    assert any("run.json" in motivo for motivo in resultado.bloqueios_duros)


def test_run_json_incoerente_bloqueia(tmp_path):
    """Reusa a validação do próprio manifesto: surface=service exige run e port."""
    raiz = _workspace(
        tmp_path,
        {"run.json": json.dumps({"schema_version": "1", "surface": "service"}),
         "app/main.py": "print('x')"},
    )

    resultado = verificar_completude(raiz)

    assert any("incoerente" in m or "inválido" in m for m in resultado.bloqueios_duros)


def test_apenas_arquivos_meta_bloqueia(tmp_path):
    """O caso real: primeira iteração com PLAN.md e mais nada."""
    raiz = _workspace(
        tmp_path,
        {"run.json": _RUN_JSON_VALIDO, "PLAN.md": "# plano",
         "README.md": "# leia", "requirements.txt": "fastapi"},
    )

    resultado = verificar_completude(raiz)

    assert any("código" in motivo for motivo in resultado.bloqueios_duros)


def test_workspace_implementavel_passa(tmp_path):
    raiz = _workspace(
        tmp_path,
        {"run.json": _RUN_JSON_VALIDO, "PLAN.md": "# plano", "app/main.py": "print('x')"},
    )

    assert verificar_completude(raiz).completo


# ---------------------------------------------------------------------------
# Camada branda — indício, não prova
# ---------------------------------------------------------------------------

def test_outputs_faltando_viram_pendencia_branda(tmp_path):
    raiz = _workspace(tmp_path, {"run.json": _RUN_JSON_VALIDO, "app/main.py": "x"})

    resultado = verificar_completude(raiz, ["app/models.py"])

    assert not resultado.bloqueios_duros
    assert resultado.pendencias_brandas
    assert "app/models.py" in resultado.pendencias_brandas[0]


def test_output_casa_por_nome_de_arquivo(tmp_path):
    """Dado real: contrato declara `models/ensaio.py`, coder cria `app/models/ensaio.py`.

    Comparar caminho completo bloquearia para sempre uma implementação correta.
    """
    raiz = _workspace(
        tmp_path,
        {"run.json": _RUN_JSON_VALIDO, "app/models/ensaio.py": "x"},
    )

    assert verificar_completude(raiz, ["models/ensaio.py"]).completo


def test_diretorios_e_placeholders_sao_ignorados(tmp_path):
    """`ensaios/<id>/fotos/` é diretório de runtime, não arquivo a verificar."""
    raiz = _workspace(tmp_path, {"run.json": _RUN_JSON_VALIDO, "app/main.py": "x"})

    resultado = verificar_completude(
        raiz, ["ensaios/<id>/fotos/", "saida/", "app/**/gerado.py"]
    )

    assert resultado.completo


def test_camada_dura_tem_precedencia_sobre_a_branda(tmp_path):
    """Listar outputs faltando junto com 'não há código' seria ruído."""
    raiz = _workspace(tmp_path, {"PLAN.md": "# plano"})

    resultado = verificar_completude(raiz, ["app/models.py"])

    assert resultado.bloqueios_duros and not resultado.pendencias_brandas
    assert resultado.motivos == resultado.bloqueios_duros


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


def _coder_ws(executor, arquivos: dict[str, str]):
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
    _coder_ws(executor, {"PLAN.md": "# plano"})
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

    _coder_ws(executor, {"PLAN.md": "# plano"})
    state = {"task_id": "TASK-001"}
    executor.recusar_execucao_incompleta(_Ctx(state))

    assert not _e_estagnacao(state["execution_result"])


def test_callback_libera_workspace_completo(executor):
    _coder_ws(executor, {"run.json": _RUN_JSON_VALIDO, "app/main.py": "x"})

    assert executor.recusar_execucao_incompleta(_Ctx({"task_id": "TASK-001"})) is None


def test_camada_branda_cede_apos_o_teto(executor):
    """Sem isso, uma divergência de nomenclatura travaria a task até o fim."""
    _coder_ws(executor, {"run.json": _RUN_JSON_VALIDO, "app/main.py": "x"})
    state = {
        "task_id": "TASK-001",
        "tasks": {
            "macro_context": {},
            "tasks": [{"id": "TASK-001", "contract": {"outputs": ["nunca_criado.py"]}}],
        },
    }

    recusas = [
        executor.recusar_execucao_incompleta(_Ctx(state)) is not None
        for _ in range(4)
    ]

    assert recusas == [True, True, False, False]
    assert state[executor.CHAVE_BLOQUEIOS_PREFLIGHT] == 2


def test_camada_dura_nao_cede(executor):
    """A dura não tem teto: sem run.json o harness falharia no estágio 1 sempre."""
    _coder_ws(executor, {"PLAN.md": "# plano"})
    state = {"task_id": "TASK-001"}

    for _ in range(5):
        assert executor.recusar_execucao_incompleta(_Ctx(state)) is not None


def test_contador_do_gate_e_zerado_entre_tasks():
    """O teto vale POR task — o TaskIterator remove a chave no reset de ciclo."""
    from src.agents.workflow_coding_review import task_iterator as ti

    assert ti.CHAVE_BLOQUEIOS_PREFLIGHT in ti._CHAVES_CICLO_REMOVIDAS

    state = {ti.CHAVE_BLOQUEIOS_PREFLIGHT: 2, "validation": {"x": 1}}
    ti.TaskIterator._resetar_ciclo(state, primeira=False, task_id="TASK-002")

    assert ti.CHAVE_BLOQUEIOS_PREFLIGHT not in state
