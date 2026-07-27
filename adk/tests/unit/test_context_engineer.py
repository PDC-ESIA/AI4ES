"""Tests para src/agents/context_engineer/ — descoberta + schemas + tools."""

import json
from pathlib import Path

import pytest


def test_context_engineer_root_agent_importavel():
    from src.agents.context_engineer import root_agent
    assert root_agent is not None
    assert root_agent.name == "context_engineer"


def test_context_engineer_tem_output_schema():
    from src.agents.context_engineer import root_agent
    from src.agents.context_engineer.schemas import TasksOutput
    assert root_agent.output_schema == TasksOutput


def test_context_engineer_tem_tool_salvar_task():
    from src.agents.context_engineer import root_agent
    # Factory injeta tool_ask_clarification_adk + tool_salvar_task + tool_ler_workspace_fase
    assert len(root_agent.tools) == 3


def test_schemas_macro_context_minimal():
    from src.agents.context_engineer.schemas import MacroContext
    mc = MacroContext(
        summary="Sistema de autenticação JWT",
        tech_stack=["Python", "FastAPI"],
        global_rules=["RESTful"],
    )
    assert mc.summary.startswith("Sistema")
    assert len(mc.tech_stack) == 2


def test_schemas_task_com_contract():
    from src.agents.context_engineer.schemas import Task, Contract
    task = Task(
        id="TASK-001",
        type="backend",
        complexity="medium",
        description="Criar endpoint POST /auth/login",
        acceptance_criteria=["Retorna 200 com JWT", "Retorna 401 com credenciais inválidas"],
        contract=Contract(inputs=[], outputs=["src/auth.py"]),
        requirement_id="RF-001",
        design_refs=["design/analise_tecnica_HU-001.md"],
    )
    assert task.id == "TASK-001"
    assert task.business_rules == []  # default factory
    assert task.contract.outputs == ["src/auth.py"]


def test_schemas_contract_interfaces_objeto_aceito():
    from src.agents.context_engineer.schemas import Contract
    contract = Contract(
        interfaces={
            "create_ensaio": {
                "method": "POST",
                "params": {"titulo": "str", "cliente": "str"},
            }
        }
    )
    assert isinstance(contract.interfaces, list)
    assert any("create_ensaio" in item for item in contract.interfaces)


def test_schemas_contract_interfaces_aceita_lista_e_string():
    from src.agents.context_engineer.schemas import Contract

    as_list = Contract.model_validate({
        "inputs": [],
        "outputs": [],
        "interfaces": ["GET /users", "DELETE /users/<id>"],
    })
    assert as_list.interfaces == ["GET /users", "DELETE /users/<id>"]

    as_string = Contract.model_validate({
        "inputs": [],
        "outputs": [],
        "interfaces": "POST /auth/login",
    })
    assert as_string.interfaces == ["POST /auth/login"]


def test_schemas_tasks_output_completo():
    from src.agents.context_engineer.schemas import TasksOutput, MacroContext, Task, Contract
    output = TasksOutput(
        macro_context=MacroContext(
            summary="X",
            tech_stack=["Python"],
            global_rules=["Y"],
        ),
        tasks=[
            Task(
                id="TASK-001",
                type="test",
                complexity="low",
                description="Z",
                acceptance_criteria=["A"],
                contract=Contract(),
                requirement_id="RF-001",
                design_refs=["design/analise_tecnica_HU-001.md"],
            )
        ],
    )
    assert len(output.tasks) == 1
    assert output.macro_context.summary == "X"


def test_tool_salvar_task_persiste_json(tmp_path, monkeypatch):
    """tool_salvar_task escreve JSON em workspace/tasks/<id>.json."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from src.agents.context_engineer.tools import tool_salvar_task
    task_json = json.dumps({
        "id": "TASK-001",
        "type": "backend",
        "description": "Criar endpoint",
    })
    result = tool_salvar_task("TASK-001", task_json)
    assert result["sucesso"] is True
    arquivo = tmp_path / "ws" / "tasks" / "TASK-001.json"
    assert arquivo.is_file()
    conteudo = json.loads(arquivo.read_text(encoding="utf-8"))
    assert conteudo["id"] == "TASK-001"


def test_tool_salvar_task_id_invalido_rejeita(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from src.agents.context_engineer.tools import tool_salvar_task
    result = tool_salvar_task("INVALID-001", json.dumps({"x": 1}))
    assert result["sucesso"] is False
    assert "TASK-" in result["erro"]


def test_tool_salvar_task_json_invalido_rejeita(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from src.agents.context_engineer.tools import tool_salvar_task
    result = tool_salvar_task("TASK-002", "not a json")
    assert result["sucesso"] is False
    assert "JSON inválido" in result["erro"] or "JSON inválido" in str(result.get("erro", ""))

def test_tool_ler_workspace_fase_requirements(tmp_path, monkeypatch):
    """tool_ler_workspace_fase le arquivos da pasta requirements."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta = tmp_path / "ws" / "requirements"
    pasta.mkdir(parents=True)
    (pasta / "RF-001.md").write_text("# RF-001\nDescrição do requisito", encoding="utf-8")
    from src.agents.context_engineer.tools import tool_ler_workspace_fase
    result = tool_ler_workspace_fase("requirements")
    assert result["sucesso"] is True
    assert result["total_lidos"] == 1
    assert result["artefatos"][0]["nome"] == "RF-001.md"


def test_tool_ler_workspace_fase_pasta_inexistente(tmp_path, monkeypatch):
    """tool_ler_workspace_fase retorna erro se pasta nao existe."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from src.agents.context_engineer.tools import tool_ler_workspace_fase
    result = tool_ler_workspace_fase("requirements")
    assert result["sucesso"] is False
    assert "não encontrada" in result["erro"]


def test_tool_ler_workspace_fase_invalida(tmp_path, monkeypatch):
    """tool_ler_workspace_fase rejeita fase invalida."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from src.agents.context_engineer.tools import tool_ler_workspace_fase
    result = tool_ler_workspace_fase("inválida")
    assert result["sucesso"] is False