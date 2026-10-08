"""Quadro do produto (`AI4ES_QUADRO_PRODUTO`): visão determinística do que as
tasks anteriores entregaram, no prompt do coder e do autor de aceite."""

from __future__ import annotations

import asyncio
import importlib
import json
from types import SimpleNamespace

import pytest

from shared.tools.coding_tools import aceite_independente as ai
from shared.tools.coding_tools import quadro as qd

_ARQ = ai.caminho_relativo("TASK-001")
_ARQ_UI = ai.caminho_relativo_interface("TASK-001")

_MAIN = '''
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/media", StaticFiles(directory="media"), name="media")

@app.get("/")
def painel():
    ...

@app.post("/ensaios/{ensaio_id}/upload")
async def upload(ensaio_id: str):
    ...
'''

_MODELS = '''
class Base: ...

class Ensaio(Base):
    __tablename__ = "ensaios"
    id = 1
    titulo = 2
    _privado = 3

class NaoModelo:
    x = 1
'''

_TASKS = [
    {
        "id": "TASK-001",
        "description": "CRUD de ensaios com tela",
        "acceptance_criteria": [
            {"id": "CA-01", "description": "A partir da página inicial, criar um ensaio"},
            {"id": "CA-02", "description": "id único no SQLite", "tecnico": True},
        ],
    },
    {"id": "TASK-002", "description": "upload", "acceptance_criteria": []},
]


@pytest.fixture
def projeto(tmp_path):
    workdir = tmp_path / "src"
    tasks_dir = tmp_path / "tasks"
    (workdir / "app" / "templates").mkdir(parents=True)
    (workdir / "app" / "main.py").write_text(_MAIN)
    (workdir / "app" / "models.py").write_text(_MODELS)
    (workdir / "app" / "ids.py").write_text("import uuid\ndef novo_id(): return str(uuid.uuid4())\n")
    (workdir / "app" / "templates" / "index.html").write_text('<form data-testid="form-novo-ensaio"></form>')
    (workdir / "venv" / "lib").mkdir(parents=True)
    (workdir / "venv" / "lib" / "x.py").write_text("@app.get('/nao-conta')\ndef x(): ...\n")
    (workdir / ai.PASTA_ACEITE).mkdir(parents=True)
    (workdir / _ARQ_UI).write_text("def test_CA_01(page): ...\n")
    tasks_dir.mkdir()
    ai.gravar_mapa(tasks_dir, "TASK-001", _ARQ_UI, {"CA-01": [f"{_ARQ_UI}::test_CA_01"]})
    relatorio = tmp_path / "TASK-001.report.json"
    relatorio.write_text(json.dumps({"criteria_evidence": [{"criterion_id": "CA-01", "outcome": "atendido"}]}))
    resultados = {"TASK-001": {"status": "aprovado", "report_path": str(relatorio)}}
    return SimpleNamespace(workdir=workdir, tasks_dir=tasks_dir, resultados=resultados)


def _quadro(p, trilha={"id": "python-web"}):
    return qd.montar_quadro(
        workdir=p.workdir, tasks_dir=p.tasks_dir, tasks=_TASKS, task_results=p.resultados, trilha=trilha
    )


def test_camada_generica_traz_homologacao_regressao_e_identificadores(projeto):
    texto = _quadro(projeto, trilha=None)
    assert "✔ TASK-001 (aprovado): CRUD de ensaios com tela" in texto
    assert "✔ CA-01 A partir da página inicial, criar um ensaio" in texto
    assert "CA-02" not in texto  # técnico não é homologação
    assert "TASK-002" not in texto  # ainda não fechada
    assert f"- {_ARQ_UI} (TASK-001)" in texto
    assert "form-novo-ensaio" in texto
    # Sem trilha python-web: nada da camada específica.
    assert "Rotas existentes" not in texto and "Modelos" not in texto


def test_camada_python_web_traz_rotas_estaticos_modelos_e_convencoes(projeto):
    texto = _quadro(projeto)
    assert "- GET / → app/main.py:painel" in texto
    assert "- POST /ensaios/{ensaio_id}/upload → app/main.py:upload" in texto
    assert "- /media (app/main.py)" in texto
    assert "- Ensaio (app/models.py): id, titulo" in texto
    assert "NaoModelo" not in texto and "_privado" not in texto
    assert "app/templates/index.html" in texto
    assert "`app/ids.py` (`novo_id()`)" in texto
    assert "/nao-conta" not in texto  # venv fica de fora


def test_sem_task_fechada_nao_ha_quadro(projeto):
    assert qd.montar_quadro(
        workdir=projeto.workdir, tasks_dir=projeto.tasks_dir, tasks=_TASKS, task_results={}, trilha=None
    ) == ""
    assert qd.secao_prompt("") == ""


def test_quadro_respeita_o_limite(projeto, monkeypatch):
    monkeypatch.setattr(qd, "LIMITE_CARACTERES", 200)
    texto = _quadro(projeto)
    assert len(texto) <= 200 + len("\n… (quadro truncado)") and texto.endswith("(quadro truncado)")


def test_coder_recebe_o_quadro_fora_do_templating(tmp_path, monkeypatch):
    """O quadro tem chaves de rota (`{ensaio_id}`): se passasse pelo
    `inject_session_state`, viraria variável de state inexistente."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    cr_coder = importlib.import_module("src.agents.workflow_coding_review.coder.agent")

    async def _injecao_estrita(texto, _ctx):
        assert "{ensaio_id}" not in texto, "o quadro passou pelo templating"
        return texto

    monkeypatch.setattr("google.adk.utils.instructions_utils.inject_session_state", _injecao_estrita)
    quadro = "## Rotas existentes\n- POST /ensaios/{ensaio_id}/upload"
    texto = asyncio.run(cr_coder._INSTRUCTION(SimpleNamespace(state={"quadro_produto": quadro})))
    assert texto.startswith("# O QUE JÁ EXISTE NO PRODUTO — NÃO QUEBRE")
    assert "/ensaios/{ensaio_id}/upload" in texto


def test_iterator_monta_o_quadro_so_com_a_flag(tmp_path, monkeypatch, projeto):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.pipeline_flags import quadro_produto
    from src.agents.workflow_coding_review import task_iterator as ti

    monkeypatch.delenv("AI4ES_QUADRO_PRODUTO", raising=False)
    assert quadro_produto() is False
    monkeypatch.setenv("AI4ES_QUADRO_PRODUTO", "true")
    assert quadro_produto() is True

    monkeypatch.setattr(ti, "get_agent_workspace", lambda nome: projeto.workdir if nome == "cr_coder" else projeto.tasks_dir)
    state = {"trilha": {"id": "python-web"}}
    ti.TaskIterator._atualizar_quadro(state, _TASKS, projeto.resultados)
    assert "Rotas existentes" in state[ti.CHAVE_QUADRO]
